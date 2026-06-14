import os
from pathlib import Path

import httpx
import pytest

os.environ.setdefault(
    "LITELLM_CONFIG_PATH",
    str(Path(__file__).resolve().parents[1] / "config.yaml"),
)

import app.main as gateway_main  # noqa: E402


@pytest.fixture
def make_client():
    def _make_client():
        return httpx.AsyncClient(
            transport=httpx.ASGITransport(app=gateway_main.app),
            base_url="http://testserver",
        )

    return _make_client


@pytest.fixture(autouse=True)
def clear_circuit_breakers():
    gateway_main._circuit_breakers.clear()
    yield
    gateway_main._circuit_breakers.clear()
