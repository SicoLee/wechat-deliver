"""Distance provider seam. Replace MockCyclingDistanceProvider with Tencent implementation in production."""
from math import asin, cos, radians, sin, sqrt


class MockCyclingDistanceProvider:
    """Development-only estimate; it is deliberately labelled simulated in the API response."""
    def distance_km(self, origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float) -> float:
        earth_km = 6371.0
        dlat, dlng = radians(dest_lat-origin_lat), radians(dest_lng-origin_lng)
        a = sin(dlat/2)**2 + cos(radians(origin_lat))*cos(radians(dest_lat))*sin(dlng/2)**2
        return round(2 * earth_km * asin(sqrt(a)) * 1.25, 2)
