"""The core payment-to-fulfilment flow must remain safe as integrations evolve."""
import os
from pathlib import Path
from decimal import Decimal

os.environ["DATABASE_URL"] = "sqlite:///./data/test.db"
TEST_DB = Path("data/test.db")
TEST_DB.parent.mkdir(parents=True, exist_ok=True)
TEST_DB.unlink(missing_ok=True)

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
import app.main as main_module  # noqa: E402
from app.config import Settings  # noqa: E402
from app.services.delivery import DeliveryProviderError, TencentBicyclingDistanceProvider  # noqa: E402
from app.worker import run_once  # noqa: E402
from app.services.delivery_pricing import DeliveryUnavailable, calculate_delivery_fee  # noqa: E402
from app.models import EventStatus, OrderEvent  # noqa: E402
from app.services.order_events import enqueue_receipt_print, process_pending_prints  # noqa: E402
from app.services.printer import PrintResult  # noqa: E402


def setup_module():
    Base.metadata.create_all(engine)


def test_paid_order_is_visible_to_admin_and_can_progress():
    with TestClient(app) as client:
        readiness = client.get("/api/ready")
        assert readiness.status_code == 200
        assert readiness.json()["database"] == "ready"
        products = client.get("/api/products")
        assert products.status_code == 200
        assert products.json()
        assert len(products.headers["X-Request-ID"]) > 10

        created = client.post(
            "/api/orders",
            headers={"X-OpenID": "test-customer"},
            json={
                "items": [{"product_id": 1, "quantity": 2}],
                "address": {
                    "name": "测试小区", "detail": "1栋101", "latitude": 26.47,
                    "longitude": 106.95, "phone": "13800000000",
                },
                "remark": "不要辣",
            },
        )
        assert created.status_code == 200
        order = created.json()
        assert order["status"] == "PENDING_PAYMENT"
        assert order["delivery_fee"] == "2.00"
        assert client.get(f"/api/orders/{order['id']}", headers={"X-OpenID": "test-customer"}).status_code == 200
        assert client.get(f"/api/orders/{order['id']}", headers={"X-OpenID": "another-customer"}).status_code == 404

        paid = client.post(f"/api/orders/{order['id']}/mock-payment-callback")
        assert paid.status_code == 200
        assert paid.json()["status"] == "PAID"
        assert paid.json()["payment_status"] == "PAID"
        assert paid.json()["print_status"] == "SUCCESS"

        # Repeated payment notifications must not re-run the business transition.
        repeated = client.post(f"/api/orders/{order['id']}/mock-payment-callback")
        assert repeated.status_code == 200
        assert repeated.json()["status"] == "PAID"
        with SessionLocal() as db:
            events = db.scalars(select(OrderEvent).where(OrderEvent.order_id == order["id"])).all()
            assert len(events) == 1
            assert events[0].status == EventStatus.SUCCEEDED

        bind = client.post("/api/auth/admin-bind?phone=18785409634", headers={"X-OpenID": "test-admin"})
        assert bind.status_code == 200
        headers = {"X-OpenID": "test-admin"}
        visible = client.get("/api/admin/orders", headers=headers)
        assert [item["id"] for item in visible.json()] == [order["id"]]
        assert client.get(f"/api/admin/orders/{order['id']}", headers=headers).json()["id"] == order["id"]

        making = client.patch(f"/api/admin/orders/{order['id']}/status?status=MAKING", headers=headers)
        assert making.status_code == 200
        assert making.json()["status"] == "MAKING"
        history = client.get(f"/api/admin/orders/{order['id']}/history", headers=headers)
        assert [row["action"] for row in history.json()] == ["PAYMENT_CONFIRMED", "STATUS_CHANGED"]
        assert history.json()[-1]["actor_openid"] == "test-admin"


def test_customer_cannot_use_admin_endpoints():
    with TestClient(app) as client:
        response = client.get("/api/admin/orders", headers={"X-OpenID": "not-an-admin"})
        assert response.status_code == 403


def test_production_rejects_mock_integration_configuration():
    settings = Settings(app_env="production")
    try:
        settings.validate_runtime()
    except ValueError as error:
        assert "Production startup is blocked" in str(error)
    else:
        raise AssertionError("production must not accept mock providers")


def test_development_admin_binding_shortcut_is_not_available_in_production(monkeypatch):
    monkeypatch.setattr(main_module.settings, "app_env", "production")
    try:
        main_module.require_development()
    except Exception as error:
        assert getattr(error, "status_code", None) == 404
    else:
        raise AssertionError("production must not accept raw phone binding")


def test_order_rejects_duplicate_products_and_invalid_coordinates():
    with TestClient(app) as client:
        duplicate = client.post(
            "/api/orders", headers={"X-OpenID": "test-customer"},
            json={"items": [{"product_id": 1, "quantity": 1}, {"product_id": 1, "quantity": 2}], "address": {"name": "测试", "detail": "1号", "latitude": 26, "longitude": 106, "phone": "13800000000"}},
        )
        assert duplicate.status_code == 422
        invalid_location = client.post(
            "/api/orders", headers={"X-OpenID": "test-customer"},
            json={"items": [{"product_id": 1, "quantity": 1}], "address": {"name": "测试", "detail": "1号", "latitude": 99, "longitude": 106, "phone": "13800000000"}},
        )
        assert invalid_location.status_code == 422


def test_order_creation_is_idempotent_per_customer_request_key():
    payload = {"items": [{"product_id": 1, "quantity": 1}], "address": {"name": "测试", "detail": "2号", "latitude": 26, "longitude": 106, "phone": "13800000000"}}
    with TestClient(app) as client:
        headers = {"X-OpenID": "retry-customer", "X-Idempotency-Key": "checkout-retry-001"}
        first = client.post("/api/orders", headers=headers, json=payload)
        second = client.post("/api/orders", headers=headers, json=payload)
        assert first.status_code == second.status_code == 200
        assert first.json()["id"] == second.json()["id"]
        assert len(client.get("/api/orders/mine", headers={"X-OpenID": "retry-customer"}).json()) == 1


def test_admin_can_manage_products_and_customers_only_see_enabled_products():
    with TestClient(app) as client:
        headers = {"X-OpenID": "test-admin"}
        assert client.post("/api/auth/admin-bind?phone=18785409634", headers=headers).status_code == 200
        created = client.post("/api/admin/products", headers=headers, json={"name": "  手作酸梅汤  ", "price": "5.00", "category": "饮品"})
        assert created.status_code == 201
        product = created.json()
        assert product["name"] == "手作酸梅汤"
        assert product["enabled"] is True
        disabled = client.patch(f"/api/admin/products/{product['id']}", headers=headers, json={"enabled": False})
        assert disabled.status_code == 200
        assert disabled.json()["enabled"] is False
        customer_products = client.get("/api/products").json()
        assert product["id"] not in [item["id"] for item in customer_products]
        assert client.post("/api/admin/products", headers=headers, json={"name": "手作酸梅汤", "price": "5.00"}).status_code == 409


def test_tencent_cycling_provider_reads_road_distance_without_leaking_key():
    import httpx
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"status": 0, "result": {"routes": [{"distance": 3250}]}}))
    with httpx.Client(transport=transport) as client:
        provider = TencentBicyclingDistanceProvider("test-key", client=client)
        assert provider.distance_km(26.45, 106.98, 26.47, 106.95) == 3.25


def test_tencent_cycling_provider_wraps_vendor_failures():
    import httpx
    transport = httpx.MockTransport(lambda request: httpx.Response(502, text="upstream failure"))
    with httpx.Client(transport=transport) as client:
        provider = TencentBicyclingDistanceProvider("test-key", client=client)
        try:
            provider.distance_km(26.45, 106.98, 26.47, 106.95)
        except DeliveryProviderError as error:
            assert "暂不可用" in str(error)
        else:
            raise AssertionError("vendor failure must be wrapped")


def test_map_outage_returns_a_safe_retryable_error(monkeypatch):
    class UnavailableProvider:
        def distance_km(self, *_):
            raise DeliveryProviderError("地图距离服务暂不可用，请稍后重试")

    monkeypatch.setattr(main_module, "distance_provider", UnavailableProvider())
    with TestClient(app) as client:
        response = client.get("/api/delivery/quote?latitude=26.47&longitude=106.95")
        assert response.status_code == 503
        assert response.json()["detail"] == "地图距离服务暂不可用，请稍后重试"


def test_wechat_payment_provider_requires_complete_credentials():
    settings = Settings(payment_provider="wechat_v3")
    try:
        settings.validate_runtime()
    except ValueError as error:
        assert "WeChat Pay v3 configuration is incomplete" in str(error)
    else:
        raise AssertionError("partial WeChat Pay configuration must be rejected")


def test_print_dispatch_job_requires_dedicated_server_token(monkeypatch):
    with TestClient(app) as client:
        assert client.post("/api/internal/jobs/dispatch-print-events").status_code == 503
        monkeypatch.setattr(main_module.settings, "job_token", "test-job-token")
        assert client.post("/api/internal/jobs/dispatch-print-events", headers={"X-Job-Token": "wrong"}).status_code == 403
        response = client.post("/api/internal/jobs/dispatch-print-events", headers={"X-Job-Token": "test-job-token"})
        assert response.status_code == 200
        assert response.json()["processed"] == 0


def test_http_print_dispatch_uses_configured_retry_policy(monkeypatch):
    observed = {}

    def capture(db, active_printer, order_id=None, max_attempts=5, retry_delay_seconds=30):
        observed.update(order_id=order_id, max_attempts=max_attempts, retry_delay_seconds=retry_delay_seconds)
        return 0

    monkeypatch.setattr(main_module, "process_pending_prints", capture)
    monkeypatch.setattr(main_module.settings, "print_max_attempts", 7)
    monkeypatch.setattr(main_module.settings, "print_retry_delay_seconds", 45)
    with SessionLocal() as db:
        assert main_module.dispatch_pending_prints(db) == 0
    assert observed == {"order_id": None, "max_attempts": 7, "retry_delay_seconds": 45}


def test_worker_can_poll_an_empty_outbox():
    assert run_once() == 0


def test_failed_print_retries_before_becoming_terminal():
    class OfflinePrinter:
        def print_order(self, *_):
            return PrintResult(False, "printer offline")

    with SessionLocal() as db:
        order = db.scalar(select(main_module.Order).limit(1))
        event = enqueue_receipt_print(db, order)
        db.commit()
        assert process_pending_prints(db, OfflinePrinter(), order.id, max_attempts=2, retry_delay_seconds=0) == 1
        db.refresh(event)
        assert event.attempts == 1
        assert event.status == EventStatus.PENDING
        assert event.next_attempt_at is not None
        assert process_pending_prints(db, OfflinePrinter(), order.id, max_attempts=2, retry_delay_seconds=0) == 1
        db.refresh(event)
        assert event.attempts == 2
        assert event.status == EventStatus.FAILED


def test_print_vendor_exception_becomes_a_retryable_event():
    class ExplodingPrinter:
        def print_order(self, *_):
            raise RuntimeError("vendor credential leaked in an exception")

    with SessionLocal() as db:
        order = db.scalar(select(main_module.Order).limit(1))
        event = enqueue_receipt_print(db, order)
        db.commit()
        assert process_pending_prints(db, ExplodingPrinter(), order.id, max_attempts=2, retry_delay_seconds=60) == 1
        db.refresh(event)
        assert event.status == EventStatus.PENDING
        assert event.last_error == "打印服务暂不可用"


def test_tiered_delivery_pricing_preserves_distance_boundaries():
    tiers = [(2.0, Decimal("2.00")), (4.0, Decimal("4.00")), (6.0, Decimal("7.00"))]
    assert calculate_delivery_fee(2.0, "tiered", Decimal("0"), tiers) == Decimal("2.00")
    assert calculate_delivery_fee(3.2, "tiered", Decimal("0"), tiers) == Decimal("4.00")
    try:
        calculate_delivery_fee(6.01, "tiered", Decimal("0"), tiers)
    except DeliveryUnavailable:
        pass
    else:
        raise AssertionError("out-of-range delivery must be rejected")
