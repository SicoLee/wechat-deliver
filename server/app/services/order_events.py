"""Transactional-outbox primitives. Production workers can poll pending events safely."""
from datetime import datetime
from typing import Optional
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import EventStatus, Order, OrderEvent, PrintStatus
from .printer import MockPrinter


PRINT_ORDER = "PRINT_ORDER"


def enqueue_receipt_print(db: Session, order: Order) -> OrderEvent:
    event = OrderEvent(order_id=order.id, event_type=PRINT_ORDER, idempotency_key=uuid4().hex)
    db.add(event)
    return event


def process_pending_prints(db: Session, printer: MockPrinter, order_id: Optional[int] = None) -> int:
    query = select(OrderEvent).where(OrderEvent.event_type == PRINT_ORDER, OrderEvent.status == EventStatus.PENDING)
    if order_id is not None:
        query = query.where(OrderEvent.order_id == order_id)
    events = db.scalars(query).all()
    for event in events:
        event.attempts += 1
        order = db.get(Order, event.order_id)
        result = printer.print_order(order.order_no, event.idempotency_key)
        if result.success:
            event.status, event.processed_at, event.last_error = EventStatus.SUCCEEDED, datetime.now(), None
            order.print_status = PrintStatus.SUCCESS
        else:
            event.status, event.last_error = EventStatus.FAILED, result.message
            order.print_status = PrintStatus.FAILED
    db.commit()
    return len(events)
