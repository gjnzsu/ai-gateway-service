from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_yaml(path):
    with open(REPO_ROOT / path, encoding="utf-8") as file:
        return yaml.safe_load(file)


def test_default_kong_config_does_not_enable_ai_proxy():
    config = _load_yaml("kong/kong.yml")

    plugin_names = {plugin["name"] for plugin in config.get("plugins", [])}
    assert "ai-proxy" not in plugin_names


def test_kong_ai_proxy_experiment_uses_separate_compose_and_config():
    compose = _load_yaml("docker-compose.kong-ai.yml")
    kong = compose["services"]["kong-ai"]

    assert kong["image"] == "kong:3"
    assert kong["environment"]["KONG_DATABASE"] == "off"
    assert (
        kong["environment"]["KONG_DECLARATIVE_CONFIG"]
        == "/kong/declarative/kong-ai-proxy-experiment.yml"
    )
    assert (
        "./kong/kong-ai-proxy-experiment.yml:/kong/declarative/kong-ai-proxy-experiment.yml:ro"
        in kong["volumes"]
    )


def test_kong_ai_proxy_experiment_declares_openai_chat_route():
    config = _load_yaml("kong/kong-ai-proxy-experiment.yml")
    service = config["services"][0]

    assert service["name"] == "kong-ai-openai-chat-experiment"
    assert service["url"] == "https://api.openai.com"

    routes = {route["name"]: route for route in service["routes"]}
    route = routes["kong-ai-openai-chat"]
    assert route["paths"] == ["/kong-ai/v1/chat/completions"]
    assert route["strip_path"] is True


def test_kong_ai_proxy_experiment_configures_ai_proxy_plugin():
    config = _load_yaml("kong/kong-ai-proxy-experiment.yml")
    route = config["services"][0]["routes"][0]
    plugins = {plugin["name"]: plugin for plugin in route["plugins"]}

    ai_proxy = plugins["ai-proxy"]["config"]
    assert ai_proxy["route_type"] == "llm/v1/chat"
    assert ai_proxy["model"]["provider"] == "openai"
    assert ai_proxy["model"]["name"] == "gpt-4o-mini"
    assert ai_proxy["auth"]["header_name"] == "Authorization"
    assert ai_proxy["auth"]["header_value"] == 'Bearer ${{ env "DECK_OPENAI_API_KEY" }}'
