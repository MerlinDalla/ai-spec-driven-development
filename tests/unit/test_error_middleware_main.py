from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from fastapi.testclient import TestClient

from fund_transfer.api.middleware.correlation import CorrelationMiddleware, REQUEST_ID_HEADER
from fund_transfer.api.middleware.error_handler import register_exception_handlers
from fund_transfer.core.exceptions import ValidationError
from fund_transfer.main import create_app


def test_correlation_middleware_preserves_request_id():
    app = FastAPI()
    app.add_middleware(CorrelationMiddleware)

    @app.get("/ping")
    async def ping():
        return PlainTextResponse("pong")

    client = TestClient(app)
    response = client.get("/ping", headers={REQUEST_ID_HEADER: "req-123"})

    assert response.status_code == 200
    assert response.headers[REQUEST_ID_HEADER] == "req-123"


def test_correlation_middleware_generates_request_id():
    app = FastAPI()
    app.add_middleware(CorrelationMiddleware)

    @app.get("/ping")
    async def ping():
        return PlainTextResponse("pong")

    client = TestClient(app)
    response = client.get("/ping")

    assert response.status_code == 200
    assert response.headers[REQUEST_ID_HEADER]


def test_error_handler_returns_domain_error_response():
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/domain-error")
    async def domain_error():
        raise ValidationError("Bad input.")

    client = TestClient(app)
    response = client.get("/domain-error", headers={REQUEST_ID_HEADER: "req-456"})

    assert response.status_code == 400
    assert response.json() == {
        "error_code": "VALIDATION_ERROR",
        "message": "Bad input.",
        "request_id": "req-456",
        "details": None,
    }


def test_error_handler_returns_generic_error_response():
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/generic-error")
    async def generic_error():
        raise RuntimeError("boom")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/generic-error")

    assert response.status_code == 500
    assert response.json()["error_code"] == "INTERNAL_ERROR"
    assert response.json()["request_id"] == "unknown"


def test_create_app_exposes_health_and_api_routes():
    app = create_app()
    client = TestClient(app)

    response = client.get("/health")
    openapi = client.get("/openapi.json").json()

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "/api/v1/accounts" in openapi["paths"]
    assert "/api/v1/transfers" in openapi["paths"]
