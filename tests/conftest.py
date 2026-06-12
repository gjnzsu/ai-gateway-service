import os
from pathlib import Path

import httpx
import pytest

os.environ.setdefault(
    "LITELLM_CONFIG_PATH",
    str(Path(__file__).resolve().parents[1] / "config.yaml"),
)

from app.main import app  # noqa: E402


@pytest.fixture
def make_client():
    def _make_client():
        return httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        )

    return _make_client
