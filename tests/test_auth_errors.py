"""Tests for API key authentication and centralized error handling."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from simpli_core.auth import add_api_key_middleware
from simpli_core.errors import (
    AuthenticationError,
    ExternalServiceError,
    ForbiddenError,
    NotFoundError,
    RateLimitedError,
    SimpliError,
    ValidationError,
)
from simpli_core.fastapi import _register_error_handlers

# -- Error hierarchy tests --


class TestErrorHierarchy:
    def test_simpli_error_defaults(self) -> None:
        err = SimpliError()
        assert err.status_code == 500
        assert err.error_code == "INTERNAL_ERROR"
        assert err.detail == "An internal error occurred"

    def test_simpli_error_custom(self) -> None:
        err = SimpliError("something broke")
        assert err.detail == "something broke"
        assert str(err) == "something broke"

    def test_not_found_error(self) -> None:
        err = NotFoundError("Ticket not found")
        assert err.status_code == 404
        assert err.error_code == "NOT_FOUND"
        assert isinstance(err, SimpliError)

    def test_authentication_error(self) -> None:
        err = AuthenticationError("Bad token")
        assert err.status_code == 401

    def test_forbidden_error(self) -> None:
        err = ForbiddenError("Not allowed")
        assert err.status_code == 403

    def test_validation_error(self) -> None:
        err = ValidationError("Invalid input")
        assert err.status_code == 422

    def test_rate_limited_error(self) -> None:
        err = RateLimitedError("Too fast")
        assert err.status_code == 429

    def test_external_service_error(self) -> None:
        err = ExternalServiceError("Salesforce down")
        assert err.status_code == 502


# -- API key middleware tests --


class TestAPIKeyMiddleware:
    def _make_app(self, api_key: str) -> FastAPI:
        app = FastAPI()
        add_api_key_middleware(app, api_key)

        @app.get("/health")
        async def health():
            return {"status": "ok"}

        @app.get("/data")
        async def data():
            return {"data": "secret"}

        return app

    def test_disabled_when_empty(self) -> None:
        app = self._make_app("")
        client = TestClient(app)
        resp = client.get("/data")
        assert resp.status_code == 200

    def test_valid_key_passes(self) -> None:
        app = self._make_app("test-key-123")
        client = TestClient(app)
        resp = client.get("/data", headers={"X-API-Key": "test-key-123"})
        assert resp.status_code == 200

    def test_invalid_key_rejected(self) -> None:
        app = self._make_app("test-key-123")
        client = TestClient(app)
        resp = client.get("/data", headers={"X-API-Key": "wrong-key"})
        assert resp.status_code == 401
        assert resp.json()["error_code"] == "AUTHENTICATION_ERROR"

    def test_missing_key_rejected(self) -> None:
        app = self._make_app("test-key-123")
        client = TestClient(app)
        resp = client.get("/data")
        assert resp.status_code == 401

    def test_health_excluded(self) -> None:
        app = self._make_app("test-key-123")
        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_docs_excluded(self) -> None:
        app = self._make_app("test-key-123")
        client = TestClient(app)
        resp = client.get("/docs")
        # FastAPI serves docs on /docs, might redirect
        assert resp.status_code in (200, 307)


# -- Error handler integration tests --


class TestErrorHandlers:
    def _make_app(self) -> FastAPI:
        app = FastAPI()
        _register_error_handlers(app)

        @app.get("/not-found")
        async def trigger_not_found():
            raise NotFoundError("Item not found")

        @app.get("/validation")
        async def trigger_validation():
            raise ValidationError("Bad input")

        @app.get("/external")
        async def trigger_external():
            raise ExternalServiceError("Upstream failed")

        @app.get("/unhandled")
        async def trigger_unhandled():
            msg = "unexpected"
            raise RuntimeError(msg)

        return app

    def test_not_found_handler(self) -> None:
        client = TestClient(self._make_app(), raise_server_exceptions=False)
        resp = client.get("/not-found")
        assert resp.status_code == 404
        data = resp.json()
        assert data["error_code"] == "NOT_FOUND"
        assert data["detail"] == "Item not found"

    def test_validation_handler(self) -> None:
        client = TestClient(self._make_app(), raise_server_exceptions=False)
        resp = client.get("/validation")
        assert resp.status_code == 422
        assert resp.json()["error_code"] == "VALIDATION_ERROR"

    def test_external_handler(self) -> None:
        client = TestClient(self._make_app(), raise_server_exceptions=False)
        resp = client.get("/external")
        assert resp.status_code == 502
        assert resp.json()["error_code"] == "EXTERNAL_SERVICE_ERROR"

    def test_unhandled_handler(self) -> None:
        client = TestClient(self._make_app(), raise_server_exceptions=False)
        resp = client.get("/unhandled")
        assert resp.status_code == 500
        assert resp.json()["error_code"] == "INTERNAL_ERROR"
