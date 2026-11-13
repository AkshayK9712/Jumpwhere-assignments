"""Input sanitization helpers (CRUD-002: data sanitization for security)."""
import re

_TAG_RE = re.compile(r"<[^>]*>")
_CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_SPACES_RE = re.compile(r"[ \t]+")


def clean_text(value: str, multiline: bool = False) -> str:
    """Remove HTML tags and control characters, trim, and collapse repeated spaces."""
    value = _CTRL_RE.sub("", value)
    value = _TAG_RE.sub("", value)
    if not multiline:
        value = value.replace("\r", " ").replace("\n", " ")
    value = _SPACES_RE.sub(" ", value)
    return value.strip()


def escape_like(term: str) -> str:
    """Escape % and _ so user search text is matched literally in LIKE queries."""
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
