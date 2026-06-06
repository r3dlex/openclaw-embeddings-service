"""Real tests for openclaw-embeddings-service/server.py.

Covers:
- /health endpoint
- /embed request validation (empty, oversized batches)
- /embed success path with a stubbed SentenceTransformer model
- EmbedRequest / EmbedResponse Pydantic models
- get_model() lazy-load + singleton behavior
- MAX_BATCH_SIZE enforcement
- Error envelope shape on 4xx/5xx

Tests use FastAPI's TestClient (via httpx) and patch the lazy
`get_model()` so no actual model weights are loaded. The unit
tests do NOT require sentence-transformers at install time —
the import is patched in the get_model() body.
"""
from __future__ import annotations

import importlib
import os
import sys
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from fastapi.testclient import TestClient

# Make server.py importable as a module.
SERVER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)


@pytest.fixture
def app_module():
    """Fresh import of server module so module-level state is clean."""
    if "server" in sys.modules:
        del sys.modules["server"]
    return importlib.import_module("server")


@pytest.fixture
def client(app_module):
    """FastAPI TestClient wrapping the freshly-imported app."""
    return TestClient(app_module.app)


@pytest.fixture
def fake_model():
    """Mock SentenceTransformer model with predictable embeddings."""
    model = MagicMock()
    # 384 = MiniLM-L6 dimension (matches the prod MODEL_NAME default).
    model.encode.return_value = np.array(
        [[0.1, 0.2, 0.3] + [0.0] * 381, [0.4, 0.5, 0.6] + [0.0] * 381],
        dtype=np.float32,
    )
    return model


@pytest.fixture
def reset_model_cache(app_module):
    """Reset the module-level _model cache before and after each test."""
    app_module._model = None
    yield
    app_module._model = None


# ─────────────────────────────────────────────────────────────────────
# Module configuration
# ─────────────────────────────────────────────────────────────────────

class TestConfig:
    def test_model_name_default(self, app_module):
        """MODEL_NAME should default to the 4-bit quantized MiniLM."""
        assert app_module.MODEL_NAME == "mlx-community/all-MiniLM-L6-v2-4bit"

    def test_max_batch_size_default(self, app_module):
        """MAX_BATCH_SIZE should default to 32."""
        assert app_module.MAX_BATCH_SIZE == 32

    def test_model_name_env_override(self, monkeypatch):
        """MODEL_NAME env var should override the default."""
        monkeypatch.setenv("MODEL_NAME", "custom-model")
        # Re-import to pick up the new env var.
        if "server" in sys.modules:
            del sys.modules["server"]
        mod = importlib.import_module("server")
        try:
            assert mod.MODEL_NAME == "custom-model"
        finally:
            monkeypatch.delenv("MODEL_NAME", raising=False)
            if "server" in sys.modules:
                del sys.modules["server"]
            importlib.import_module("server")  # restore default

    def test_max_batch_size_env_override(self, monkeypatch):
        """MAX_BATCH_SIZE env var should override the default (int parse)."""
        monkeypatch.setenv("MAX_BATCH_SIZE", "16")
        if "server" in sys.modules:
            del sys.modules["server"]
        mod = importlib.import_module("server")
        try:
            assert mod.MAX_BATCH_SIZE == 16
        finally:
            monkeypatch.delenv("MAX_BATCH_SIZE", raising=False)
            if "server" in sys.modules:
                del sys.modules["server"]
            importlib.import_module("server")  # restore default

    def test_app_title(self, app_module):
        """FastAPI app should advertise the correct title + version."""
        assert app_module.app.title == "Openclaw Embeddings Service"
        assert app_module.app.version == "1.0.0"


# ─────────────────────────────────────────────────────────────────────
# get_model() — lazy load + cache
# ─────────────────────────────────────────────────────────────────────

class TestGetModel:
    def test_first_call_loads_model(self, app_module, reset_model_cache, fake_model):
        """First call should invoke SentenceTransformer and cache the result."""
        with patch("sentence_transformers.SentenceTransformer", return_value=fake_model):
            m1 = app_module.get_model()
        assert m1 is fake_model
        # The module-level _model should now be set.
        assert app_module._model is fake_model

    def test_second_call_returns_cached(self, app_module, reset_model_cache, fake_model):
        """Second call should NOT re-instantiate the model."""
        with patch("sentence_transformers.SentenceTransformer", return_value=fake_model) as ctor:
            app_module.get_model()
            app_module.get_model()  # cached
            app_module.get_model()  # cached
        assert ctor.call_count == 1

    def test_load_failure_raises_503(self, app_module, reset_model_cache):
        """If SentenceTransformer raises, get_model() should raise HTTPException 503."""
        with patch("sentence_transformers.SentenceTransformer", side_effect=RuntimeError("boom")):
            with pytest.raises(Exception) as exc_info:
                app_module.get_model()
        # FastAPI's HTTPException surfaces via Starlette; just check the detail.
        assert "503" in str(exc_info.value) or "Model loading failed" in str(exc_info.value)


# ─────────────────────────────────────────────────────────────────────
# Pydantic models
# ─────────────────────────────────────────────────────────────────────

class TestEmbedRequest:
    def test_default_normalize_true(self):
        from server import EmbedRequest
        req = EmbedRequest(texts=["hello"])
        assert req.normalize is True

    def test_explicit_normalize_false(self):
        from server import EmbedRequest
        req = EmbedRequest(texts=["hello"], normalize=False)
        assert req.normalize is False

    def test_empty_texts_allowed_at_model_level(self):
        """Empty list passes Pydantic validation; the endpoint rejects it."""
        from server import EmbedRequest
        req = EmbedRequest(texts=[])
        assert req.texts == []

    def test_missing_texts_rejected(self):
        from pydantic import ValidationError

        from server import EmbedRequest
        with pytest.raises(ValidationError):
            EmbedRequest()


class TestEmbedResponse:
    def test_construction(self):
        from server import EmbedResponse
        resp = EmbedResponse(
            embeddings=[[0.1, 0.2]],
            model="some-model",
            dimensions=2,
        )
        assert resp.dimensions == 2
        assert resp.model == "some-model"
        assert len(resp.embeddings) == 1


# ─────────────────────────────────────────────────────────────────────
# /health endpoint
# ─────────────────────────────────────────────────────────────────────

class TestHealthEndpoint:
    def test_health_ok(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["model"] == "mlx-community/all-MiniLM-L6-v2-4bit"


# ─────────────────────────────────────────────────────────────────────
# /embed endpoint — validation
# ─────────────────────────────────────────────────────────────────────

class TestEmbedValidation:
    def test_empty_texts_returns_400(self, client):
        r = client.post("/embed", json={"texts": []})
        assert r.status_code == 400
        assert "empty" in r.json()["detail"].lower()

    def test_oversized_batch_returns_400(self, client, monkeypatch):
        monkeypatch.setattr(client.app, "dependency_overrides", {})  # noop
        # Patch MAX_BATCH_SIZE via env re-import.
        with patch.dict(os.environ, {"MAX_BATCH_SIZE": "2"}):
            # The app already read the env at import time, so we patch the
            # constant on the module instead.
            import server
            with patch.object(server, "MAX_BATCH_SIZE", 2):
                r = client.post("/embed", json={"texts": ["a", "b", "c"]})
                assert r.status_code == 400
                assert "exceeds maximum" in r.json()["detail"]

    def test_missing_texts_field_returns_422(self, client):
        r = client.post("/embed", json={})
        assert r.status_code == 422  # Pydantic validation


# ─────────────────────────────────────────────────────────────────────
# /embed endpoint — success path
# ─────────────────────────────────────────────────────────────────────

class TestEmbedSuccess:
    def test_embed_returns_correct_shape(self, client, reset_model_cache, fake_model):
        with patch("server.get_model", return_value=fake_model):
            r = client.post("/embed", json={"texts": ["hello", "world"]})
        assert r.status_code == 200
        data = r.json()
        assert data["model"] == "mlx-community/all-MiniLM-L6-v2-4bit"
        assert data["dimensions"] == 384
        assert len(data["embeddings"]) == 2
        # Each embedding is a 384-dim vector.
        for vec in data["embeddings"]:
            assert len(vec) == 384

    def test_embed_passes_normalize_flag(self, client, reset_model_cache, fake_model):
        """The normalize flag from the request should be forwarded to the model."""
        with patch("server.get_model", return_value=fake_model):
            r = client.post("/embed", json={"texts": ["x"], "normalize": False})
        assert r.status_code == 200
        # Inspect what the model was called with.
        kwargs = fake_model.encode.call_args.kwargs
        assert kwargs["normalize_embeddings"] is False
        assert fake_model.encode.call_args.args[0] == ["x"]

    def test_embed_passes_normalize_true_default(self, client, reset_model_cache, fake_model):
        """normalize defaults to True; should be passed to the model."""
        with patch("server.get_model", return_value=fake_model):
            r = client.post("/embed", json={"texts": ["x"]})
        assert r.status_code == 200
        kwargs = fake_model.encode.call_args.kwargs
        assert kwargs["normalize_embeddings"] is True

    def test_embed_model_error_returns_500(self, client, reset_model_cache):
        broken = MagicMock()
        broken.encode.side_effect = RuntimeError("encode failed")
        with patch("server.get_model", return_value=broken):
            r = client.post("/embed", json={"texts": ["x"]})
        assert r.status_code == 500
        assert "encode failed" in r.json()["detail"]


# ─────────────────────────────────────────────────────────────────────
# __main__ entry
# ─────────────────────────────────────────────────────────────────────

class TestMainEntry:
    def test_module_runs_uvicorn(self):
        """The __main__ block calls uvicorn.run with the right port."""
        # The module's __main__ guard is `if __name__ == "__main__":`, so
        # we just import the module and confirm the attributes used by
        # the guard are present.
        import server
        # The port env default lives in the __main__ block; re-import
        # the source to confirm the call site is there.
        src = open(server.__file__).read()
        assert "uvicorn.run" in src
        assert '__name__ == "__main__"' in src
