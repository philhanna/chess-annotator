from pathlib import Path

import pytest

from annotate.adapters.markdown_html_pdf_renderer import (
    MarkdownHTMLPDFRenderer,
    _build_html,
    _build_markdown,
    _substitute_diagram_tokens,
)
from annotate.domain.annotation import Annotation
from annotate.domain.segment import SegmentContent

_PGN = (
    "[Event \"Test\"]\n"
    "[White \"White\"]\n"
    "[Black \"Black\"]\n"
    "[Result \"*\"]\n"
    "\n"
    "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 *\n"
)


class FakeDiagramRenderer:
    def __init__(self) -> None:
        self.calls = []

    def render(self, pgn, ply, orientation, size, cache_dir):
        self.calls.append((pgn, ply, orientation, size, cache_dir))
        cache_dir.mkdir(parents=True, exist_ok=True)
        path = cache_dir / f"{ply}-{orientation}.svg"
        path.write_text("<svg/>")
        return path


def make_annotation() -> Annotation:
    return Annotation(
        game_id="game-1",
        title="White - Black",
        author="Tester",
        date="2024-01-01",
        pgn=_PGN,
        player_side="white",
        turning_points=[1, 5],
        segment_contents={
            1: SegmentContent(label="Opening", annotation="Develop pieces"),
            5: SegmentContent(
                label="Pressure",
                annotation="Pin the knight\n\n[[diagram 2b]]",
            ),
        },
    )


def test_render_rejects_missing_annotation(tmp_path):
    annotation = make_annotation()
    annotation.segment_contents[5].annotation = ""
    renderer = MarkdownHTMLPDFRenderer(diagram_renderer=FakeDiagramRenderer())

    with pytest.raises(ValueError, match="must have both label and annotation"):
        renderer.render(
            annotation,
            output_path=tmp_path / "game-1" / "output.pdf",
            diagram_size=200,
            page_size="a4",
            store_dir=tmp_path,
        )


def test_render_uses_game_directory_cache_and_writes_pdf(tmp_path, monkeypatch):
    annotation = make_annotation()
    diagram_renderer = FakeDiagramRenderer()
    renderer = MarkdownHTMLPDFRenderer(diagram_renderer=diagram_renderer)
    written = {}

    class FakeHTML:
        def __init__(self, string):
            written["html"] = string

        def write_pdf(self, output_path):
            Path(output_path).write_text("pdf")

    monkeypatch.setattr("annotate.adapters.markdown_html_pdf_renderer.weasyprint.HTML", FakeHTML)

    output_path = tmp_path / "game-1" / "output.pdf"
    renderer.render(
        annotation,
        output_path=output_path,
        diagram_size=220,
        page_size="letter",
        store_dir=tmp_path,
    )

    assert output_path.exists()
    # The [[diagram 2b]] token in segment 5's annotation should trigger a render call.
    assert diagram_renderer.calls
    assert diagram_renderer.calls[0][4] == tmp_path / "game-1" / "diagram-cache"
    assert "Develop pieces" in written["html"]
    assert "Pin the knight" in written["html"]


def test_diagram_token_is_substituted_inline(tmp_path, monkeypatch):
    """A [[diagram ...]] token in annotation text is replaced with an SVG figure block."""
    annotation = make_annotation()
    diagram_renderer = FakeDiagramRenderer()
    renderer = MarkdownHTMLPDFRenderer(diagram_renderer=diagram_renderer)
    written = {}

    class FakeHTML:
        def __init__(self, string):
            written["html"] = string

        def write_pdf(self, output_path):
            Path(output_path).write_text("pdf")

    monkeypatch.setattr("annotate.adapters.markdown_html_pdf_renderer.weasyprint.HTML", FakeHTML)

    renderer.render(
        annotation,
        output_path=tmp_path / "game-1" / "output.pdf",
        diagram_size=220,
        page_size="a4",
        store_dir=tmp_path,
    )

    html = written["html"]
    # Token should be replaced by a figure block.
    assert "[[diagram 2b]]" not in html
    assert '<figure class="diagram">' in html
    assert "<figcaption>After 2...Nc6</figcaption>" in html


def test_build_html_preserves_embedded_html_and_svg_markup(tmp_path):
    annotation = make_annotation()
    diagram_path = tmp_path / "diagram.svg"
    diagram_path.write_text('<svg xmlns="http://www.w3.org/2000/svg"><text>board</text></svg>')

    # Ply 4 = move 2 black = "2...Nc6"; orientation "white"
    markdown = _build_markdown(annotation, {(4, "white"): diagram_path})
    html = _build_html(markdown, "a4")

    assert '<p class="byline">Tester' in html
    assert '<code class="move-list">' in html
    assert '<svg xmlns="http://www.w3.org/2000/svg">' in html
    assert "<figcaption>After 2...Nc6</figcaption>" in html
    assert "&lt;p" not in html
    assert "&lt;svg" not in html


def test_substitute_diagram_tokens_replaces_known_token(tmp_path):
    svg_path = tmp_path / "4-white.svg"
    svg_path.write_text("<svg/>")
    diagram_paths = {(4, "white"): svg_path}

    result = _substitute_diagram_tokens("Before [[diagram 2b]] After", diagram_paths, _PGN)

    assert "[[diagram 2b]]" not in result
    assert "<svg/>" in result
    assert "After 2...Nc6" in result
    assert "Before" in result
    assert "After" in result


def test_substitute_diagram_tokens_leaves_unknown_token(tmp_path):
    result = _substitute_diagram_tokens("[[diagram 99w]]", {}, _PGN)
    assert result == "[[diagram 99w]]"


def test_substitute_diagram_tokens_default_orientation(tmp_path):
    svg_path = tmp_path / "1-white.svg"
    svg_path.write_text("<svg/>")
    # Token without explicit orientation defaults to white.
    result = _substitute_diagram_tokens("[[diagram 1w]]", {(1, "white"): svg_path}, _PGN)
    assert "<svg/>" in result


def test_substitute_diagram_tokens_explicit_black_orientation(tmp_path):
    svg_path = tmp_path / "1-black.svg"
    svg_path.write_text("<svg/>")
    result = _substitute_diagram_tokens(
        "[[diagram 1w black]]", {(1, "black"): svg_path}, _PGN
    )
    assert "<svg/>" in result
