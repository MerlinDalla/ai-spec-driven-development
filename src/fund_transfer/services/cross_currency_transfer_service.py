from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
import inspect

import structlog
from opentelemetry import trace
from prometheus_client import Counter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fund_transfer.core.config import get_settings
from fund_transfer.core.exceptions import (
    ForbiddenError,
    IdempotencyConflictError,
    InsufficientFundsError,
    NotFoundError,
    RateDeviationError,
    StaleRateError,
    TransferLimitExceededError,
    UnsupportedCurrencyPairError,
)
from fund_transfer.models.account import Account, AccountStatus
from fund_transfer.models.audit_log import OperationType
from fund_transfer.models.transfer import Transfer, TransferStatus
from fund_transfer.repositories.fx_rate_repository import FxRateRepository
from fund_transfer.repositories.transfer_repository import TransferRepository
from fund_transfer.schemas.fx import CrossCurrencyTransferRequest, CrossCurrencyTransferResponse
from fund_transfer.services.notification_service import NotificationService

logger = structlog.get_logger()
_tracer = trace.get_tracer(__name__)
QUANT = Decimal("0.0001")
TRANSFER_STATUS_TOTAL = Counter(
    "transfer_status_total",
    "Cross-currency transfer state transitions",
    labelnames=("status",),
)


class CrossCurrencyTransferService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._settings = get_settings()
        self._transfer_repo = TransferRepository(session)
        self._fx_repo = FxRateRepository(session)
        self._notification_service = NotificationService(session)

    async def initiate(
        self,
        request: CrossCurrencyTransferRequest,
        caller_id: str,
        idempotency_key: str,
        request_id: str | None,
    ) -> tuple[CrossCurrencyTransferResponse, bool]:
        existing = await self._transfer_repo.get_idempotency_record(idempotency_key)
        if existing is not None:
            transfer = existing["transfer"]
            if transfer.caller_id != caller_id:
                raise IdempotencyConflictError("Idempotency-Key was previously used by a different caller.")
            return self._to_response(transfer), True

        async with await _begin_transaction(self._session):
            current_snapshot = await self._fx_repo.get_latest_snapshot()
            if current_snapshot is None or current_snapshot.is_stale:
                raise StaleRateError("Exchange rates are stale. Please retry shortly.")

            preview_snapshot = await self._fx_repo.get_snapshot_by_id(request.fx_snapshot_id)
            if preview_snapshot is None or preview_snapshot.is_stale:
                raise StaleRateError("Selected FX snapshot is no longer available.")

            await self._ensure_active_pair(request.source_currency, request.destination_currency)
            source_account, destination_account = await self._load_accounts(
                request.source_account_number,
                request.destination_account_number,
            )
            if source_account.owner_id != caller_id:
                raise ForbiddenError("You are not authorized to transfer from this account.")
            if source_account.currency != request.source_currency:
                raise UnsupportedCurrencyPairError(
                    f"Source account currency {source_account.currency} does not match request currency {request.source_currency}."
                )

            preview_rate = self._get_rate(preview_snapshot.rates, request.source_currency, request.destination_currency)
            current_rate = self._get_rate(current_snapshot.rates, request.source_currency, request.destination_currency)
            self._check_rate_deviation(preview_rate, current_rate, current_snapshot.id)

            sending_fee, gross_amount, receiving_fee, net_amount, total_sender_cost = self._calculate_amounts(
                request.source_amount,
                current_rate,
            )
            source_amount_usd = self._amount_in_usd(request.source_amount, request.source_currency, current_snapshot.rates)
            await self._check_transfer_limits(source_account.account_number, source_amount_usd)

            if source_account.balance < total_sender_cost:
                raise InsufficientFundsError(
                    f"Source account has insufficient funds: balance {source_account.balance:.4f} {source_account.currency}, required {total_sender_cost:.4f} {source_account.currency}."
                )

            transfer = await self._transfer_repo.create_cross_currency_transfer(
                idempotency_key=idempotency_key,
                source_account_number=source_account.account_number,
                destination_account_number=destination_account.account_number,
                source_amount=request.source_amount,
                source_currency=request.source_currency,
                destination_amount=net_amount,
                destination_currency=request.destination_currency,
                exchange_rate=current_rate,
                status=TransferStatus.pending.value,
                caller_id=caller_id,
                request_id=request_id,
                sending_fee=sending_fee,
                sending_fee_currency=request.source_currency,
                receiving_fee=receiving_fee,
                receiving_fee_currency=request.destination_currency,
                fx_snapshot_id=current_snapshot.id,
                rate_confirmed_at=datetime.now(timezone.utc),
                source_amount_usd=source_amount_usd,
            )
            self._record_status_metric(TransferStatus.pending.value)
            with _tracer.start_as_current_span("transfer.state_transition") as span:
                span.set_attribute("transfer_id", str(transfer.id))
                span.set_attribute("from_status", "new")
                span.set_attribute("to_status", TransferStatus.pending.value)
            logger.info("cross_currency_transfer_state_changed", transfer_id=str(transfer.id), status=TransferStatus.pending.value)

            await self._transfer_repo.update_transfer_status(transfer.id, TransferStatus.processing.value, request_id=request_id)
            transfer.status = TransferStatus.processing.value
            self._record_status_metric(TransferStatus.processing.value)
            with _tracer.start_as_current_span("transfer.state_transition") as span:
                span.set_attribute("transfer_id", str(transfer.id))
                span.set_attribute("from_status", TransferStatus.pending.value)
                span.set_attribute("to_status", TransferStatus.processing.value)
            logger.info("cross_currency_transfer_state_changed", transfer_id=str(transfer.id), status=TransferStatus.processing.value)

            source_account.balance = (source_account.balance - total_sender_cost).quantize(QUANT, rounding=ROUND_HALF_UP)
            destination_account.balance = (destination_account.balance + net_amount).quantize(QUANT, rounding=ROUND_HALF_UP)

            transfer.destination_amount = net_amount
            await self._transfer_repo.update_transfer_status(transfer.id, TransferStatus.completed.value, request_id=request_id)
            transfer.status = TransferStatus.completed.value
            self._record_status_metric(TransferStatus.completed.value)
            with _tracer.start_as_current_span("transfer.state_transition") as span:
                span.set_attribute("transfer_id", str(transfer.id))
                span.set_attribute("from_status", TransferStatus.processing.value)
                span.set_attribute("to_status", TransferStatus.completed.value)
            logger.info("cross_currency_transfer_state_changed", transfer_id=str(transfer.id), status=TransferStatus.completed.value)

            if source_account.account_number != destination_account.account_number:
                await self._notification_service.create_transfer_notifications(
                    transfer,
                    source_account,
                    destination_account,
                    actor_identity=caller_id,
                    request_id=request_id,
                )

            await self._aml_kyc_check(transfer, source_account, destination_account, source_amount_usd, request_id)
            return self._to_response(transfer, gross_amount), False

    async def get_status(self, transfer_id: uuid.UUID, caller_id: str) -> CrossCurrencyTransferResponse:
        transfer = await self._transfer_repo.get_transfer_by_id(transfer_id)
        if transfer is None:
            raise NotFoundError("Transfer not found.", error_code="TRANSFER_NOT_FOUND")
        if transfer.caller_id != caller_id:
            raise ForbiddenError("You are not authorized to access this transfer.", error_code="FORBIDDEN")
        return self._to_response(transfer)

    async def _load_accounts(self, source_account_number: str, destination_account_number: str) -> tuple[Account, Account]:
        source_result = await self._session.execute(
            select(Account).where(Account.account_number == source_account_number).with_for_update()
        )
        source_account = source_result.scalar_one_or_none()
        if source_account is None or source_account.status != AccountStatus.active.value:
            raise NotFoundError(f"Source account {source_account_number} does not exist.", error_code="ACCOUNT_NOT_FOUND")

        destination_result = await self._session.execute(
            select(Account).where(Account.account_number == destination_account_number).with_for_update()
        )
        destination_account = destination_result.scalar_one_or_none()
        if destination_account is None or destination_account.status != AccountStatus.active.value:
            raise NotFoundError(
                f"Destination account {destination_account_number} does not exist.",
                error_code="ACCOUNT_NOT_FOUND",
            )
        return source_account, destination_account

    async def _ensure_active_pair(self, from_currency: str, to_currency: str) -> None:
        active_pairs = await self._fx_repo.get_active_currency_pairs()
        if not any(pair.from_currency == from_currency and pair.to_currency == to_currency for pair in active_pairs):
            raise UnsupportedCurrencyPairError(f"Currency pair {from_currency}/{to_currency} is not supported.")

    def _get_rate(self, rates: dict, from_currency: str, to_currency: str) -> Decimal:
        try:
            return Decimal(str(rates[from_currency][to_currency]))
        except KeyError as exc:
            raise UnsupportedCurrencyPairError(f"No rate for {from_currency}/{to_currency}.") from exc

    def _calculate_amounts(self, source_amount: Decimal, rate: Decimal) -> tuple[Decimal, Decimal, Decimal, Decimal, Decimal]:
        sending_fee = (source_amount * self._settings.SENDING_FEE_PCT).quantize(QUANT, rounding=ROUND_HALF_UP)
        gross_amount = (source_amount * rate).quantize(QUANT, rounding=ROUND_HALF_UP)
        receiving_fee = (gross_amount * self._settings.RECEIVING_FEE_PCT).quantize(QUANT, rounding=ROUND_HALF_UP)
        net_amount = (gross_amount - receiving_fee).quantize(QUANT, rounding=ROUND_HALF_UP)
        total_sender_cost = (source_amount + sending_fee).quantize(QUANT, rounding=ROUND_HALF_UP)
        return sending_fee, gross_amount, receiving_fee, net_amount, total_sender_cost

    def _amount_in_usd(self, amount: Decimal, currency: str, rates: dict) -> Decimal:
        if currency == "USD":
            return amount.quantize(QUANT, rounding=ROUND_HALF_UP)
        usd_rate = self._get_rate(rates, currency, "USD")
        return (amount * usd_rate).quantize(QUANT, rounding=ROUND_HALF_UP)

    def _check_rate_deviation(self, preview_rate: Decimal, current_rate: Decimal, current_snapshot_id: uuid.UUID) -> None:
        if preview_rate == Decimal("0"):
            return
        deviation_pct = ((abs(current_rate - preview_rate) / preview_rate) * Decimal("100")).quantize(
            QUANT,
            rounding=ROUND_HALF_UP,
        )
        if deviation_pct > self._settings.FX_RATE_DEVIATION_THRESHOLD_PCT:
            raise RateDeviationError(
                "Exchange rate moved beyond the confirmation threshold.",
                preview_rate=preview_rate,
                current_rate=current_rate,
                deviation_pct=deviation_pct,
                new_snapshot_id=str(current_snapshot_id),
            )

    async def _check_transfer_limits(self, account_number: str, source_amount_usd: Decimal) -> None:
        if source_amount_usd > self._settings.TRANSFER_LIMIT_PER_TX_USD:
            raise TransferLimitExceededError(
                "Transfer exceeds the per-transaction USD limit.",
                limit_type="per_transaction",
                limit_usd=self._settings.TRANSFER_LIMIT_PER_TX_USD,
                attempted_usd=source_amount_usd,
            )
        rolling_since = datetime.now(timezone.utc) - timedelta(hours=24)
        daily_volume = await self._transfer_repo.get_daily_transfer_volume_usd(account_number, rolling_since)
        total_volume = (daily_volume + source_amount_usd).quantize(QUANT, rounding=ROUND_HALF_UP)
        if total_volume > self._settings.TRANSFER_LIMIT_PER_DAY_USD:
            raise TransferLimitExceededError(
                "Transfer exceeds the rolling 24h USD limit.",
                limit_type="per_day",
                limit_usd=self._settings.TRANSFER_LIMIT_PER_DAY_USD,
                attempted_usd=total_volume,
            )

    async def _aml_kyc_check(
        self,
        transfer: Transfer,
        sender_account: Account,
        recipient_account: Account,
        source_amount_usd: Decimal,
        request_id: str | None,
    ) -> None:
        if source_amount_usd < self._settings.AML_SCREENING_THRESHOLD_USD:
            return
        await self._transfer_repo.write_audit_log(
            operation_type=OperationType.aml_kyc_screening_triggered.value,
            actor_identity=transfer.caller_id,
            affected_account_numbers=[sender_account.account_number, recipient_account.account_number],
            amount=source_amount_usd,
            currency="USD",
            outcome="success",
            detail={"transfer_id": str(transfer.id), "source_amount_usd": str(source_amount_usd)},
            request_id=request_id,
        )

    def _record_status_metric(self, status: str) -> None:
        TRANSFER_STATUS_TOTAL.labels(status=status).inc()

    def _to_response(self, transfer: Transfer, gross_amount: Decimal | None = None) -> CrossCurrencyTransferResponse:
        computed_gross = gross_amount
        if computed_gross is None:
            computed_gross = (Decimal(str(transfer.source_amount)) * Decimal(str(transfer.exchange_rate))).quantize(
                QUANT,
                rounding=ROUND_HALF_UP,
            )
        return CrossCurrencyTransferResponse(
            id=transfer.id,
            status=transfer.status,
            source_amount=Decimal(str(transfer.source_amount)),
            source_currency=transfer.source_currency,
            sending_fee=Decimal(str(transfer.sending_fee or Decimal("0"))),
            gross_converted_amount=computed_gross,
            receiving_fee=Decimal(str(transfer.receiving_fee or Decimal("0"))),
            net_credited_amount=Decimal(str(transfer.destination_amount)),
            destination_currency=transfer.destination_currency,
            exchange_rate=Decimal(str(transfer.exchange_rate)),
            failure_reason=getattr(transfer, "failure_reason", None),
            fx_snapshot_id=getattr(transfer, "fx_snapshot_id", None),
            created_at=transfer.created_at,
        )


async def _begin_transaction(session: AsyncSession):
    transaction = session.begin()
    if inspect.isawaitable(transaction):
        transaction = await transaction
    return transaction
