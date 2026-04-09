from pathlib import Path

import pytest

from annotate.adapters.markdown_html_pdf_renderer import (
    MarkdownHTMLPDFRenderer,
    _build_html,
    _build_markdown,
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

    def render(self, pgn, end_ply, orientation, size, cache_dir):
        self.calls.append((pgn, end_ply, orientation, size, cache_dir))
        cache_dir.mkdir(parents=True, exist_ok=True)
        path = cache_dir / f"{end_ply}-{orientation}.svg"
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
        diagram_orientation="white",
        turning_points=[1, 5],
        segment_contents={
            1: SegmentContent(label="Opening", annotation="Develop pieces"),
            5: SegmentContent(label="Pressure", annotation="Pin the knight"),
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
    assert diagram_renderer.calls
    assert diagram_renderer.calls[0][4] == tmp_path / "game-1" / "diagram-cache"
    assert "Develop pieces" in written["html"]


def test_build_html_preserves_embedded_html_and_svg_markup(tmp_path):
    annotation = make_annotation()
    diagram_path = tmp_path / "diagram.svg"
    diagram_path.write_text('<svg xmlns="http://www.w3.org/2000/svg"><text>board</text></svg>')

    markdown = _build_markdown(annotation, {0: diagram_path})
    html = _build_html(markdown, "a4")

    assert '<p class="byline">Tester' in html
    assert '<code class="move-list">' in html
    assert '<svg xmlns="http://www.w3.org/2000/svg">' in html
    assert "<figcaption>After 2...Nc6</figcaption>" in html
    assert "&lt;p" not in html
    assert "&lt;svg" not in html
