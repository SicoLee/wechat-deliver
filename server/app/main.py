from contextlib import asynccontextmanager
from datetime import datetime
from decimal import Decimal
import hmac
from typing import Optional
from uuid import uuid4
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from .config import get_settings
from .db import get_db
from .models import Admin, Order, OrderAuditLog, OrderItem, OrderStatus, PaymentStatus, PrintStatus, Product
from .schemas import OrderAuditOut, OrderCreateIn, OrderOut, ProductCreateIn, ProductOut, ProductUpdateIn
from .services.order_audit import record_order_audit
from .services.delivery import build_distance_provider
from .services.order_events import enqueue_receipt_print, process_pending_prints
from .services.printer import MockPrinter
from .services.payment import PaymentVerificationError, WechatPayV3CallbackVerifier, confirm_payment
from .observability import configure_logging, request_log_middleware

settings = get_settings()
distance_provider = build_distance_provider(settings.delivery_provider, settings.tencent_map_key, settings.external_request_timeout_seconds)
printer = MockPrinter()


def seed_products(db: Session) -> None:
    if db.scalar(select(Product.id).limit(1)):
        return
    db.add_all([
        Product(name="招牌大排粉", price=Decimal("15.00"), category="粉面"),
        Product(name="牛肉粉", price=Decimal("14.00"), category="粉面"),
        Product(name="素粉", price=Decimal("10.00"), category="粉面"),
        Product(name="矿泉水", price=Decimal("2.00"), category="饮品"),
        Product(name="冰豆浆", price=Decimal("4.00"), category="饮品"),
    ])
    db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.validate_runtime()
    configure_logging(settings.log_level)
    with next(get_db()) as db:
        seed_products(db)
    yield


app = FastAPI(title="单店微信点单 API", version="0.1.0", lifespan=lifespan)
app.middleware("http")(request_log_middleware)


def openid_from_header(x_openid: Optional[str] = Header(default=None)) -> str:
    if not x_openid:
        raise HTTPException(401, "缺少 X-OpenID；小程序正式版应由 wx.login 换取")
    return x_openid


def require_development() -> None:
    if settings.app_env not in {"development", "test"}:
        raise HTTPException(404, "Not Found")


def require_job_token(x_job_token: Optional[str] = Header(default=None)) -> None:
    if not settings.job_token:
        raise HTTPException(503, "后台任务尚未配置")
    if not x_job_token or not hmac.compare_digest(x_job_token, settings.job_token):
        raise HTTPException(403, "后台任务凭据无效")


def require_admin(openid: str = Depends(openid_from_header), db: Session = Depends(get_db)) -> str:
    if not db.scalar(select(Admin).where(Admin.openid == openid)):
        raise HTTPException(403, "当前微信未绑定商家权限")
    return openid


def query_order(db: Session, order_id: int) -> Order:
    order = db.scalar(select(Order).options(selectinload(Order.items)).where(Order.id == order_id))
    if not order:
        raise HTTPException(404, "订单不存在")
    return order


@app.get("/api/health")
def health():
    return {"ok": True, "env": settings.app_env, "payment_mode": "mock" if settings.app_env == "development" else "wechat"}


@app.get("/api/products", response_model=list[ProductOut])
def products(db: Session = Depends(get_db)):
    return db.scalars(select(Product).where(Product.enabled.is_(True)).order_by(Product.id)).all()


@app.get("/api/admin/products", response_model=list[ProductOut])
def admin_products(_: str = Depends(require_admin), db: Session = Depends(get_db)):
    return db.scalars(select(Product).order_by(Product.category, Product.id)).all()


@app.post("/api/admin/products", response_model=ProductOut, status_code=201)
def create_product(payload: ProductCreateIn, _: str = Depends(require_admin), db: Session = Depends(get_db)):
    if db.scalar(select(Product.id).where(Product.name == payload.name)):
        raise HTTPException(409, "商品名称已存在")
    product = Product(**payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@app.patch("/api/admin/products/{product_id}", response_model=ProductOut)
def update_product(product_id: int, payload: ProductUpdateIn, _: str = Depends(require_admin), db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(404, "商品不存在")
    updates = payload.model_dump(exclude_unset=True)
    if "name" in updates and updates["name"] != product.name:
        if db.scalar(select(Product.id).where(Product.name == updates["name"])):
            raise HTTPException(409, "商品名称已存在")
    for field, value in updates.items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product


@app.post("/api/auth/admin-bind")
def bind_admin(phone: str, openid: str = Depends(openid_from_header), db: Session = Depends(get_db)):
    """Production calls this only after verifying the one-time WeChat phone credential server-side."""
    if phone not in settings.allowed_admin_phones:
        raise HTTPException(403, "该手机号不在商家白名单")
    existing = db.scalar(select(Admin).where(Admin.phone == phone))
    if existing and existing.openid != openid:
        raise HTTPException(409, "该手机号已绑定其他微信")
    if not existing:
        db.add(Admin(phone=phone, openid=openid))
        db.commit()
    return {"ok": True, "message": "商家权限绑定成功"}


@app.get("/api/delivery/quote")
def delivery_quote(latitude: float, longitude: float):
    distance = distance_provider.distance_km(settings.shop_latitude, settings.shop_longitude, latitude, longitude)
    return {"distance_km": distance, "delivery_fee": settings.delivery_fee, "distance_source": settings.delivery_provider}


@app.post("/api/orders", response_model=OrderOut)
def create_order(payload: OrderCreateIn, openid: str = Depends(openid_from_header), db: Session = Depends(get_db)):
    product_ids = [item.product_id for item in payload.items]
    products_by_id = {p.id: p for p in db.scalars(select(Product).where(Product.id.in_(product_ids), Product.enabled.is_(True))).all()}
    if len(products_by_id) != len(set(product_ids)):
        raise HTTPException(400, "存在已下架或不存在的商品")
    goods = sum((products_by_id[item.product_id].price * item.quantity for item in payload.items), Decimal("0.00"))
    distance = distance_provider.distance_km(settings.shop_latitude, settings.shop_longitude, payload.address.latitude, payload.address.longitude)
    order = Order(
        order_no=datetime.now().strftime("%Y%m%d%H%M%S") + uuid4().hex[:4].upper(), openid=openid,
        goods_amount=goods, delivery_fee=settings.delivery_fee, total_amount=goods + settings.delivery_fee,
        address=f"{payload.address.name} {payload.address.detail}", latitude=payload.address.latitude,
        longitude=payload.address.longitude, delivery_distance_km=distance, phone=payload.address.phone,
        remark=payload.remark,
    )
    order.items = [OrderItem(product_id=item.product_id, product_name=products_by_id[item.product_id].name,
                             unit_price=products_by_id[item.product_id].price, quantity=item.quantity) for item in payload.items]
    db.add(order)
    db.commit()
    return query_order(db, order.id)


@app.post("/api/orders/{order_id}/mock-payment-callback", response_model=OrderOut)
def mock_payment_callback(order_id: int, _: None = Depends(require_development), db: Session = Depends(get_db)):
    """Development stand-in for a verified WeChat payment callback; deliberately idempotent."""
    order = query_order(db, order_id)
    if order.payment_status == PaymentStatus.UNPAID:
        confirm_payment(db, order, "mock", f"mock-{order.order_no}")
        # In production this dispatch happens in a worker after the verified callback has returned 204.
        process_pending_prints(db, printer, order.id)
    return query_order(db, order_id)


@app.post("/api/payments/wechat/notify", status_code=204)
async def wechat_payment_notify(request: Request, db: Session = Depends(get_db)):
    """Real-payment callback: verify, persist payment once, then acknowledge without printing inline."""
    if settings.payment_provider != "wechat_v3":
        raise HTTPException(404, "Not Found")
    try:
        verifier = WechatPayV3CallbackVerifier(settings.wechat_pay_api_v3_key or "", settings.wechat_pay_platform_cert_path or "")
        payload = verifier.verify_and_decrypt(request.headers, await request.body())
        if payload.get("trade_state") != "SUCCESS" or payload.get("appid") != settings.wechat_pay_appid or payload.get("mchid") != settings.wechat_pay_mchid:
            raise PaymentVerificationError("unexpected payment callback payload")
        order = db.scalar(select(Order).where(Order.order_no == payload.get("out_trade_no")))
        if not order or payload.get("amount", {}).get("total") != int(order.total_amount * 100):
            raise PaymentVerificationError("order or amount verification failed")
        confirm_payment(db, order, "wechat_v3", payload["transaction_id"])
    except PaymentVerificationError as error:
        raise HTTPException(400, "invalid payment callback") from error
    return Response(status_code=204)


@app.post("/api/internal/jobs/dispatch-print-events")
def dispatch_print_events(_: None = Depends(require_job_token), db: Session = Depends(get_db)):
    """Invoke from a private scheduler/worker; never expose JOB_TOKEN to the mini-program."""
    return {"processed": process_pending_prints(db, printer)}


@app.get("/api/orders/mine", response_model=list[OrderOut])
def my_orders(openid: str = Depends(openid_from_header), db: Session = Depends(get_db)):
    return db.scalars(select(Order).options(selectinload(Order.items)).where(Order.openid == openid).order_by(Order.id.desc())).all()


@app.get("/api/admin/orders", response_model=list[OrderOut])
def admin_orders(_: str = Depends(require_admin), db: Session = Depends(get_db)):
    return db.scalars(select(Order).options(selectinload(Order.items)).where(Order.status != OrderStatus.PENDING_PAYMENT).order_by(Order.id.desc())).all()


@app.get("/api/admin/orders/{order_id}/history", response_model=list[OrderAuditOut])
def order_history(order_id: int, _: str = Depends(require_admin), db: Session = Depends(get_db)):
    query_order(db, order_id)
    return db.scalars(select(OrderAuditLog).where(OrderAuditLog.order_id == order_id).order_by(OrderAuditLog.id)).all()


@app.patch("/api/admin/orders/{order_id}/status", response_model=OrderOut)
def change_order_status(order_id: int, status: OrderStatus, admin_openid: str = Depends(require_admin), db: Session = Depends(get_db)):
    order = query_order(db, order_id)
    transitions = {OrderStatus.PAID: {OrderStatus.MAKING}, OrderStatus.MAKING: {OrderStatus.READY_FOR_DELIVERY}, OrderStatus.READY_FOR_DELIVERY: {OrderStatus.COMPLETED}}
    if status not in transitions.get(order.status, set()):
        raise HTTPException(400, f"不允许从 {order.status.value} 改为 {status.value}")
    previous_status = order.status.value
    order.status = status
    record_order_audit(db, order, "STATUS_CHANGED", actor_openid=admin_openid, from_status=previous_status, to_status=status.value)
    db.commit()
    return query_order(db, order_id)


@app.post("/api/admin/orders/{order_id}/reprint", response_model=OrderOut)
def reprint(order_id: int, admin_openid: str = Depends(require_admin), db: Session = Depends(get_db)):
    order = query_order(db, order_id)
    enqueue_receipt_print(db, order)
    record_order_audit(db, order, "REPRINT_REQUESTED", actor_openid=admin_openid)
    db.commit()
    process_pending_prints(db, printer, order.id)
    return query_order(db, order_id)
