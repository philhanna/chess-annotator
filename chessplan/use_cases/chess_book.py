from __future__ import annotations

from html import escape
from pathlib import Path

from chessplan.adapters.pgn_reader import PythonChessGameLoader
from chessplan.domain.chess_book import BookChunk


class ChessBookService:
    """Render PGN-embedded ``#chp`` annotations as HTML."""

    def __init__(self, game_loader: PythonChessGameLoader | None = None) -> None:
        self._game_loader = game_loader or PythonChessGameLoader()

    def render_html(self, pgn_path: Path, perspective: str) -> str:
        """Return HTML for the PGN at ``pgn_path``."""

        parsed_game = self._game_loader.load_chess_book(pgn_path)
        chunks = self._game_loader.build_book_chunks(parsed_game, perspective=perspective)
        return self._render_document(parsed_game.headers, chunks)

    def _render_document(self, headers: object, chunks: list[BookChunk]) -> str:
        """Serialize the PGN header summary plus rendered chunks into HTML."""

        lines = [
            "<!doctype html>",
            '<html lang="en">',
            "<head>",
            '  <meta charset="utf-8">',
            "  <title>Chess Book</title>",
            "  <style>",
            "    body { font-family: Georgia, serif; line-height: 1.5; max-width: 760px; margin: 2rem auto; padding: 0 1rem; }",
            "    h1, h3 { margin-bottom: 0.35rem; }",
            "    .chunk { margin-top: 2rem; }",
            "    .moves { font-weight: 700; margin: 0; }",
            "    .comments { margin: 1rem 0; }",
            "    .diagram { margin: 1rem 0 0; }",
            "  </style>",
            "</head>",
            "<body>",
        ]
        event = self._display_header_value(getattr(headers, "event", ""))
        date = self._display_header_value(getattr(headers, "date", ""))
        white = self._display_header_value(getattr(headers, "white", ""))
        black = self._display_header_value(getattr(headers, "black", ""))

        title = event
        if event and date:
            title = f"{event} ({date})"
        elif date:
            title = date

        if title:
            lines.append(f"  <h1>{escape(title)}</h1>")
        if white or black:
            lines.append(f"  <h3>{escape(f'{white} vs. {black}'.strip())}</h3>")

        for chunk in chunks:
            lines.append('  <section class="chunk">')
            if chunk.label:
                lines.append(f"    <h3>{escape(chunk.label)}</h3>")
            lines.append(f"    <p class=\"moves\">{escape(chunk.move_text)}</p>")
            if chunk.comments.strip():
                lines.append(f"    <p class=\"comments\">{escape(chunk.comments)}</p>")
            if chunk.svg:
                lines.append(f'    <div class="diagram">{chunk.svg}</div>')
            lines.append("  </section>")

        lines.extend(["</body>", "</html>"])
        return "\n".join(lines) + "\n"

    def _display_header_value(self, value: str) -> str:
        """Hide PGN placeholder values such as ``?`` and ``????.??.??``."""

        normalized = value.strip()
        if normalized in {"", "?", "????.??.??"}:
            return ""
        return normalized
