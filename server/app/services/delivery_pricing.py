from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable


class DeliveryUnavailable(ValueError):
    pass


@dataclass(frozen=True)
class DeliveryQuote:
    distance_km: float
    delivery_fee: Decimal


def calculate_delivery_fee(distance_km: float, mode: str, fixed_fee: Decimal, tiers: Iterable[tuple[float, Decimal]]) -> Decimal:
    if mode == "fixed":
        return fixed_fee
    for max_km, fee in tiers:
        if distance_km <= max_km:
            return fee
    raise DeliveryUnavailable("收货地址超出配送范围")
