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
    assert "**1. e4 e5**" in output
    assert "**2. Nf3**" in output
    assert "**2... Nc6 3. Bb5 a6**" in output
    assert "Fight for the center." in output
    assert "Switch into Ruy Lopez ideas." in output
    assert "ordinary comment" not in output
    assert output.count("<svg") == 2


def test_build_book_chunks_omits_svg_for_final_explicit_chunk() -> None:
    loader = PythonChessGameLoader()
    pgn_path = Path("tests/testdata/final-marker-book.pgn")

    parsed_game = loader.load_chess_book(pgn_path)
    chunks = loader.build_book_chunks(parsed_game, perspective="black")

    assert len(chunks) == 1
    assert chunks[0].move_text == "1. d4 d5 2. c4 e6"
    assert chunks[0].comments == "Classical QGD start."
    assert chunks[0].svg is None


def test_load_chess_book_rejects_unknown_field(tmp_path: Path) -> None:
    loader = PythonChessGameLoader()
    pgn_path = tmp_path / "bad-field.pgn"
    pgn_path.write_text(
        '[Event "Bad"]\n\n1. e4 {#chp label: Test; kind: plan; note: nope} e5 1-0\n',
        encoding="utf-8",
    )

    with pytest.raises(SystemExit, match="unknown field 'note'"):
        loader.load_chess_book(pgn_path)


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

    assert "**1. e4 e5**" in output
    assert output.count("<svg") == 1
    assert "\n\n\n" not in output
