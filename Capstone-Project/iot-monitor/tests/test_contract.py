"""The running app must not drift from docs/api-spec.yaml."""
from pathlib import Path

import yaml

from app.main import app

SPEC = yaml.safe_load((Path(__file__).resolve().parent.parent / "docs" / "api-spec.yaml").read_text(encoding="utf-8"))
METHODS = {"get", "post", "put", "patch", "delete"}


def test_every_implemented_endpoint_is_in_the_spec():
    live = app.openapi()["paths"]
    checked = 0
    for path, item in live.items():
        if not path.startswith("/api/v1"):
            continue
        spec_path = path[len("/api/v1"):]
        assert spec_path in SPEC["paths"], f"{path} is implemented but missing from api-spec.yaml"
        for method, op in item.items():
            if method not in METHODS:
                continue
            assert method in SPEC["paths"][spec_path], f"{method.upper()} {path} missing from api-spec.yaml"
            assert op["operationId"] == SPEC["paths"][spec_path][method]["operationId"], f"operationId differs for {method.upper()} {path}"
            checked += 1
    assert checked >= 30


def test_sensor_metadata_is_exposed_under_its_json_name():
    schema = app.openapi()["components"]["schemas"]["SensorOut"]["properties"]
    assert "metadata" in schema and "meta" not in schema
