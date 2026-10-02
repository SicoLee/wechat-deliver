from decimal import Decimal
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_env: str = "development"
    database_url: str = "sqlite:///./data/dev.db"
    shop_name: str = "妈妈的店"
    shop_latitude: float = 26.45
    shop_longitude: float = 106.98
    delivery_fee: Decimal = Decimal("2.00")
    admin_phones: str = "18785409634,18285424586"

    @property
    def allowed_admin_phones(self) -> set[str]:
        return {phone.strip() for phone in self.admin_phones.split(",") if phone.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
