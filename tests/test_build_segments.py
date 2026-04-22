# tests.test_build_segments
import chess

from render.domain.render_model import build_segments, parse_pgn
from tests.pdf_renderer_support import TESTDATA, make_move


def test_no_comments_one_segment():
    moves = [make_move(1, "e4"), make_move(2, "d5"), make_move(3, "exd5")]
    segments = build_segments(moves)
    assert len(segments) == 1
    assert segments[0].comment == ""
    assert len(segments[0].moves) == 3


def test_comment_on_move_1_one_segment():
    moves = [make_move(1, "e4", comment="Good opening."), make_move(2, "d5")]
    segments = build_segments(moves)
    assert len(segments) == 1
    assert segments[0].comment == "Good opening."


def test_comment_splits_into_two_segments():
    moves = [
        make_move(1, "e4"),
        make_move(2, "d5"),
        make_move(3, "Nc3", comment="White develops."),
        make_move(4, "Nf6"),
    ]
    segments = build_segments(moves)
    assert len(segments) == 2
    assert segments[0].comment == ""
    assert len(segments[0].moves) == 2
    assert segments[1].comment == "White develops."
    assert len(segments[1].moves) == 2


def test_multiple_comments_three_segments():
    moves = [
        make_move(1, "e4"),
        make_move(2, "d5", comment="Scandinavian."),
        make_move(3, "exd5"),
        make_move(4, "Qxd5", comment="Recapture."),
    ]
    segments = build_segments(moves)
    assert len(segments) == 3
    assert segments[0].comment == ""
    assert segments[1].comment == "Scandinavian."
    assert segments[2].comment == "Recapture."


def test_first_diagram_per_segment_used():
    board1 = chess.Board()
    board1.push_san("e4")
    board2 = chess.Board()
    board2.push_san("e4")
    board2.push_san("d5")
    move1 = make_move(1, "e4", diagram_board=board1)
    move2 = make_move(2, "d5", diagram_board=board2)
    segments = build_segments([move1, move2])
    assert segments[0].diagram_move is move1


def test_no_diagram_move_is_none():
    moves = [make_move(1, "e4"), make_move(2, "d5")]
    segments = build_segments(moves)
    assert segments[0].diagram_move is None


def test_empty_moves_returns_empty():
    assert build_segments([]) == ()


def test_collect_moves_sets_result_on_final_move():
    pgn_text = (TESTDATA / "game1.pgn").read_text()
    model = parse_pgn(pgn_text)
    assert model.segments[-1].moves[-1].result == "0-1"


def test_parse_pgn_captures_pre_game_comment():
    pgn_text = (
        '[White "A"]\n[Black "B"]\n\n'
        "{ This is the opening note. }\n"
        "1. e4 e5 *\n"
    )
    model = parse_pgn(pgn_text)
    assert model.pre_game_comment == "This is the opening note."


def test_parse_pgn_pre_game_comment_empty_when_absent():
    pgn_text = '[White "A"]\n[Black "B"]\n\n1. e4 e5 *\n'
    model = parse_pgn(pgn_text)
    assert model.pre_game_comment == ""
