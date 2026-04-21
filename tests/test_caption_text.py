# tests.test_caption_text
from render.domain.render_model import caption_text
from tests.pdf_renderer_support import make_move


def test_caption_white_move():
    assert caption_text(make_move(ply=5, san="Nc3")) == "After 3. Nc3"


def test_caption_black_move():
    assert caption_text(make_move(ply=6, san="Qd8")) == "After 3 ... Qd8"


def test_caption_ply_1():
    assert caption_text(make_move(ply=1, san="e4")) == "After 1. e4"


def test_caption_ply_2():
    assert caption_text(make_move(ply=2, san="d5")) == "After 1 ... d5"
