# tests.test_render_pdf_smoke
from render.adapters.pdf_renderer import render_pdf
from tests.pdf_renderer_support import TESTDATA


def test_smoke_render_game1(tmp_path):
    pgn_text = (TESTDATA / "game1.pgn").read_text()
    output_path = tmp_path / "game1.pdf"
    render_pdf(pgn_text, output_path=output_path)
    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_smoke_render_game2(tmp_path):
    pgn_text = (TESTDATA / "game2.pgn").read_text()
    output_path = tmp_path / "game2.pdf"
    render_pdf(pgn_text, output_path=output_path)
    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_smoke_render_black_orientation(tmp_path):
    pgn_text = (TESTDATA / "game1.pgn").read_text()
    output_path = tmp_path / "game1_black.pdf"
    render_pdf(pgn_text, output_path=output_path, orientation="black")
    assert output_path.exists()
    assert output_path.stat().st_size > 0
