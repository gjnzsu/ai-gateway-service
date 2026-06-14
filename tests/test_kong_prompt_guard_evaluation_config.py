from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_yaml(path):
    with open(REPO_ROOT / path, encoding="utf-8") as file:
        return yaml.safe_load(file)


def test_default_kong_config_does_not_enable_prompt_guard():
    config = _load_yaml("kong/kong.yml")

    plugin_names = {plugin["name"] for plugin in config.get("plugins", [])}
    assert "ai-prompt-guard" not in plugin_names

    route_plugins = [
        plugin["name"]
        for service in config.get("services", [])
        for route in service.get("routes", [])
        for plugin in route.get("plugins", [])
    ]
    assert "ai-prompt-guard" not in route_plugins


def test_kong_prompt_guard_evaluation_uses_separate_compose_and_config():
    compose = _load_yaml("docker-compose.kong-guard.yml")
    kong = compose["services"]["kong-guard"]

    assert kong["image"] == "kong:3"
    assert kong["environment"]["KONG_DATABASE"] == "off"
    assert (
        kong["environment"]["KONG_DECLARATIVE_CONFIG"]
        == "/kong/declarative/kong-prompt-guard-evaluation.yml"
    )
    assert (
        "./kong/kong-prompt-guard-evaluation.yml:/kong/declarative/kong-prompt-guard-evaluation.yml:ro"
        in kong["volumes"]
    )


def test_kong_prompt_guard_evaluation_routes_to_ai_gateway_service():
    config = _load_yaml("kong/kong-prompt-guard-evaluation.yml")
    service = config["services"][0]

    assert service["name"] == "ai-gateway-service-prompt-guard-evaluation"
    assert service["url"] == "http://ai-gateway-service:4000"

    routes = {route["name"]: route for route in service["routes"]}
    route = routes["kong-prompt-guard-v1"]
    assert route["paths"] == ["/kong-guard/v1"]
    assert route["strip_path"] is True


def test_kong_prompt_guard_evaluation_is_pass_through_only():
    config = _load_yaml("kong/kong-prompt-guard-evaluation.yml")
    route = config["services"][0]["routes"][0]
    plugins = {plugin["name"]: plugin for plugin in route["plugins"]}

    prompt_guard = plugins["ai-prompt-guard"]["config"]
    assert prompt_guard["allow_patterns"] == ["(?s).*"]
    assert prompt_guard["deny_patterns"] == []
