from __future__ import annotations

from pathlib import Path

from chessplan.domain import GameHeaders, GameRecord, MovePair


class PythonChessGameLoader:
    def load_game(self, pgn_path: Path) -> GameRecord:
        import chess
        import chess.pgn

        with pgn_path.open("r", encoding="utf-8") as fh:
            first_game = chess.pgn.read_game(fh)
            if first_game is None:
                raise SystemExit(f"No game found in {pgn_path}")
            second_game = chess.pgn.read_game(fh)
            if second_game is not None:
                raise SystemExit(
                    f"Expected exactly one game in {pgn_path}, but found more than one. "
                    "Split the PGN first or use a file containing just one game."
                )

        return GameRecord(
            headers=GameHeaders(
                event=first_game.headers.get("Event", ""),
                site=first_game.headers.get("Site", ""),
                date=first_game.headers.get("Date", ""),
                white=first_game.headers.get("White", ""),
                black=first_game.headers.get("Black", ""),
                result=first_game.headers.get("Result", ""),
                white_elo=first_game.headers.get("WhiteElo", ""),
                black_elo=first_game.headers.get("BlackElo", ""),
                termination=first_game.headers.get("Termination", ""),
            ),
            move_pairs=self._move_pairs(first_game),
        )

    def _move_pairs(self, game: object) -> list[MovePair]:
        import chess

        board = game.board()
        pairs: list[MovePair] = []
        current_move_number = 1
        white_san: str | None = None

        for move in game.mainline_moves():
            san = board.san(move)
            if board.turn == chess.WHITE:
                current_move_number = board.fullmove_number
                white_san = san
            else:
                pairs.append(MovePair(current_move_number, white_san, san))
                white_san = None
            board.push(move)

        if white_san is not None:
            pairs.append(MovePair(current_move_number, white_san, None))

        return pairs
