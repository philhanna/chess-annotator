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
        return self._render_document(parsed_game.headers, chunks)

    def _render_document(self, headers: object, chunks: list[BookChunk]) -> str:
        """Serialize the PGN header summary plus rendered chunks into Markdown."""

        lines: list[str] = []
        event = getattr(headers, "event", "").strip()
        date = getattr(headers, "date", "").strip()
        white = getattr(headers, "white", "").strip()
        black = getattr(headers, "black", "").strip()

        title = event
        if event and date:
            title = f"{event} ({date})"
        elif date:
            title = date

        if title:
            lines.append(f"# {title}")
        if white or black:
            lines.append(f"### {white} vs. {black}".strip())

        if lines and chunks:
            lines.append("")

        for index, chunk in enumerate(chunks):
            if index:
                lines.append("")
            if chunk.label:
                lines.append(f"### {chunk.label}")
                lines.append("")
            lines.append(f"**{chunk.move_text}**")
            if chunk.comments.strip():
                lines.append("")
                lines.append(chunk.comments)
            if chunk.svg:
                lines.append("")
                lines.append(chunk.svg)
        return "\n".join(lines).rstrip() + "\n"
