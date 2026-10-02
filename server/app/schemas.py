from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field
from .models import OrderStatus, PrintStatus


class CartItemIn(BaseModel):
    product_id: int
    quantity: int = Field(gt=0, le=99)


class AddressIn(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    detail: str = Field(min_length=1, max_length=200)
    latitude: float
    longitude: float
    phone: str = Field(min_length=6, max_length=20)


class OrderCreateIn(BaseModel):
    items: list[CartItemIn] = Field(min_length=1)
    address: AddressIn
    remark: Optional[str] = Field(default=None, max_length=300)


class ProductOut(BaseModel):
    id: int
    name: str
    price: Decimal
    image: Optional[str]
    category: str
    model_config = {"from_attributes": True}


class OrderItemOut(BaseModel):
    product_id: int
    product_name: str
    unit_price: Decimal
    quantity: int
    model_config = {"from_attributes": True}


class OrderOut(BaseModel):
    id: int
    order_no: str
    goods_amount: Decimal
    delivery_fee: Decimal
    total_amount: Decimal
    address: str
    delivery_distance_km: float
    phone: str
    remark: Optional[str]
    status: OrderStatus
    print_status: PrintStatus
    created_at: datetime
    items: list[OrderItemOut]
    model_config = {"from_attributes": True}
