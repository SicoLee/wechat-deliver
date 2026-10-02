from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base


class OrderStatus(str, Enum):
    PENDING_PAYMENT = "PENDING_PAYMENT"
    PAID = "PAID"
    MAKING = "MAKING"
    READY_FOR_DELIVERY = "READY_FOR_DELIVERY"
    COMPLETED = "COMPLETED"


class PrintStatus(str, Enum):
    NOT_PRINTED = "NOT_PRINTED"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class PaymentStatus(str, Enum):
    UNPAID = "UNPAID"
    PAID = "PAID"


class EventStatus(str, Enum):
    PENDING = "PENDING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    image: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    category: Mapped[str] = mapped_column(String(40), default="招牌")
    enabled: Mapped[bool] = mapped_column(default=True)


class Admin(Base):
    __tablename__ = "admins"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    openid: Mapped[str] = mapped_column(String(80), unique=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (UniqueConstraint("openid", "client_request_id", name="uq_orders_openid_client_request_id"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_no: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    openid: Mapped[str] = mapped_column(String(80), index=True)
    # Non-null keys are supplied once per checkout and make client retries safe.
    client_request_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    goods_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    delivery_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    address: Mapped[str] = mapped_column(Text)
    latitude: Mapped[float] = mapped_column()
    longitude: Mapped[float] = mapped_column()
    delivery_distance_km: Mapped[float] = mapped_column()
    phone: Mapped[str] = mapped_column(String(20))
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[OrderStatus] = mapped_column(SqlEnum(OrderStatus), default=OrderStatus.PENDING_PAYMENT)
    payment_status: Mapped[PaymentStatus] = mapped_column(SqlEnum(PaymentStatus), default=PaymentStatus.UNPAID)
    payment_provider: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    payment_transaction_id: Mapped[Optional[str]] = mapped_column(String(80), unique=True, nullable=True)
    print_status: Mapped[PrintStatus] = mapped_column(SqlEnum(PrintStatus), default=PrintStatus.NOT_PRINTED)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")
    events: Mapped[list["OrderEvent"]] = relationship(back_populates="order", cascade="all, delete-orphan")
    audit_logs: Mapped[list["OrderAuditLog"]] = relationship(back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    product_id: Mapped[int] = mapped_column(Integer)
    product_name: Mapped[str] = mapped_column(String(80))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    quantity: Mapped[int] = mapped_column(Integer)
    order: Mapped[Order] = relationship(back_populates="items")


class OrderEvent(Base):
    """Durable outbox/audit trail for side effects such as receipt printing."""
    __tablename__ = "order_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(40))
    idempotency_key: Mapped[str] = mapped_column(String(64), unique=True)
    status: Mapped[EventStatus] = mapped_column(SqlEnum(EventStatus), default=EventStatus.PENDING)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    next_attempt_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    order: Mapped[Order] = relationship(back_populates="events")


class OrderAuditLog(Base):
    """Append-only operational history; intentionally separate from retriable outbox events."""
    __tablename__ = "order_audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    action: Mapped[str] = mapped_column(String(40))
    actor_openid: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    from_status: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    to_status: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    order: Mapped[Order] = relationship(back_populates="audit_logs")
