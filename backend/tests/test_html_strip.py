"""Coverage for app.utils.html_strip — RemoteOK-style fragments are the main case."""
from app.utils.html_strip import strip_html


def test_none_passthrough():
    assert strip_html(None) is None


def test_plain_text_passthrough():
    assert strip_html("Already plain") == "Already plain"
    assert strip_html("  whitespace trimmed  ") == "whitespace trimmed"


def test_strips_simple_tags():
    out = strip_html("<p>Hello <b>world</b></p>")
    assert out == "Hello world"


def test_preserves_paragraph_breaks():
    out = strip_html("<p>First paragraph.</p><p>Second paragraph.</p>")
    assert "First paragraph." in out
    assert "Second paragraph." in out
    assert "\n\n" in out


def test_remoteok_style_fragment():
    """The exact shape that produced literal `<p>` tags in the UI."""
    raw = (
        "<p>At Verint, we believe customer engagement is the core...</p>"
        "<p>Overview of Job Function:</p>"
        "<p>As a Software Engineer, you will be a core contributor...</p>"
    )
    out = strip_html(raw)
    assert "<p>" not in out
    assert "</p>" not in out
    assert "At Verint" in out
    assert "Software Engineer" in out


def test_list_items_get_bullets():
    raw = "<ul><li>Build features</li><li>Ship fast</li></ul>"
    out = strip_html(raw)
    assert "• Build features" in out
    assert "• Ship fast" in out


def test_br_becomes_newline():
    out = strip_html("Line one<br>Line two")
    assert "Line one\nLine two" in out


def test_drops_script_and_style():
    raw = "<p>Real content</p><script>alert('xss')</script><style>body{}</style>"
    out = strip_html(raw)
    assert "Real content" in out
    assert "alert" not in out
    assert "body{}" not in out


def test_collapses_excessive_blank_lines():
    raw = "<p>First</p><p></p><p></p><p></p><p>Second</p>"
    out = strip_html(raw)
    # Should have at most a single double-newline gap between, not 8 lines of blank.
    assert "First\n\nSecond" in out


def test_empty_string():
    assert strip_html("") == ""


def test_html_entities_decoded():
    out = strip_html("<p>5 &amp; 6 &lt; 10</p>")
    assert out == "5 & 6 < 10"
