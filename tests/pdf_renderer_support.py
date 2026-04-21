# tests.pdf_renderer_support
from pathlib import Path

from annotate.domain.plied_move import PliedMove
from annotate.domain.segment import Segment

TESTDATA = Path(__file__).parent / "testdata"


def make_move(ply, san, nag_symbol=None, comment="", diagram_board=None, result=None):
    return PliedMove(
        ply=ply,
        san=san,
        nag_symbol=nag_symbol,
        diagram_board=diagram_board,
        comment=comment,
        result=result,
    )


def make_segment(moves, comment="", diagram_move=None):
    return Segment(moves=tuple(moves), comment=comment, diagram_move=diagram_move)
