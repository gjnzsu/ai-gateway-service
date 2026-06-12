from pathlib import Path

from app.main import resolve_config_path


def test_resolve_config_path_uses_explicit_env_path(monkeypatch, tmp_path):
    explicit_config = tmp_path / "custom-config.yaml"
    explicit_config.write_text("model_list: []", encoding="utf-8")
    monkeypatch.setenv("LITELLM_CONFIG_PATH", str(explicit_config))

    assert resolve_config_path() == explicit_config


def test_resolve_config_path_falls_back_to_repo_config(monkeypatch):
    monkeypatch.delenv("LITELLM_CONFIG_PATH", raising=False)

    assert resolve_config_path().name == "config.yaml"
    assert resolve_config_path() == Path(__file__).resolve().parents[1] / "config.yaml"
