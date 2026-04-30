"""HTML → plain-text conversion for job descriptions.

Multiple scrapers (RemoteOK, JobSpy, Adzuna) return descriptions as raw HTML
fragments. Storing the raw HTML and rendering it on the frontend produced
literal `<p>` tags in the UI. We strip on ingest instead — render path stays
simple, and one canonical text representation is easier to search/score on.

Preserves paragraph breaks (`<p>`, `<br>`, `<li>`) as `\n\n` / `\n` so the
output is still readable in a `<pre whitespace-pre-wrap>` element. Trims
runs of 3+ newlines back down to 2 to avoid huge gaps.
"""
import re

from bs4 import BeautifulSoup, NavigableString

_BLOCK_TAGS = {"p", "div", "section", "article", "header", "footer", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "pre"}
_LINEBREAK_TAGS = {"br", "hr"}
_LIST_BULLET_TAGS = {"li"}


def strip_html(text: str | None) -> str | None:
    """Return plain text from an HTML fragment, or pass through if not HTML.

    Returns None on None input. Empty string on whitespace-only.
    """
    if text is None:
        return None
    if "<" not in text or ">" not in text:
        # Already plain — short-circuit to skip the BS4 overhead.
        return text.strip() or ""

    soup = BeautifulSoup(text, "html.parser")

    # Remove script/style entirely; their text content is never useful for a
    # job description ("/* css */", "var x=…").
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    parts: list[str] = []
    for node in soup.descendants:
        if isinstance(node, NavigableString):
            parent_name = node.parent.name if node.parent else ""
            if parent_name in {"script", "style", "noscript"}:
                continue
            parts.append(str(node))
        elif node.name in _LINEBREAK_TAGS:
            parts.append("\n")
        elif node.name in _LIST_BULLET_TAGS:
            parts.append("\n• ")
        elif node.name in _BLOCK_TAGS:
            # Block boundary — emit a paragraph break before block content.
            parts.append("\n\n")

    out = "".join(parts)
    # Collapse 3+ blank lines into double-newline; trim trailing whitespace per line.
    out = re.sub(r"[ \t]+\n", "\n", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()
