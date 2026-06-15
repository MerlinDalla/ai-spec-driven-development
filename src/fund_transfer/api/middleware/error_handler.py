from __future__ import annotations
import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from fund_transfer.core.exceptions import FundTransferError
from fund_transfer.schemas.errors import ErrorResponse

logger = structlog.get_logger()


def _get_request_id(request: Request) -> str:
    return request.headers.get("X-Request-ID", "unknown")


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(FundTransferError)
    async def fund_transfer_error_handler(request: Request, exc: FundTransferError) -> JSONResponse:
        request_id = _get_request_id(request)
        logger.warning("domain_error", error_code=exc.error_code, message=exc.message, request_id=request_id)
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error_code=exc.error_code,
                message=exc.message,
                request_id=request_id,
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = _get_request_id(request)
        logger.error("unexpected_error", error=str(type(exc).__name__), request_id=request_id)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error_code="INTERNAL_ERROR",
                message="An unexpected error occurred. Please retry or contact support.",
                request_id=request_id,
            ).model_dump(),
        )
