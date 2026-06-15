from __future__ import annotations

from decimal import Decimal

import pytest

from fund_transfer.core.exceptions import UnsupportedCurrencyError, ValidationError
from fund_transfer.services.exchange_rate_service import ExchangeRateService


def test_same_currency_rate_is_one(exchange_rate_config):
    svc = ExchangeRateService(exchange_rate_config)
    assert svc.get_rate("EUR", "EUR") == Decimal("1")


def test_cross_currency_rate_returned_as_decimal(exchange_rate_config):
    svc = ExchangeRateService(exchange_rate_config)
    rate = svc.get_rate("EUR", "USD")
    assert rate == Decimal("1.08500000")
    assert isinstance(rate, Decimal)


def test_unsupported_currency_raises(exchange_rate_config):
    svc = ExchangeRateService(exchange_rate_config)
    with pytest.raises(UnsupportedCurrencyError):
        svc.get_rate("EUR", "XYZ")


def test_all_rates_loaded_as_decimal(exchange_rate_config):
    svc = ExchangeRateService(exchange_rate_config)
    for from_cur, rates in exchange_rate_config.rates.items():
        for to_cur, rate in rates.items():
            assert isinstance(rate, Decimal), f"Rate {from_cur}->{to_cur} is not Decimal"


def test_get_max_transfer_amount_returns_decimal(exchange_rate_config):
    svc = ExchangeRateService(exchange_rate_config)
    max_amount = svc.get_max_transfer_amount("EUR")
    assert max_amount == Decimal("1000000.0000")
    assert isinstance(max_amount, Decimal)


def test_validate_currency_valid(exchange_rate_config):
    svc = ExchangeRateService(exchange_rate_config)
    svc.validate_currency("EUR")


def test_validate_currency_invalid(exchange_rate_config):
    svc = ExchangeRateService(exchange_rate_config)
    with pytest.raises(UnsupportedCurrencyError):
        svc.validate_currency("XYZ")
