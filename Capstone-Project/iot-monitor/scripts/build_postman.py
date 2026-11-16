"""Generate the Postman collection and environment from docs/api-spec.yaml.

    python scripts/build_postman.py

Import both files from docs/postman/ into Postman, pick the "IoT Monitor (local)" environment,
run "auth / login" first: its test script stores the tokens that every other request uses.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _spec_tools import PARAM_EXAMPLES, ROOT, all_parameters, body_example, deref, dump, load_spec, operations  # noqa: E402

LOGIN_TEST = [
    "pm.test('Logged in', () => pm.response.to.have.status(200));",
    "const body = pm.response.json();",
    "pm.collectionVariables.set('access_token', body.access_token);",
    "pm.collectionVariables.set('refresh_token', body.refresh_token);",
]
REFRESH_TEST = [
    "if (pm.response.code === 200) {",
    "  const body = pm.response.json();",
    "  pm.collectionVariables.set('access_token', body.access_token);",
    "  pm.collectionVariables.set('refresh_token', body.refresh_token);",
    "}",
]
GENERIC_TEST = ["pm.test('No server error', () => pm.expect(pm.response.code).to.be.below(500));"]


def request_item(spec, path, method, op):
    parts = [p for p in path.strip("/").split("/") if p]
    segs = [":" + p[1:-1] if p.startswith("{") else p for p in parts]
    variables = [{"key": p[1:-1], "value": PARAM_EXAMPLES.get(p[1:-1], "1")} for p in parts if p.startswith("{")]
    query = [{"key": p["name"], "value": "", "description": p.get("description", ""), "disabled": True}
             for p in all_parameters(spec, op) if p["in"] == "query"]
    headers = [{"key": p["name"], "value": "", "disabled": True} for p in all_parameters(spec, op) if p["in"] == "header"]
    url = {"raw": "{{baseUrl}}/" + "/".join(segs), "host": ["{{baseUrl}}"], "path": segs, "variable": variables, "query": query}

    item = {"name": f"{op['summary']}", "request": {"method": method.upper(), "header": headers, "url": url,
            "description": (op.get("description") or "") + f"\n\noperationId: {op['operationId']}"}}
    if not op.get("security"):
        item["request"]["auth"] = {"type": "noauth"}

    media, example = body_example(spec, op)
    if media == "application/json":
        if op["operationId"] in ("refresh_token", "logout"):
            example = {"refresh_token": "{{refresh_token}}"}
        item["request"]["header"].append({"key": "Content-Type", "value": "application/json"})
        item["request"]["body"] = {"mode": "raw", "raw": dump(example), "options": {"raw": {"language": "json"}}}
    elif media == "application/x-www-form-urlencoded":
        item["request"]["body"] = {"mode": "urlencoded", "urlencoded": [
            {"key": "username", "value": "{{email}}"}, {"key": "password", "value": "{{password}}"}, {"key": "remember_me", "value": "false"}]}

    script = LOGIN_TEST if op["operationId"] == "login" else REFRESH_TEST if op["operationId"] == "refresh_token" else GENERIC_TEST
    item["event"] = [{"listen": "test", "script": {"type": "text/javascript", "exec": script}}]
    return item


def main():
    spec = load_spec()
    folders: dict[str, list] = {}
    for path, method, op in operations(spec):
        folders.setdefault(op["tags"][0], []).append(request_item(spec, path, method, op))

    collection = {
        "info": {"name": spec["info"]["title"], "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
                 "description": "Generated from docs/api-spec.yaml. Run 'auth / Log in and get tokens' first; it stores the tokens used by every other request."},
        "auth": {"type": "bearer", "bearer": [{"key": "token", "value": "{{access_token}}", "type": "string"}]},
        "variable": [{"key": "baseUrl", "value": "http://localhost:8000/api/v1"}, {"key": "email", "value": "admin@example.com"},
                     {"key": "password", "value": "Admin@12345"}, {"key": "access_token", "value": ""}, {"key": "refresh_token", "value": ""}],
        "item": [{"name": tag, "item": items} for tag, items in folders.items()],
    }
    environment = {
        "id": "iot-monitor-local", "name": "IoT Monitor (local)", "_postman_variable_scope": "environment",
        "values": [{"key": "baseUrl", "value": "http://localhost:8000/api/v1", "enabled": True},
                   {"key": "email", "value": "admin@example.com", "enabled": True},
                   {"key": "password", "value": "Admin@12345", "type": "secret", "enabled": True}],
    }
    out = ROOT / "docs" / "postman"
    out.mkdir(parents=True, exist_ok=True)
    (out / "iot-monitor.postman_collection.json").write_text(json.dumps(collection, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "iot-monitor.postman_environment.json").write_text(json.dumps(environment, indent=2), encoding="utf-8")
    (out / ".gitkeep").unlink(missing_ok=True)
    print(f"Wrote {out} ({sum(len(v) for v in folders.values())} requests in {len(folders)} folders)")


if __name__ == "__main__":
    main()
