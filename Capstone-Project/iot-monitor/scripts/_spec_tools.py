"""Shared helpers for turning docs/api-spec.yaml into docs (build_api_docs.py) and Postman files (build_postman.py)."""
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
METHODS = ("get", "post", "put", "patch", "delete")

# Friendlier request bodies than auto-generated ones
BODY_EXAMPLES = {
    "register": {"email": "ann@example.com", "password": "Str0ng!Pass", "name": "Ann Lee"},
    "resend_verification": {"email": "ann@example.com"},
    "refresh_token": {"refresh_token": "<refresh_token>"},
    "logout": {"refresh_token": "<refresh_token>"},
    "update_me": {"name": "Ann Lee"},
    "put_my_profile": {"bio": "Maintenance lead", "phone": "+91 98765 43210", "timezone": "Asia/Kolkata", "language": "en-IN", "preferences": {"theme": "dark"}},
    "admin_update_user": {"role": "user", "is_active": True},
    "create_sensor": {"title": "Boiler Temperature", "description": "Main boiler outlet", "category": "temperature", "status": "active", "priority": "high",
                      "metadata": {"factory": "Hyderabad Plant", "location": "Boiler Room", "unit": "°C", "thresholds": {"min": 60, "max": 90}}},
    "replace_sensor": {"title": "Boiler Temperature", "category": "temperature", "status": "active", "priority": "high", "metadata": {"unit": "°C"}},
    "update_sensor": {"status": "faulty"},
    "bulk_create_sensors": {"items": [{"title": "Pump A", "category": "pressure"}, {"title": "Pump B", "category": "pressure"}]},
    "bulk_delete_sensors": {"ids": [7, 8]},
    "create_reading": {"value": 71.5},
    "bulk_create_readings": {"items": [{"value": 70.1}, {"value": 71.5, "recorded_at": "2026-11-14T10:00:00Z"}]},
    "create_report": {"name": "Weekly plant report", "format": "pdf", "query_params": {"template": "summary", "category": "temperature", "window_hours": 168}},
    "put_config": {"value": 5, "description": "Dashboard refresh interval in seconds", "is_active": True},
}
PARAM_EXAMPLES = {"sensor_id": "1", "user_id": "2", "report_id": "1", "key": "dashboard.poll_interval_seconds", "token": "<token-from-email>"}


def load_spec() -> dict:
    return yaml.safe_load((ROOT / "docs" / "api-spec.yaml").read_text(encoding="utf-8"))


def deref(spec: dict, node):
    """Follow a $ref like #/components/schemas/Sensor."""
    while isinstance(node, dict) and "$ref" in node:
        target = spec
        for part in node["$ref"].lstrip("#/").split("/"):
            target = target[part]
        node = target
    return node


def example(spec: dict, schema, depth: int = 0):
    schema = deref(spec, schema)
    if depth > 6 or not isinstance(schema, dict):
        return None
    if "example" in schema:
        return schema["example"]
    if "default" in schema:
        return schema["default"]
    if "enum" in schema:
        return schema["enum"][0]
    kind = schema.get("type")
    if kind == "object" or "properties" in schema:
        props = schema.get("properties", {})
        return {k: example(spec, v, depth + 1) for k, v in props.items()}
    if kind == "array":
        return [example(spec, schema.get("items", {}), depth + 1)]
    fmt = schema.get("format")
    if kind == "string":
        return {"email": "user@example.com", "password": "Str0ng!Pass", "date-time": "2026-11-14T10:00:00Z", "binary": "<file>"}.get(fmt, "string")
    if kind == "integer":
        return 1
    if kind == "number":
        return 1.5
    if kind == "boolean":
        return True
    return None


def operations(spec: dict):
    """Yield (path, method, op) in the order of the spec."""
    for path, item in spec["paths"].items():
        for method in METHODS:
            if method in item:
                yield path, method, item[method]


def body_schema(spec: dict, op: dict):
    content = deref(spec, op.get("requestBody", {})).get("content", {})
    for media in ("application/json", "application/x-www-form-urlencoded"):
        if media in content:
            return media, content[media]["schema"]
    return None, None


def body_example(spec: dict, op: dict):
    media, schema = body_schema(spec, op)
    if media is None:
        return None, None
    return media, BODY_EXAMPLES.get(op["operationId"]) or example(spec, schema)


def all_parameters(spec: dict, op: dict) -> list[dict]:
    return [deref(spec, p) for p in op.get("parameters", [])]


def dump(obj) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False)
