# tests.test_diagram_rendering
import chess

from annotate.adapters.chess_svg_diagram_renderer import ChessSvgDiagramRenderer


def test_chess_svg_diagram_renderer_uses_white_margin_and_black_coordinates():
    svg = ChessSvgDiagramRenderer().render(chess.Board(), "white")
    assert 'stroke="#ffffff"' in svg
    assert 'fill="#000000" stroke="none"' in svg
