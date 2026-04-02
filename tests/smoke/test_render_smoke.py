# tests.smoke
"""End-to-end smoke test for the M3 rendering pipeline."""

from pathlib import Path

import pytest

from annotate.adapters.markdown_html_pdf_renderer import MarkdownHTMLPDFRenderer
from annotate.domain.annotation import Annotation
from annotate.domain.model import ply_from_move
from annotate.domain.segment import Segment
from annotate.use_cases.interactors import split_segment

_RUY_LOPEZ_PGN = (
    "[Event \"Test\"]\n"
    "[White \"White\"]\n"
    "[Black \"Black\"]\n"
    "[Result \"*\"]\n"
    "\n"
    "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 "
    "6. Re1 b5 7. Bb3 d6 8. c3 O-O 9. h3 Nb8 10. d4 Nbd7 *\n"
)


def test_render_produces_non_empty_pdf(tmp_path):
    annotation = Annotation.create(
        title="Test Game",
        author="Tester",
        date="2024-01-01",
        pgn=_RUY_LOPEZ_PGN,
        player_side="white",
    )

    # Split into two segments at move 6 white (ply 11)
    annotation = split_segment(annotation, ply_from_move(6, "white"))

    # Label both segments
    annotation.segments[0].label = "The Opening"
    annotation.segments[1].label = "The Middlegame"

    # Add commentary and a diagram to the first segment
    annotation.segments[0].commentary = "White opens with the Ruy Lopez."
    annotation.segments[0].show_diagram = True

    output_path = tmp_path / "test_output.pdf"
    store_dir = tmp_path / "store"

    renderer = MarkdownHTMLPDFRenderer()
    renderer.render(
        annotation,
        output_path=output_path,
        diagram_size=200,
        page_size="a4",
        store_dir=store_dir,
    )

    assert output_path.exists()
    assert output_path.stat().st_size > 0
