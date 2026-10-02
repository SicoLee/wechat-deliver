from decimal import Decimal
from functools import lru_cache
import json
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = "sqlite:///./data/dev.db"
    shop_name: str = "妈妈的店"
    shop_latitude: float = 26.45
    shop_longitude: float = 106.98
    delivery_fee: Decimal = Decimal("2.00")
    delivery_pricing_mode: str = "fixed"
    delivery_distance_tiers_json: str = ""
    delivery_provider: str = "mock"
    tencent_map_key: Optional[str] = None
    external_request_timeout_seconds: float = 5.0
    payment_provider: str = "mock"
    wechat_pay_mchid: Optional[str] = None
    wechat_pay_appid: Optional[str] = None
    wechat_pay_api_v3_key: Optional[str] = None
    wechat_pay_platform_cert_path: Optional[str] = None
    job_token: Optional[str] = None
    worker_poll_interval_seconds: float = Field(default=5.0, gt=0, le=300)
    admin_phones: str = "18785409634,18285424586"

    @property
    def allowed_admin_phones(self) -> set[str]:
        return {phone.strip() for phone in self.admin_phones.split(",") if phone.strip()}

    def validate_runtime(self) -> None:
        if self.app_env not in {"development", "test", "production"}:
            raise ValueError("APP_ENV must be development, test, or production")
        if self.app_env == "production":
            raise ValueError(
                "Production startup is blocked until real WeChat Pay, Tencent Map, and cloud-printer providers are configured."
            )
        if self.delivery_provider not in {"mock", "tencent_bicycling"}:
            raise ValueError("DELIVERY_PROVIDER must be mock or tencent_bicycling")
        if self.delivery_provider == "tencent_bicycling" and not self.tencent_map_key:
            raise ValueError("TENCENT_MAP_KEY is required for tencent_bicycling")
        if self.delivery_pricing_mode not in {"fixed", "tiered"}:
            raise ValueError("DELIVERY_PRICING_MODE must be fixed or tiered")
        if self.delivery_pricing_mode == "tiered":
            self.delivery_distance_tiers()
        if self.payment_provider not in {"mock", "wechat_v3"}:
            raise ValueError("PAYMENT_PROVIDER must be mock or wechat_v3")
        if self.payment_provider == "wechat_v3":
            required = (self.wechat_pay_mchid, self.wechat_pay_appid, self.wechat_pay_api_v3_key, self.wechat_pay_platform_cert_path)
            if not all(required):
                raise ValueError("WeChat Pay v3 configuration is incomplete")

    def delivery_distance_tiers(self) -> list[tuple[float, Decimal]]:
        try:
            raw_tiers = json.loads(self.delivery_distance_tiers_json)
            tiers = [(float(item["max_km"]), Decimal(str(item["fee"]))) for item in raw_tiers]
        except (TypeError, ValueError, KeyError, json.JSONDecodeError) as error:
            raise ValueError("DELIVERY_DISTANCE_TIERS_JSON must be a valid tier list") from error
        if not tiers or any(max_km <= 0 or fee < 0 for max_km, fee in tiers):
            raise ValueError("delivery tiers must contain positive distances and non-negative fees")
        if [max_km for max_km, _ in tiers] != sorted(max_km for max_km, _ in tiers):
            raise ValueError("delivery tiers must be sorted by max_km")
        return tiers


@lru_cache
def get_settings() -> Settings:
    return Settings()
