"""Input sanitization utilities stripping malicious tags and script injections."""

import html
import re

_DANGEROUS_PATTERNS = re.compile(
    r"(<script[^>]*>.*?</script>|javascript:|onerror\s*=|onload\s*=|<iframe.*?>)",
    re.IGNORECASE | re.DOTALL,
)


def sanitize_text(val: str | None) -> str | None:
    """Strips dangerous script tags and escapes HTML entities from user input."""
    if val is None:
        return None
    cleaned = _DANGEROUS_PATTERNS.sub("", val).strip()
    return html.escape(cleaned, quote=False)
