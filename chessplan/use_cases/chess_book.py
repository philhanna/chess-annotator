from __future__ import annotations

from pathlib import Path

from chessplan.adapters.pgn_reader import PythonChessGameLoader
from chessplan.domain.chess_book import BookChunk


class ChessBookService:
    """Render PGN-embedded ``#chp`` annotations as Markdown."""

    def __init__(self, game_loader: PythonChessGameLoader | None = None) -> None:
        self._game_loader = game_loader or PythonChessGameLoader()

    def render_markdown(self, pgn_path: Path, perspective: str) -> str:
        """Return Markdown for the PGN at ``pgn_path``."""

        parsed_game = self._game_loader.load_chess_book(pgn_path)
        chunks = self._game_loader.build_book_chunks(parsed_game, perspective=perspective)
        return self._render_chunks(chunks)

    def _render_chunks(self, chunks: list[BookChunk]) -> str:
        """Serialize rendered chunks into the CLI's Markdown format."""

        lines: list[str] = []
        for index, chunk in enumerate(chunks):
            if index:
                lines.append("")
            lines.append(f"**{chunk.move_text}**")
            if chunk.svg:
                lines.append("")
                lines.append(chunk.svg)
            if chunk.comments.strip():
                lines.append("")
                lines.append(chunk.comments)
        return "\n".join(lines).rstrip() + "\n"
