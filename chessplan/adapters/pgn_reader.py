from __future__ import annotations

from pathlib import Path

from chessplan.domain import GameHeaders, GameRecord, MovePair
from chessplan.domain.chess_book import BookChunk, ChpMarker, ParsedChessBook, PlayedMove


class PythonChessGameLoader:
    """Load PGN data using the `python-chess` parser."""

    def load_game(self, pgn_path: Path) -> GameRecord:
        """Read exactly one game from a PGN file and normalize its fields.

        Raises
        ------
        SystemExit
            If the file contains zero games or more than one game.
        """

        first_game = self._read_single_game(pgn_path)

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

    def load_chess_book(self, pgn_path: Path) -> ParsedChessBook:
        """Parse a PGN and extract normalized ``#chp`` chunk metadata."""

        game = self._read_single_game(pgn_path)
        self._ensure_no_chp_in_variations(game)

        board = game.board()
        moves: list[PlayedMove] = []
        chunk_markers: dict[int, ChpMarker] = {}

        for node in game.mainline():
            move = node.move
            if move is None:
                continue
            san = board.san(move)
            side = "white" if board.turn else "black"
            moves.append(
                PlayedMove(
                    ply_index=len(moves) + 1,
                    move_number=board.fullmove_number,
                    side=side,
                    san=san,
                )
            )
            board.push(move)
            marker = self._parse_chp_comment(node.comment, self._node_location(node))
            if marker is not None:
                chunk_markers[len(moves)] = marker

        trailing_comments = ""
        if moves:
            last_marker = chunk_markers[max(chunk_markers)] if chunk_markers else None
            trailing_comments = last_marker.comments if last_marker is not None else ""

        return ParsedChessBook(
            moves=moves,
            chunk_markers=chunk_markers,
            trailing_comments=trailing_comments,
        )

    def build_book_chunks(self, parsed_game: ParsedChessBook, *, perspective: str) -> list[BookChunk]:
        """Build rendered chunks, including SVG diagrams, from parsed PGN data."""

        if perspective not in {"white", "black"}:
            raise SystemExit("--side must be either 'white' or 'black'")

        import chess
        import chess.svg

        if not parsed_game.moves:
            return []

        chunks: list[BookChunk] = []
        start_index = 0
        total_moves = len(parsed_game.moves)
        ordered_marker_positions = sorted(parsed_game.chunk_markers)

        for end_index in ordered_marker_positions:
            move_text = self._format_move_text(parsed_game.moves[start_index:end_index])
            marker = parsed_game.chunk_markers[end_index]
            board = self._board_after_ply(parsed_game.moves, end_index)
            chunks.append(
                BookChunk(
                    move_text=move_text,
                    comments=marker.comments,
                    svg=None
                    if end_index == total_moves
                    else chess.svg.board(board=board, orientation=chess.WHITE if perspective == "white" else chess.BLACK),
                )
            )
            start_index = end_index

        if start_index < total_moves:
            move_text = self._format_move_text(parsed_game.moves[start_index:total_moves])
            chunks.append(
                BookChunk(
                    move_text=move_text,
                    comments=parsed_game.trailing_comments,
                    svg=None,
                )
            )

        return chunks

    def _move_pairs(self, game: object) -> list[MovePair]:
        """Convert a python-chess game into display-friendly move pairs."""

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

    def _read_single_game(self, pgn_path: Path) -> object:
        """Read exactly one PGN game from disk and return the python-chess node tree."""

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
        return first_game

    def _ensure_no_chp_in_variations(self, game: object) -> None:
        """Reject ``#chp`` markers that appear outside the mainline."""

        for variation in list(getattr(game, "variations", []))[1:]:
            self._ensure_subtree_has_no_chp(variation)

        for node in game.mainline():
            for variation in list(getattr(node, "variations", []))[1:]:
                self._ensure_subtree_has_no_chp(variation)

    def _ensure_subtree_has_no_chp(self, node: object) -> None:
        """Walk a variation subtree and fail if any node comment starts with ``#chp``."""

        comment = getattr(node, "comment", "")
        if self._comment_is_chp(comment):
            raise SystemExit(f"Invalid #chp marker in variation at {self._node_location(node)}")
        for variation in getattr(node, "variations", []):
            self._ensure_subtree_has_no_chp(variation)

    def _parse_chp_comment(self, raw_comment: str, location: str) -> ChpMarker | None:
        """Parse one ``#chp`` comment or return ``None`` for ordinary comments."""

        if not self._comment_is_chp(raw_comment):
            return None

        payload = raw_comment.strip()[4:].strip()
        if not payload:
            raise SystemExit(f"Malformed #chp marker at {location}: missing fields")

        parsed_fields: dict[str, str] = {}
        for raw_part in payload.split(";"):
            part = raw_part.strip()
            if not part:
                continue
            if ":" not in part:
                raise SystemExit(f"Malformed #chp marker at {location}: invalid field syntax '{part}'")
            key, value = part.split(":", 1)
            normalized_key = key.strip()
            normalized_value = value.strip()
            if normalized_key not in {"label", "kind", "comments"}:
                raise SystemExit(
                    f"Malformed #chp marker at {location}: unknown field '{normalized_key}'"
                )
            if normalized_key in parsed_fields:
                raise SystemExit(
                    f"Malformed #chp marker at {location}: duplicate field '{normalized_key}'"
                )
            parsed_fields[normalized_key] = normalized_value

        marker = ChpMarker(
            label=parsed_fields.get("label", ""),
            kind=parsed_fields.get("kind", ""),
            comments=parsed_fields.get("comments", ""),
        )
        errors = marker.validate()
        if errors:
            raise SystemExit(f"Malformed #chp marker at {location}: {'; '.join(errors)}")
        return marker

    def _comment_is_chp(self, raw_comment: str) -> bool:
        """Return ``True`` when the comment is a structured ``#chp`` marker."""

        return raw_comment.lstrip().startswith("#chp")

    def _node_location(self, node: object) -> str:
        """Describe the move location for error messages."""

        board = node.board()
        if node.move is None:
            return "game start"
        if board.turn:
            return f"{board.fullmove_number}."
        return f"{board.fullmove_number}..."

    def _board_after_ply(self, moves: list[PlayedMove], ply_index: int) -> object:
        """Recreate the board after the supplied 1-based ply index."""

        import chess

        board = chess.Board()
        for move in moves[:ply_index]:
            board.push_san(move.san)
        return board

    def _format_move_text(self, moves: list[PlayedMove]) -> str:
        """Render a contiguous move slice as compact PGN-style text."""

        tokens: list[str] = []
        previous_move: PlayedMove | None = None

        for move in moves:
            if move.side == "white":
                tokens.append(f"{move.move_number}. {move.san}")
            elif previous_move is not None and previous_move.side == "white" and previous_move.move_number == move.move_number:
                tokens.append(move.san)
            else:
                tokens.append(f"{move.move_number}... {move.san}")
            previous_move = move

        return " ".join(tokens)
