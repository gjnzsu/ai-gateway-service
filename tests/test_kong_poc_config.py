from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_yaml(path):
    with open(REPO_ROOT / path, encoding="utf-8") as file:
        return yaml.safe_load(file)


def test_kong_compose_runs_db_less_with_declarative_config():
    compose = _load_yaml("docker-compose.kong.yml")
    kong = compose["services"]["kong"]

    environment = kong["environment"]
    assert environment["KONG_DATABASE"] == "off"
    assert environment["KONG_DECLARATIVE_CONFIG"] == "/kong/declarative/kong.yml"
    assert "./kong/kong.yml:/kong/declarative/kong.yml:ro" in kong["volumes"]


def test_kong_routes_preserve_gateway_paths():
    config = _load_yaml("kong/kong.yml")
    service = config["services"][0]

    assert service["name"] == "ai-gateway-service"
    assert service["url"] == "http://ai-gateway-service:4000"

    routes = {route["name"]: route for route in service["routes"]}
    assert routes["ai-gateway-v1"]["paths"] == ["/v1"]
    assert routes["ai-gateway-v1"]["strip_path"] is False
    assert routes["ai-gateway-health"]["paths"] == ["/health"]
    assert routes["ai-gateway-health"]["strip_path"] is False
    assert routes["ai-gateway-readiness"]["paths"] == ["/readiness"]
    assert routes["ai-gateway-readiness"]["strip_path"] is False


def test_kong_poc_has_request_correlation_and_rate_limit_plugins():
    config = _load_yaml("kong/kong.yml")
    plugins = {plugin["name"]: plugin for plugin in config["plugins"]}

    assert "correlation-id" in plugins
    assert plugins["correlation-id"]["config"]["header_name"] == "X-Request-ID"

    assert "rate-limiting" in plugins
    assert plugins["rate-limiting"]["config"]["minute"] == 120
    assert plugins["rate-limiting"]["config"]["policy"] == "local"
