from __future__ import annotations


class FundTransferError(Exception):
    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, error_code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if error_code is not None:
            self.error_code = error_code


class ValidationError(FundTransferError):
    status_code = 400
    error_code = "VALIDATION_ERROR"


class UnsupportedCurrencyError(FundTransferError):
    status_code = 400
    error_code = "UNSUPPORTED_CURRENCY"


class NotFoundError(FundTransferError):
    status_code = 404
    error_code = "ACCOUNT_NOT_FOUND"


class ForbiddenError(FundTransferError):
    status_code = 403
    error_code = "FORBIDDEN"


class InsufficientFundsError(FundTransferError):
    status_code = 422
    error_code = "INSUFFICIENT_FUNDS"


class LimitExceededError(FundTransferError):
    status_code = 422
    error_code = "TRANSFER_LIMIT_EXCEEDED"


class IdempotencyConflictError(FundTransferError):
    status_code = 409
    error_code = "IDEMPOTENCY_CONFLICT"


class AccountHasBalanceError(FundTransferError):
    status_code = 400
    error_code = "ACCOUNT_HAS_BALANCE"


class DatabaseError(FundTransferError):
    status_code = 500
    error_code = "DATABASE_ERROR"
