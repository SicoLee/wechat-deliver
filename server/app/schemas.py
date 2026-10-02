from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, model_validator
from .models import OrderStatus, PaymentStatus, PrintStatus


class CartItemIn(BaseModel):
    product_id: int
    quantity: int = Field(gt=0, le=99)


class AddressIn(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    detail: str = Field(min_length=1, max_length=200)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    phone: str = Field(min_length=6, max_length=20)


class OrderCreateIn(BaseModel):
    items: list[CartItemIn] = Field(min_length=1, max_length=30)
    address: AddressIn
    remark: Optional[str] = Field(default=None, max_length=300)

    @model_validator(mode="after")
    def product_ids_are_unique(self):
        product_ids = [item.product_id for item in self.items]
        if len(product_ids) != len(set(product_ids)):
            raise ValueError("同一商品只能出现在购物车中一次")
        return self


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
    payment_status: PaymentStatus
    print_status: PrintStatus
    created_at: datetime
    items: list[OrderItemOut]
    model_config = {"from_attributes": True}


class OrderAuditOut(BaseModel):
    action: str
    actor_openid: Optional[str]
    from_status: Optional[str]
    to_status: Optional[str]
    created_at: datetime
    model_config = {"from_attributes": True}
