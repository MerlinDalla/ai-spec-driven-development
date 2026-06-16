from __future__ import annotations

from fastapi import APIRouter

from fund_transfer.api.v1.accounts import router as accounts_router
from fund_transfer.api.v1.fx import router as fx_router
from fund_transfer.api.v1.notifications import router as notifications_router
from fund_transfer.api.v1.transfers import router as transfers_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(accounts_router)
api_router.include_router(transfers_router)
api_router.include_router(fx_router)
api_router.include_router(notifications_router)
