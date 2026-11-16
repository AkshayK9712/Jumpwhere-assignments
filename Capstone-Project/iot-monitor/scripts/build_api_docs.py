"""Generate docs/api/reference.md (every endpoint with curl examples) from docs/api-spec.yaml.

    python scripts/build_api_docs.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _spec_tools import ROOT, all_parameters, body_example, deref, dump, load_spec, operations  # noqa: E402


def curl(spec, path, method, op):
    url_path = path
    query = []
    for p in all_parameters(spec, op):
        if p["in"] == "path":
            from _spec_tools import PARAM_EXAMPLES
            url_path = url_path.replace("{%s}" % p["name"], PARAM_EXAMPLES.get(p["name"], "1"))
    url = f'"$BASE{url_path}"'
    parts = [f"curl -X {method.upper()} {url}"]
    if op.get("security"):
        parts.append('-H "Authorization: Bearer $TOKEN"')
    media, example = body_example(spec, op)
    if media == "application/json":
        import json
        parts.append('-H "Content-Type: application/json"')
        parts.append(f"-d '{json.dumps(example, ensure_ascii=False)}'")
    elif media == "application/x-www-form-urlencoded":
        parts.append('-d "username=user@example.com&password=User@12345&remember_me=false"')
    return " \\\n  ".join(parts)


def main():
    spec = load_spec()
    out = [f"# {spec['info']['title']}: API reference", "",
           "_Generated from `docs/api-spec.yaml` by `scripts/build_api_docs.py`. Do not edit by hand._", "",
           "Examples assume:", "", "```bash", "BASE=http://localhost:8000/api/v1",
           'TOKEN=$(curl -s -X POST "$BASE/auth/login" -d "username=user@example.com&password=User@12345" | python -c "import sys,json;print(json.load(sys.stdin)[\'access_token\'])")',
           "```", ""]
    by_tag: dict[str, list] = {}
    for path, method, op in operations(spec):
        by_tag.setdefault(op["tags"][0], []).append((path, method, op))

    out += ["## Contents", ""]
    for tag, items in by_tag.items():
        out.append(f"- **{tag}**: " + ", ".join(f"`{m.upper()} {p}`" for p, m, _ in items))
    out.append("")

    for tag, items in by_tag.items():
        out += [f"## {tag.capitalize()}", ""]
        for path, method, op in items:
            out += [f"### `{method.upper()} {path}`", "", f"**{op['summary']}** (operationId: `{op['operationId']}`)", ""]
            if op.get("description"):
                out += [op["description"], ""]
            out.append("Authentication: " + ("Bearer token required." if op.get("security") else "none (public)."))
            out.append("")
            params = all_parameters(spec, op)
            if params:
                out += ["| Parameter | In | Required | Type | Notes |", "|---|---|---|---|---|"]
                for p in params:
                    schema = deref(spec, p.get("schema", {}))
                    typ = schema.get("type", "") + (f" ({', '.join(map(str, schema['enum']))})" if "enum" in schema else "")
                    out.append(f"| `{p['name']}` | {p['in']} | {'yes' if p.get('required') else 'no'} | {typ} | {p.get('description', '')} |")
                out.append("")
            media, example = body_example(spec, op)
            if media:
                out += [f"Request body (`{media}`):", ""]
                out += ["```json", dump(example), "```"] if media == "application/json" else ["```", "username=user@example.com&password=User@12345&remember_me=false", "```"]
                out.append("")
            out += ["Example:", "", "```bash", curl(spec, path, method, op), "```", "", "Responses:", ""]
            for code, resp in op["responses"].items():
                resp = deref(spec, resp)
                out.append(f"- `{code}`: {resp.get('description', '')}")
            out.append("")
    target = ROOT / "docs" / "api" / "reference.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"Wrote {target} ({sum(len(v) for v in by_tag.values())} endpoints)")


if __name__ == "__main__":
    main()
