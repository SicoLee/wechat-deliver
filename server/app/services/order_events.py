"""Transactional-outbox primitives. Production workers can poll pending events safely."""
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4
from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from ..models import EventStatus, Order, OrderEvent, PrintStatus
from .printer import Printer


PRINT_ORDER = "PRINT_ORDER"


def enqueue_receipt_print(db: Session, order: Order) -> OrderEvent:
    event = OrderEvent(order_id=order.id, event_type=PRINT_ORDER, idempotency_key=uuid4().hex)
    db.add(event)
    return event


def process_pending_prints(db: Session, printer: Printer, order_id: Optional[int] = None, max_attempts: int = 5, retry_delay_seconds: float = 30.0) -> int:
    now = datetime.now()
    query = select(OrderEvent).where(
        OrderEvent.event_type == PRINT_ORDER,
        OrderEvent.status == EventStatus.PENDING,
        or_(OrderEvent.next_attempt_at.is_(None), OrderEvent.next_attempt_at <= now),
    )
    if order_id is not None:
        query = query.where(OrderEvent.order_id == order_id)
    events = db.scalars(query).all()
    for event in events:
        event.attempts += 1
        order = db.get(Order, event.order_id)
        result = printer.print_order(order.order_no, event.idempotency_key)
        if result.success:
            event.status, event.processed_at, event.last_error, event.next_attempt_at = EventStatus.SUCCEEDED, now, None, None
            order.print_status = PrintStatus.SUCCESS
        else:
            event.last_error = result.message
            if event.attempts >= max_attempts:
                event.status, event.next_attempt_at = EventStatus.FAILED, None
            else:
                event.next_attempt_at = now + timedelta(seconds=retry_delay_seconds * (2 ** (event.attempts - 1)))
            order.print_status = PrintStatus.FAILED
    db.commit()
    return len(events)
