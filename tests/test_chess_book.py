from pathlib import Path

import pytest

from chessbook import main
from chessplan.adapters.pgn_reader import PythonChessGameLoader
from chessplan.use_cases.chess_book import ChessBookService


def test_book_command_renders_markdown_chunks(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    pgn_path = tmp_path / "book.pgn"
    pgn_path.write_text(
        "\n".join(
                [
                    '[Event "Book Test"]',
                    '[Date "2026.03.29"]',
                    '[White "White"]',
                    '[Black "Black"]',
                    '[Result "1-0"]',
                "",
                "1. e4 e5 {#chp label: Open game; kind: plan; comments: Fight for the center.} "
                "2. Nf3 {#chp label: Spanish setup; kind: transition; comments: Switch into Ruy Lopez ideas.} "
                "Nc6 3. Bb5 a6 {ordinary comment} 1-0",
                "",
            ]
        ),
        encoding="utf-8",
    )

    assert main([str(pgn_path), "--side", "white"]) == 0

    output = capsys.readouterr().out
    assert "# Book Test (2026.03.29)" in output
    assert "### White vs. Black" in output
    assert "### Open game" in output
    assert "### Spanish setup" in output
    assert "**1. e4 e5**" in output
    assert "**2. Nf3**" in output
    assert "**2... Nc6 3. Bb5 a6**" in output
    assert "Fight for the center." in output
    assert "Switch into Ruy Lopez ideas." in output
    assert output.rstrip().endswith("**2... Nc6 3. Bb5 a6**")
    assert "ordinary comment" not in output
    assert output.count("<svg") == 2
    assert output.index("Fight for the center.") < output.index("<svg")
    assert "**1. e4 e5**\n\nFight for the center." in output


def test_build_book_chunks_omits_svg_for_final_explicit_chunk() -> None:
    loader = PythonChessGameLoader()
    pgn_path = Path("tests/testdata/final-marker-book.pgn")

    parsed_game = loader.load_chess_book(pgn_path)

    assert parsed_game.headers.event == "Final Marker"
    assert parsed_game.headers.white == "White"
    assert parsed_game.headers.black == "Black"
    chunks = loader.build_book_chunks(parsed_game, perspective="black")

    assert len(chunks) == 1
    assert chunks[0].label == "QGD setup"
    assert chunks[0].move_text == "1. d4 d5 2. c4 e6"
    assert chunks[0].comments == "Classical QGD start."
    assert chunks[0].svg is None


def test_board_reconstruction_uses_exact_moves_for_piece_positions() -> None:
    loader = PythonChessGameLoader()
    pgn_path = Path("tests/testdata/reconstruction-book.pgn")

    parsed_game = loader.load_chess_book(pgn_path)
    board = loader._board_after_ply(parsed_game.moves, 2)

    assert board.piece_at(28).symbol() == "P"  # e4
    assert board.piece_at(36).symbol() == "p"  # e5


def test_load_chess_book_rejects_unknown_field(tmp_path: Path) -> None:
    loader = PythonChessGameLoader()
    pgn_path = tmp_path / "bad-field.pgn"
    pgn_path.write_text(
        '[Event "Bad"]\n\n1. e4 {#chp label: Test; kind: plan; note: nope} e5 1-0\n',
        encoding="utf-8",
    )

    with pytest.raises(SystemExit, match="unknown field 'note'"):
        loader.load_chess_book(pgn_path)


def test_load_chess_book_accepts_comment_alias(tmp_path: Path) -> None:
    loader = PythonChessGameLoader()
    pgn_path = tmp_path / "comment-alias.pgn"
    pgn_path.write_text(
        '[Event "Alias"]\n\n1. e4 {#chp label: Test; kind: plan; comment: Keep pressure on e5.} e5 1-0\n',
        encoding="utf-8",
    )

    parsed_game = loader.load_chess_book(pgn_path)

    assert parsed_game.chunk_markers[1].comments == "Keep pressure on e5."


def test_load_chess_book_rejects_chp_in_variation(tmp_path: Path) -> None:
    loader = PythonChessGameLoader()
    pgn_path = tmp_path / "variation.pgn"
    pgn_path.write_text(
        (
            '[Event "Variation"]\n\n'
            '1. e4 (1. d4 {#chp label: Sideline; kind: plan; comments: Invalid here.} d5) e5 1-0\n'
        ),
        encoding="utf-8",
    )

    with pytest.raises(SystemExit, match="Invalid #chp marker in variation"):
        loader.load_chess_book(pgn_path)


def test_chess_book_service_renders_empty_comments_without_extra_paragraph(tmp_path: Path) -> None:
    service = ChessBookService()
    pgn_path = tmp_path / "no-comments.pgn"
    pgn_path.write_text(
        (
            '[Event "No Comments"]\n\n'
            '1. e4 e5 {#chp label: Equal start; kind: defense} 2. Nf3 Nc6 1/2-1/2\n'
        ),
        encoding="utf-8",
    )

    output = service.render_markdown(pgn_path, perspective="white")

    assert "# No Comments" in output
    assert "### Equal start" in output
    assert "**1. e4 e5**" in output
    assert output.count("<svg") == 1
    assert "\n\n\n" not in output


def test_rendered_svg_inlines_piece_shapes_instead_of_use_references(tmp_path: Path) -> None:
    service = ChessBookService()
    pgn_path = tmp_path / "inline-svg.pgn"
    pgn_path.write_text(
        (
            '[Event "Inline SVG"]\n\n'
            '1. e4 e5 {#chp label: Open game; kind: plan; comments: Inline pieces.} 2. Nf3 Nc6 1-0\n'
        ),
        encoding="utf-8",
    )

    output = service.render_markdown(pgn_path, perspective="white")

    assert "# Inline SVG" in output
    assert "### Open game" in output
    assert "<svg" in output
    assert "<use " not in output
    assert 'id="white-pawn"' not in output
