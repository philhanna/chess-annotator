# tests.test_pdf_renderer
from pathlib import Path

import chess
import pytest

from annotate.adapters.chess_svg_diagram_renderer import ChessSvgDiagramRenderer
from annotate.adapters.pdf_renderer import render_pdf
from annotate.domain.game_headers import GameHeaders
from annotate.domain.plied_move import PliedMove
from annotate.domain.render_model import (
    build_segments,
    caption_text,
    collect_moves,
    format_date,
    moves_text,
    parse_pgn,
    subtitle_text,
)
from annotate.domain.segment import Segment

TESTDATA = Path(__file__).parent / "testdata"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_move(ply, san, nag_symbol=None, comment="", diagram_board=None, result=None):
    return PliedMove(ply=ply, san=san, nag_symbol=nag_symbol,
                     diagram_board=diagram_board, comment=comment, result=result)


def _seg(moves, comment="", diagram_move=None):
    return Segment(moves=tuple(moves), comment=comment, diagram_move=diagram_move)


# ---------------------------------------------------------------------------
# format_date
# ---------------------------------------------------------------------------

def test_format_date_full():
    assert format_date("2026.03.30") == "30 Mar 2026"


def test_format_date_no_day():
    assert format_date("2026.03.??") == "Mar 2026"


def test_format_date_year_only():
    assert format_date("2026.??.??") == "2026"


def test_format_date_all_missing():
    assert format_date("????.??.??") == ""


# ---------------------------------------------------------------------------
# subtitle_text
# ---------------------------------------------------------------------------

def test_subtitle_event_and_date():
    h = GameHeaders(white="", black="", event="World Championship",
                    date="2026.03.30", opening="")
    assert subtitle_text(h) == "World Championship, 30 Mar 2026"


def test_subtitle_event_only():
    h = GameHeaders(white="", black="", event="Blitz Open",
                    date="????.??.??", opening="")
    assert subtitle_text(h) == "Blitz Open"


def test_subtitle_date_only():
    h = GameHeaders(white="", black="", event="",
                    date="2026.??.??", opening="")
    assert subtitle_text(h) == "2026"


def test_subtitle_neither():
    h = GameHeaders(white="", black="", event="",
                    date="????.??.??", opening="")
    assert subtitle_text(h) is None


# ---------------------------------------------------------------------------
# moves_text
# ---------------------------------------------------------------------------

def test_moves_text_white_start():
    seg = _seg([_make_move(1, "e4"), _make_move(2, "d5"), _make_move(3, "exd5")])
    assert moves_text(seg) == "1. e4 d5 2. exd5"


def test_moves_text_black_start():
    seg = _seg([_make_move(4, "Qxd5"), _make_move(5, "Nc3")])
    assert moves_text(seg) == "2... Qxd5 3. Nc3"


def test_moves_text_nag_symbol():
    seg = _seg([_make_move(1, "e4"), _make_move(2, "d5", nag_symbol="!")])
    assert moves_text(seg) == "1. e4 d5!"


def test_moves_text_diagram_nag_not_shown():
    board = chess.Board()
    board.push_san("e4")
    move = _make_move(ply=1, san="e4", diagram_board=board)
    seg = _seg([move], diagram_move=move)
    assert moves_text(seg) == "1. e4"


def test_moves_text_full_sequence():
    moves = [
        _make_move(1, "e4"),
        _make_move(2, "d5"),
        _make_move(3, "exd5", nag_symbol="?"),
        _make_move(4, "Qxd5"),
    ]
    seg = _seg(moves)
    assert moves_text(seg) == "1. e4 d5 2. exd5? Qxd5"


def test_moves_text_appends_result_to_final_move():
    seg = _seg([_make_move(1, "e4"), _make_move(2, "e5", result="1/2-1/2")])
    assert moves_text(seg) == "1. e4 e5 1/2-1/2"


# ---------------------------------------------------------------------------
# caption_text
# ---------------------------------------------------------------------------

def test_caption_white_move():
    assert caption_text(_make_move(ply=5, san="Nc3")) == "After 3. Nc3"


def test_caption_black_move():
    assert caption_text(_make_move(ply=6, san="Qd8")) == "After 3 ... Qd8"


def test_caption_ply_1():
    assert caption_text(_make_move(ply=1, san="e4")) == "After 1. e4"


def test_caption_ply_2():
    assert caption_text(_make_move(ply=2, san="d5")) == "After 1 ... d5"


# ---------------------------------------------------------------------------
# build_segments
# ---------------------------------------------------------------------------

def test_no_comments_one_segment():
    moves = [_make_move(1, "e4"), _make_move(2, "d5"), _make_move(3, "exd5")]
    segs = build_segments(moves)
    assert len(segs) == 1
    assert segs[0].comment == ""
    assert len(segs[0].moves) == 3


def test_comment_on_move_1_one_segment():
    moves = [_make_move(1, "e4", comment="Good opening."), _make_move(2, "d5")]
    segs = build_segments(moves)
    assert len(segs) == 1
    assert segs[0].comment == "Good opening."


def test_comment_splits_into_two_segments():
    moves = [
        _make_move(1, "e4"),
        _make_move(2, "d5"),
        _make_move(3, "Nc3", comment="White develops."),
        _make_move(4, "Nf6"),
    ]
    segs = build_segments(moves)
    assert len(segs) == 2
    assert segs[0].comment == ""
    assert len(segs[0].moves) == 2
    assert segs[1].comment == "White develops."
    assert len(segs[1].moves) == 2


def test_multiple_comments_three_segments():
    moves = [
        _make_move(1, "e4"),
        _make_move(2, "d5", comment="Scandinavian."),
        _make_move(3, "exd5"),
        _make_move(4, "Qxd5", comment="Recapture."),
    ]
    segs = build_segments(moves)
    assert len(segs) == 3
    assert segs[0].comment == ""
    assert segs[1].comment == "Scandinavian."
    assert segs[2].comment == "Recapture."


def test_first_diagram_per_segment_used():
    board1 = chess.Board()
    board1.push_san("e4")
    board2 = chess.Board()
    board2.push_san("e4")
    board2.push_san("d5")
    m1 = _make_move(1, "e4", diagram_board=board1)
    m2 = _make_move(2, "d5", diagram_board=board2)
    segs = build_segments([m1, m2])
    assert segs[0].diagram_move is m1


def test_no_diagram_move_is_none():
    moves = [_make_move(1, "e4"), _make_move(2, "d5")]
    segs = build_segments(moves)
    assert segs[0].diagram_move is None


def test_empty_moves_returns_empty():
    assert build_segments([]) == ()


def test_collect_moves_sets_result_on_final_move():
    pgn_text = (TESTDATA / "game1.pgn").read_text()
    model = parse_pgn(pgn_text)
    assert model.segments[-1].moves[-1].result == "0-1"


# ---------------------------------------------------------------------------
# diagram rendering
# ---------------------------------------------------------------------------

def test_chess_svg_diagram_renderer_uses_white_margin_and_black_coordinates():
    svg = ChessSvgDiagramRenderer().render(chess.Board(), "white")
    assert 'stroke="#ffffff"' in svg
    assert 'fill="#000000" stroke="none"' in svg


# ---------------------------------------------------------------------------
# Smoke tests — render_pdf produces a non-empty PDF file
# ---------------------------------------------------------------------------

def test_smoke_render_game1(tmp_path):
    pgn_text = (TESTDATA / "game1.pgn").read_text()
    out = tmp_path / "game1.pdf"
    render_pdf(pgn_text, output_path=out)
    assert out.exists()
    assert out.stat().st_size > 0


def test_smoke_render_game2(tmp_path):
    pgn_text = (TESTDATA / "game2.pgn").read_text()
    out = tmp_path / "game2.pdf"
    render_pdf(pgn_text, output_path=out)
    assert out.exists()
    assert out.stat().st_size > 0


def test_smoke_render_black_orientation(tmp_path):
    pgn_text = (TESTDATA / "game1.pgn").read_text()
    out = tmp_path / "game1_black.pdf"
    render_pdf(pgn_text, output_path=out, orientation="black")
    assert out.exists()
    assert out.stat().st_size > 0
