"""The web UI is served correctly, is CSP-safe, and its JS modules are consistent."""
import re
from pathlib import Path

FRONTEND = Path(__file__).resolve().parent.parent / "src" / "frontend"
JS_FILES = sorted((FRONTEND / "js").rglob("*.js"))


def test_index_is_served_at_ui(client):
    r = client.get("/ui/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert 'type="module"' in r.text and 'id="view"' in r.text


def test_every_js_file_is_served_with_a_javascript_mime_type(client):
    assert len(JS_FILES) >= 20
    for f in JS_FILES:
        rel = f.relative_to(FRONTEND).as_posix()
        r = client.get(f"/ui/{rel}")
        assert r.status_code == 200, rel
        assert "javascript" in r.headers["content-type"], f"{rel}: {r.headers['content-type']}"


def test_css_is_served(client):
    r = client.get("/ui/css/styles.css")
    assert r.status_code == 200 and "text/css" in r.headers["content-type"]


def test_security_headers(client):
    ui = client.get("/ui/")
    csp = ui.headers["content-security-policy"]
    assert "script-src 'self'" in csp and "frame-ancestors 'none'" in csp
    assert ui.headers["x-content-type-options"] == "nosniff"
    api = client.get("/api/v1/health")
    assert api.headers["x-content-type-options"] == "nosniff"
    assert "content-security-policy" not in api.headers


def test_swagger_docs_are_not_restricted_by_the_ui_policy(client):
    assert "content-security-policy" not in client.get("/docs").headers


def test_index_has_no_inline_script_or_style(client):
    html = (FRONTEND / "index.html").read_text(encoding="utf-8")
    assert not re.search(r"<script(?![^>]*\bsrc=)", html), "inline <script> would be blocked by the CSP"
    assert "<style" not in html and ' style="' not in html


def test_js_never_uses_unsafe_dom_apis():
    for f in JS_FILES:
        text = f.read_text(encoding="utf-8")
        for bad in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval(", 'setAttribute("style"'):
            assert bad not in text, f"{f.name} uses {bad}"


def test_relative_imports_resolve():
    for f in JS_FILES:
        for rel in re.findall(r'from "(\.[^"]+)"', f.read_text(encoding="utf-8")):
            assert (f.parent / rel).resolve().exists(), f"{f.name} imports missing file {rel}"
