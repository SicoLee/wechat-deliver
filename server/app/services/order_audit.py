from typing import Optional
from sqlalchemy.orm import Session
from ..models import Order, OrderAuditLog


def record_order_audit(
    db: Session,
    order: Order,
    action: str,
    actor_openid: Optional[str] = None,
    from_status: Optional[str] = None,
    to_status: Optional[str] = None,
) -> None:
    db.add(OrderAuditLog(
        order_id=order.id, action=action, actor_openid=actor_openid,
        from_status=from_status, to_status=to_status,
    ))
