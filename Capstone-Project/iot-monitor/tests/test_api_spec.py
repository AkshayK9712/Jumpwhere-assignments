"""Sanity checks for docs/api-spec.yaml (no server needed)."""
import re
from pathlib import Path

import yaml

SPEC_PATH = Path(__file__).resolve().parent.parent / "docs" / "api-spec.yaml"
spec = yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))
METHODS = {"get", "post", "put", "patch", "delete"}


def _operations():
    for path, item in spec["paths"].items():
        for method, op in item.items():
            if method in METHODS:
                yield path, method, op


def _refs(node):
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "$ref":
                yield v
            else:
                yield from _refs(v)
    elif isinstance(node, list):
        for v in node:
            yield from _refs(v)


def test_openapi_version_and_info():
    assert spec["openapi"].startswith("3.")
    assert spec["info"]["title"] == "IoT Monitor API"


def test_all_refs_resolve():
    for r in _refs(spec):
        assert r.startswith("#/components/")
        _, _, section, name = r.split("/")
        assert name in spec["components"][section], f"Broken ref: {r}"


def test_every_operation_is_documented():
    ids = []
    for path, method, op in _operations():
        assert op.get("operationId"), f"{method} {path} has no operationId"
        assert op.get("tags"), f"{method} {path} has no tags"
        assert op.get("responses"), f"{method} {path} has no responses"
        ids.append(op["operationId"])
    assert len(ids) == len(set(ids)), "operationId values must be unique"


def test_path_parameters_are_declared():
    for path, method, op in _operations():
        names = set(re.findall(r"{(\w+)}", path))
        declared = {p["name"] for p in op.get("parameters", []) if p.get("in") == "path"}
        assert names <= declared, f"{method} {path} missing path params {names - declared}"


def test_protected_operations_require_bearer():
    public = {"health", "health_db", "register", "verify_email", "resend_verification", "login", "refresh_token"}
    for path, method, op in _operations():
        if op["operationId"] in public:
            assert "security" not in op
        else:
            assert op.get("security") == [{"bearerAuth": []}], f"{op['operationId']} must be secured"


def test_every_requirement_area_has_endpoints():
    tags = {op["tags"][0] for _, _, op in _operations()}
    assert {"auth", "users", "sensors", "readings", "dashboard", "reports", "admin"} <= tags
