from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def load_yaml(relative_path: str) -> dict:
    return yaml.safe_load((ROOT / relative_path).read_text(encoding="utf-8"))


def embedded_kong_config() -> dict:
    manifest = load_yaml("k8s/kong-config.yaml")
    return yaml.safe_load(manifest["data"]["kong.yml"])



def test_kong_configmap_defines_dbless_gateway_routes_and_plugins():
    manifest = load_yaml("k8s/kong-config.yaml")
    kong_config = embedded_kong_config()

    assert manifest["kind"] == "ConfigMap"
    assert manifest["metadata"]["name"] == "ai-gateway-kong-config"
    assert manifest["metadata"]["namespace"] == "ai-gateway"

    service = kong_config["services"][0]
    assert service["url"] == "http://ai-gateway.ai-gateway.svc.cluster.local"

    routes_by_path = {
        path: route
        for route in service["routes"]
        for path in route["paths"]
    }
    for path in ("/v1", "/health", "/readiness"):
        assert routes_by_path[path]["strip_path"] is False

    plugin_names = {plugin["name"] for plugin in kong_config["plugins"]}
    assert {"correlation-id", "rate-limiting"} <= plugin_names


def test_kong_deployment_runs_independent_dbless_gateway():
    manifest = load_yaml("k8s/kong-deployment.yaml")

    assert manifest["kind"] == "Deployment"
    assert manifest["metadata"]["name"] == "ai-gateway-kong"
    assert manifest["metadata"]["namespace"] == "ai-gateway"

    pod_spec = manifest["spec"]["template"]["spec"]
    container = pod_spec["containers"][0]
    env = {item["name"]: item["value"] for item in container["env"]}

    assert container["image"].startswith("kong:")
    assert env["KONG_DATABASE"] == "off"
    assert env["KONG_DECLARATIVE_CONFIG"] == "/kong/declarative/kong.yml"
    assert any(port["containerPort"] == 8000 for port in container["ports"])
    assert any(
        mount["name"] == "kong-config"
        and mount["mountPath"] == "/kong/declarative"
        for mount in container["volumeMounts"]
    )
    assert any(
        volume["name"] == "kong-config"
        and volume["configMap"]["name"] == "ai-gateway-kong-config"
        for volume in pod_spec["volumes"]
    )
    env = {item["name"]: item["value"] for item in container["env"]}
    assert env["KONG_NGINX_WORKER_PROCESSES"] == "2"
    assert container["resources"]["requests"] == {"cpu": "250m", "memory": "512Mi"}
    assert container["resources"]["limits"] == {"cpu": "1000m", "memory": "1Gi"}
    for probe_name in ("readinessProbe", "livenessProbe"):
        probe = container[probe_name]
        assert probe["tcpSocket"]["port"] == 8000
        assert "httpGet" not in probe


def test_kong_service_exposes_internal_cluster_ip_proxy():
    manifest = load_yaml("k8s/kong-service.yaml")

    assert manifest["kind"] == "Service"
    assert manifest["metadata"]["name"] == "ai-gateway-kong"
    assert manifest["metadata"]["namespace"] == "ai-gateway"
    assert manifest["spec"]["type"] == "ClusterIP"
    assert manifest["spec"]["selector"]["app"] == "ai-gateway-kong"

    port = manifest["spec"]["ports"][0]
    assert port["port"] == 80
    assert port["targetPort"] == 8000


def test_kong_config_uses_gke_service_dns_for_ai_gateway_upstream():
    content = (ROOT / "k8s/kong-config.yaml").read_text(encoding="utf-8")

    assert "ai-gateway-service:4000" not in content
    assert "ai-gateway.ai-gateway.svc.cluster.local" in content
