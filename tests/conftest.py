from __future__ import annotations

import os
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

# Set test environment variables before any imports
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://fund_transfer:fund_transfer_pass@localhost:5432/fund_transfer_test")
os.environ.setdefault("JWKS_URI", "https://test-idp.example.com/.well-known/jwks.json")
os.environ.setdefault("JWT_AUDIENCE", "fund-transfer-service")
os.environ.setdefault("EXCHANGE_RATES_CONFIG", "config/exchange_rates.yaml")
os.environ.setdefault("LOG_LEVEL", "DEBUG")
os.environ.setdefault("SERVICE_NAME", "fund-transfer-test")

from fund_transfer.core.config import ExchangeRateConfig


@pytest.fixture
def exchange_rate_config() -> ExchangeRateConfig:
    return ExchangeRateConfig(
        supported_currencies=["EUR", "USD", "GBP", "CHF", "RON"],
        max_transfer_amounts={
            "EUR": Decimal("1000000.0000"),
            "USD": Decimal("1000000.0000"),
            "GBP": Decimal("1000000.0000"),
            "CHF": Decimal("1000000.0000"),
            "RON": Decimal("5000000.0000"),
        },
        rates={
            "EUR": {"USD": Decimal("1.08500000"), "GBP": Decimal("0.85700000"), "CHF": Decimal("0.97200000"), "RON": Decimal("4.97000000")},
            "USD": {"EUR": Decimal("0.92200000"), "GBP": Decimal("0.78900000"), "CHF": Decimal("0.89500000"), "RON": Decimal("4.57900000")},
            "GBP": {"EUR": Decimal("1.16700000"), "USD": Decimal("1.26800000"), "CHF": Decimal("1.13400000"), "RON": Decimal("5.80100000")},
            "CHF": {"EUR": Decimal("1.02900000"), "USD": Decimal("1.11800000"), "GBP": Decimal("0.88200000"), "RON": Decimal("5.11200000")},
            "RON": {"EUR": Decimal("0.20100000"), "USD": Decimal("0.21800000"), "GBP": Decimal("0.17200000"), "CHF": Decimal("0.19600000")},
        },
    )
