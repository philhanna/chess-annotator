from pathlib import Path

import pytest

from chessplan.adapters.pgn_reader import PythonChessGameLoader


def test_load_game_reads_headers_and_move_pairs() -> None:
    loader = PythonChessGameLoader()

    game = loader.load_game(Path("tests/testdata/mygame.pgn"))

    assert game.headers.event == "Live Chess"
    assert game.headers.white == "pehanna7"
    assert game.headers.black == "fasmang"
    assert game.headers.white_elo == "1175"
    assert game.headers.black_elo == "1216"
    assert game.headers.result == "1-0"
    assert game.max_fullmove_number == 45
    assert game.move_pairs[0].white_san == "d4"
    assert game.move_pairs[0].black_san == "d5"
    assert game.move_pairs[-1].move_number == 45
    assert game.move_pairs[-1].white_san == "Rh7#"
    assert game.move_pairs[-1].black_san is None


def test_load_game_rejects_empty_pgn(tmp_path: Path) -> None:
    loader = PythonChessGameLoader()
    pgn_path = tmp_path / "empty.pgn"
    pgn_path.write_text("", encoding="utf-8")

    with pytest.raises(SystemExit, match="No game found"):
        loader.load_game(pgn_path)


def test_load_game_rejects_multiple_games(tmp_path: Path) -> None:
    loader = PythonChessGameLoader()
    pgn_path = tmp_path / "many.pgn"
    pgn_path.write_text(
        (
            '[Event "Game 1"]\n\n1. e4 e5 2. Nf3 Nc6 1-0\n\n'
            '[Event "Game 2"]\n\n1. d4 d5 0-1\n'
        ),
        encoding="utf-8",
    )

    with pytest.raises(SystemExit, match="Expected exactly one game"):
        loader.load_game(pgn_path)
