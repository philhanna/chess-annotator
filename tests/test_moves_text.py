# tests.test_moves_text
import chess

from annotate.domain.render_model import moves_text
from tests.pdf_renderer_support import make_move, make_segment


def test_moves_text_white_start():
    segment = make_segment([make_move(1, "e4"), make_move(2, "d5"), make_move(3, "exd5")])
    assert moves_text(segment) == "1. e4 d5 2. exd5"


def test_moves_text_black_start():
    segment = make_segment([make_move(4, "Qxd5"), make_move(5, "Nc3")])
    assert moves_text(segment) == "2... Qxd5 3. Nc3"


def test_moves_text_nag_symbol():
    segment = make_segment([make_move(1, "e4"), make_move(2, "d5", nag_symbol="!")])
    assert moves_text(segment) == "1. e4 d5!"


def test_moves_text_diagram_nag_not_shown():
    board = chess.Board()
    board.push_san("e4")
    move = make_move(ply=1, san="e4", diagram_board=board)
    segment = make_segment([move], diagram_move=move)
    assert moves_text(segment) == "1. e4"


def test_moves_text_full_sequence():
    moves = [
        make_move(1, "e4"),
        make_move(2, "d5"),
        make_move(3, "exd5", nag_symbol="?"),
        make_move(4, "Qxd5"),
    ]
    segment = make_segment(moves)
    assert moves_text(segment) == "1. e4 d5 2. exd5? Qxd5"


def test_moves_text_appends_result_to_final_move():
    segment = make_segment([make_move(1, "e4"), make_move(2, "e5", result="1/2-1/2")])
    assert moves_text(segment) == "1. e4 e5 1/2-1/2"
