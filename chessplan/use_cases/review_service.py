from __future__ import annotations

from pathlib import Path

from chessplan.domain import Block, GameAnnotations, GameRecord
from chessplan.ports import AnnotationStore, GameLoader


class ReviewService:
    """Coordinates game loading and annotation workflows for the CLI."""

    def __init__(self, game_loader: GameLoader, annotation_store: AnnotationStore) -> None:
        """Create a review service backed by the supplied ports."""

        self._game_loader = game_loader
        self._annotation_store = annotation_store

    def load_game(self, pgn_path: Path) -> GameRecord:
        """Load and normalize a single game from the given PGN path."""

        return self._game_loader.load_game(pgn_path)

    def default_annotation_path(self, pgn_path: Path) -> Path:
        """Return the default sidecar JSON path for a PGN file."""

        return pgn_path.with_suffix(pgn_path.suffix + ".plans.json")

    def load_annotations(self, annotation_path: Path, pgn_path: Path, game: GameRecord) -> GameAnnotations:
        """Load existing annotations or create an empty review scaffold."""

        return self._annotation_store.load_annotations(annotation_path, pgn_path, game)

    def save_annotations(self, annotation_path: Path, annotations: GameAnnotations) -> None:
        """Persist annotations to the configured storage adapter."""

        self._annotation_store.save_annotations(annotation_path, annotations)

    def add_block(
        self,
        annotations: GameAnnotations,
        game: GameRecord,
        *,
        kind: str,
        label: str,
        move_range: tuple[int, int],
        side: str,
        idea: str,
        trigger: str,
        end_condition: str,
        result: str,
        opponent_plan: str,
        better_plan: str,
        notes: str,
    ) -> Block:
        """Create, validate, and attach a review block to the annotations.

        Raises
        ------
        SystemExit
            If the proposed block fails domain validation.
        """

        start_move, end_move = move_range
        block = Block(
            kind=kind,
            label=label,
            start_move=start_move,
            end_move=end_move,
            side=side,
            idea=idea,
            trigger=trigger,
            end_condition=end_condition,
            result=result,
            opponent_plan=opponent_plan,
            better_plan=better_plan,
            notes=notes,
        )
        errors = block.validate(game.max_fullmove_number)
        if errors:
            raise SystemExit("Invalid block:" + "".join(errors))
        annotations.blocks.append(block)
        return block

    def set_summary(self, annotations: GameAnnotations, summary: str) -> None:
        """Replace the stored one-line summary for the reviewed game."""

        annotations.summary = summary
