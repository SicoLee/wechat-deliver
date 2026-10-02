from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Integer, Numeric, String, Text, func
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
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_no: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    openid: Mapped[str] = mapped_column(String(80), index=True)
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
    print_status: Mapped[PrintStatus] = mapped_column(SqlEnum(PrintStatus), default=PrintStatus.NOT_PRINTED)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    product_id: Mapped[int] = mapped_column(Integer)
    product_name: Mapped[str] = mapped_column(String(80))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    quantity: Mapped[int] = mapped_column(Integer)
    order: Mapped[Order] = relationship(back_populates="items")
