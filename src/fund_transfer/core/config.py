from __future__ import annotations
import os
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, field_validator
from pydantic_settings import BaseSettings


class ExchangeRateConfig(BaseModel):
    supported_currencies: list[str]
    max_transfer_amounts: dict[str, Decimal]
    rates: dict[str, dict[str, Decimal]]

    @field_validator("max_transfer_amounts", mode="before")
    @classmethod
    def parse_max_amounts(cls, v: Any) -> Any:
        if isinstance(v, dict):
            return {k: Decimal(str(val)) for k, val in v.items()}
        return v

    @field_validator("rates", mode="before")
    @classmethod
    def parse_rates(cls, v: Any) -> Any:
        if isinstance(v, dict):
            return {
                from_cur: {to_cur: Decimal(str(rate)) for to_cur, rate in rates.items()}
                for from_cur, rates in v.items()
            }
        return v


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://fund_transfer:fund_transfer_pass@localhost:5432/fund_transfer"
    JWKS_URI: str = "https://your-idp.example.com/.well-known/jwks.json"
    JWT_AUDIENCE: str = "fund-transfer-service"
    EXCHANGE_RATES_CONFIG: str = "config/exchange_rates.yaml"
    LOG_LEVEL: str = "INFO"
    SERVICE_NAME: str = "fund-transfer-service"
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4317"

    _exchange_rate_config: ExchangeRateConfig | None = None

    def get_exchange_rate_config(self) -> ExchangeRateConfig:
        if self._exchange_rate_config is None:
            config_path = Path(self.EXCHANGE_RATES_CONFIG)
            if not config_path.is_absolute():
                config_path = Path(os.getcwd()) / config_path
            with open(config_path) as f:
                data = yaml.safe_load(f)
            object.__setattr__(self, "_exchange_rate_config", ExchangeRateConfig(**data))
        return self._exchange_rate_config  # type: ignore[return-value]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
