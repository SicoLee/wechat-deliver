"""Road-distance providers; only this module knows a map vendor's wire format."""
from math import asin, cos, radians, sin, sqrt
from typing import Optional, Protocol
import httpx


class DeliveryProviderError(RuntimeError):
    """A map provider is unavailable or returned an unusable route response."""


class CyclingDistanceProvider(Protocol):
    def distance_km(self, origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float) -> float:
        ...


class MockCyclingDistanceProvider:
    """Development-only estimate; it is deliberately labelled simulated in the API response."""
    def distance_km(self, origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float) -> float:
        earth_km = 6371.0
        dlat, dlng = radians(dest_lat-origin_lat), radians(dest_lng-origin_lng)
        a = sin(dlat/2)**2 + cos(radians(origin_lat))*cos(radians(dest_lat))*sin(dlng/2)**2
        return round(2 * earth_km * asin(sqrt(a)) * 1.25, 2)


class TencentBicyclingDistanceProvider:
    endpoint = "https://apis.map.qq.com/ws/direction/v1/bicycling/"

    def __init__(self, key: str, timeout_seconds: float = 5.0, client: Optional[httpx.Client] = None):
        self.key = key
        self.timeout_seconds = timeout_seconds
        self.client = client or httpx.Client()

    def distance_km(self, origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float) -> float:
        try:
            response = self.client.get(
                self.endpoint,
                params={"key": self.key, "from": f"{origin_lat},{origin_lng}", "to": f"{dest_lat},{dest_lng}"},
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
            routes = payload.get("result", {}).get("routes", []) if payload.get("status") == 0 else []
            if not routes or not isinstance(routes[0].get("distance"), (int, float)):
                raise ValueError("missing bicycling route")
            return round(routes[0]["distance"] / 1000, 2)
        except (httpx.HTTPError, ValueError, TypeError) as error:
            # Deliberately do not expose provider responses or the map key to callers.
            raise DeliveryProviderError("地图距离服务暂不可用，请稍后重试") from error


def build_distance_provider(provider: str, key: Optional[str], timeout_seconds: float) -> CyclingDistanceProvider:
    if provider == "mock":
        return MockCyclingDistanceProvider()
    if provider == "tencent_bicycling" and key:
        return TencentBicyclingDistanceProvider(key, timeout_seconds)
    raise ValueError("Invalid delivery provider configuration")
