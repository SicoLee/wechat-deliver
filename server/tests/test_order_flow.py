"""The core payment-to-fulfilment flow must remain safe as integrations evolve."""
import os
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///./data/test.db"
TEST_DB = Path("data/test.db")
TEST_DB.parent.mkdir(parents=True, exist_ok=True)
TEST_DB.unlink(missing_ok=True)

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.config import Settings  # noqa: E402
from app.models import EventStatus, OrderEvent  # noqa: E402


def setup_module():
    Base.metadata.create_all(engine)


def test_paid_order_is_visible_to_admin_and_can_progress():
    with TestClient(app) as client:
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
