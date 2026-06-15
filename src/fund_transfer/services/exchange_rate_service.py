from __future__ import annotations

from decimal import Decimal

from fund_transfer.core.config import ExchangeRateConfig, get_settings
from fund_transfer.core.exceptions import UnsupportedCurrencyError, ValidationError


class ExchangeRateService:
    def __init__(self, config: ExchangeRateConfig | None = None) -> None:
        if config is None:
            config = get_settings().get_exchange_rate_config()
        self._config = config

    def validate_currency(self, code: str) -> None:
        if code not in self._config.supported_currencies:
            supported = ", ".join(self._config.supported_currencies)
            raise UnsupportedCurrencyError(
                f"Currency '{code}' is not supported. Supported currencies: {supported}.",
                error_code="UNSUPPORTED_CURRENCY",
            )

    def get_rate(self, from_currency: str, to_currency: str) -> Decimal:
        if from_currency == to_currency:
            return Decimal("1")
        self.validate_currency(from_currency)
        self.validate_currency(to_currency)
        try:
            return self._config.rates[from_currency][to_currency]
        except KeyError:
            raise ValidationError(
                f"No exchange rate configured for {from_currency} → {to_currency}.",
                error_code="UNSUPPORTED_CURRENCY",
            )

    def get_max_transfer_amount(self, currency: str) -> Decimal:
        self.validate_currency(currency)
        return self._config.max_transfer_amounts[currency]
