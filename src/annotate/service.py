"""Application service state for the annotate web app."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import chess

from annotate.adapters.pgn_repository import (
    NAG_DIAGRAM,
    ParsedGame,
    parse_game,
    parse_pgn_collection,
    serialize_pgn_collection,
    selected_node,
    suggested_output_name,
)
from annotate.adapters.svg_board_renderer import SvgBoardRenderer


@dataclass
class SessionState:
    """Serializable high-level session state for the SPA."""

    app_name: str
    frontend_root: str
    source_name: str | None
    selected_game_index: int | None
    selected_ply: int | None
    last_saved_name: str | None
    unsaved_changes: bool
    status: str


@dataclass
class EditorState:
    """Selected-ply annotation view state."""

    comment: str
    diagram: bool


class AnnotateSession:
    """Session state and view-model builder for the annotate UI."""

    def __init__(self, frontend_root: Path, board_renderer: SvgBoardRenderer | None = None) -> None:
        self._frontend_root = frontend_root
        self._board_renderer = board_renderer or SvgBoardRenderer()
        self._source_name: str | None = None
        self._games: tuple[ParsedGame, ...] = ()
        self._selected_game_index: int | None = None
        self._selected_ply: int | None = None
        self._last_saved_name: str | None = None
        self._unsaved_changes = False

    @property
    def frontend_root(self) -> Path:
        """Return the configured frontend asset directory."""

        return self._frontend_root

    def snapshot(self) -> SessionState:
        """Return the current session state for JSON responses."""

        if self._games:
            status = "document-loaded"
        elif self._source_name is None:
            status = "idle"
        else:
            status = "document-empty"

        return SessionState(
            app_name="chess-annotate",
            frontend_root=str(self._frontend_root),
            source_name=self._source_name,
            selected_game_index=self._selected_game_index,
            selected_ply=self._selected_ply,
            last_saved_name=self._last_saved_name,
            unsaved_changes=self._unsaved_changes,
            status=status,
        )

    def open_pgn(self, display_name: str, pgn_text: str) -> dict[str, object]:
        """Load a browser-provided PGN into the current session."""

        games = parse_pgn_collection(pgn_text)
        self._source_name = display_name
        self._games = games
        self._last_saved_name = None
        self._unsaved_changes = False

        if games:
            self._selected_game_index = 0
            self._selected_ply = 0
        else:
            self._selected_game_index = None
            self._selected_ply = None

        return self.current_view()

    def select_game(self, index: int) -> dict[str, object]:
        """Select a game by index and return the updated view."""

        self._require_document_loaded()
        if index < 0 or index >= len(self._games):
            raise ValueError(f"game index out of range: {index}")

        game = self._games[index]
        self._selected_game_index = index
        self._selected_ply = 0
        return self.current_view()

    def select_ply(self, ply: int) -> dict[str, object]:
        """Select a ply in the current game and return the updated view."""

        game = self._selected_game()
        valid_plies = {move.ply for move in game.moves}
        if ply not in valid_plies:
            raise ValueError(f"ply not found in selected game: {ply}")

        self._selected_ply = ply
        return self.current_view()

    def navigate(self, action: str) -> dict[str, object]:
        """Navigate the selected ply and return the updated view."""

        game = self._selected_game()
        if not game.moves:
            return self.current_view()

        plies = [move.ply for move in game.moves]
        current_ply = self._selected_ply if self._selected_ply is not None else 0
        current_index = plies.index(current_ply)

        if action == "start":
            new_index = 0
        elif action == "prev":
            new_index = max(0, current_index - 1)
        elif action == "next":
            new_index = min(len(plies) - 1, current_index + 1)
        elif action == "end":
            new_index = len(plies) - 1
        else:
            raise ValueError(f"unknown navigation action: {action}")

        self._selected_ply = plies[new_index]
        return self.current_view()

    def apply_annotation(self, comment: str, diagram: bool) -> dict[str, object]:
        """Apply stored annotation state to the selected ply."""

        game = self._selected_game()
        if self._selected_ply is None:
            raise ValueError("no ply is currently selected")

        node = selected_node(game.game, self._selected_ply)
        if node is None:
            raise ValueError(f"ply not found in selected game: {self._selected_ply}")

        node.comment = comment.strip()
        if self._selected_ply == 0:
            diagram = False
        else:
            if diagram:
                node.nags.add(NAG_DIAGRAM)
            else:
                node.nags.discard(NAG_DIAGRAM)

        self._replace_selected_game(parse_game(game.game, index=game.summary.index, flipped=game.flipped))
        self._unsaved_changes = True
        return self.current_view()

    def set_board_flipped(self, flipped: bool) -> dict[str, object]:
        """Set the selected game's board orientation preference."""

        game = self._selected_game()
        if game.flipped == flipped:
            return self.current_view()

        self._replace_selected_game(parse_game(game.game, index=game.summary.index, flipped=flipped))
        return self.current_view()

    def cancel_annotation(self) -> dict[str, object]:
        """Return the currently stored annotation state without mutation."""

        self._require_document_loaded()
        return self.current_view()

    def clear_comments(self) -> dict[str, object]:
        """Clear all comments in the currently selected game."""

        game = self._selected_game()
        game.game.comment = ""

        node = game.game
        while node.variations:
            node = node.variations[0]
            node.comment = ""

        self._replace_selected_game(parse_game(game.game, index=game.summary.index, flipped=game.flipped))
        self._unsaved_changes = True

        self._selected_ply = 0
        return self.current_view()

    def save_payload(self) -> dict[str, object]:
        """Return PGN content and metadata for browser-controlled save."""

        self._require_document_loaded()
        return {
            "pgn_text": serialize_pgn_collection(self._games),
            "suggested_filename": suggested_output_name(self._source_name),
            "unsaved_changes": self._unsaved_changes,
        }

    def confirm_save(self, output_name: str) -> dict[str, object]:
        """Mark the current in-memory document as saved by the browser."""

        self._require_document_loaded()
        self._last_saved_name = output_name
        self._unsaved_changes = False
        return self.current_view()

    def current_view(self) -> dict[str, object]:
        """Return the full current UI payload."""

        session = asdict(self.snapshot())
        game_summaries = [asdict(game.summary) for game in self._games]

        payload: dict[str, object] = {
            "session": session,
            "games": game_summaries,
            "selected_game": None,
            "selected_ply": self._selected_ply,
            "board_svg": self._board_svg(),
            "board_flipped": False,
            "flip_enabled": self._selected_game_index is not None,
            "move_rows": [],
            "editor": asdict(self._editor_state()),
            "editor_enabled": self._selected_game_index is not None,
            "diagram_enabled": self._selected_game_index is not None and self._selected_ply != 0,
        }

        if self._selected_game_index is not None:
            game = self._games[self._selected_game_index]
            payload["selected_game"] = asdict(game.summary)
            payload["board_flipped"] = game.flipped
            payload["move_rows"] = [
                {
                    **asdict(move),
                    "selected": move.ply == self._selected_ply,
                }
                for move in game.moves
            ]

        return payload

    def _editor_state(self) -> EditorState:
        move = self._selected_move()
        if move is None:
            return EditorState(comment="", diagram=False)
        return EditorState(comment=move.comment, diagram=move.diagram)

    def _board_svg(self) -> str:
        if self._selected_game_index is None:
            return self._board_renderer.render(chess.STARTING_FEN)

        game = self._games[self._selected_game_index]
        move = self._selected_move()
        fen = move.fen if move is not None else game.initial_fen
        lastmove = None
        if self._selected_ply not in {None, 0}:
            node = selected_node(game.game, self._selected_ply)
            if node is not None:
                lastmove = node.move
        return self._board_renderer.render(fen, lastmove=lastmove, flipped=game.flipped)

    def _selected_move(self):
        if self._selected_game_index is None or self._selected_ply is None:
            return None

        game = self._games[self._selected_game_index]
        for move in game.moves:
            if move.ply == self._selected_ply:
                return move
        return None

    def _selected_game(self) -> ParsedGame:
        self._require_document_loaded()
        assert self._selected_game_index is not None
        return self._games[self._selected_game_index]

    def _replace_selected_game(self, replacement: ParsedGame) -> None:
        assert self._selected_game_index is not None
        games = list(self._games)
        games[self._selected_game_index] = replacement
        self._games = tuple(games)

    def _require_document_loaded(self) -> None:
        if not self._games:
            raise ValueError("no PGN document is currently loaded")
