from pathlib import Path

import pytest

from chessplan.domain import GameAnnotations, GameHeaders, GameRecord, MovePair
from chessplan.use_cases.review_service import ReviewService


class StubGameLoader:
    def __init__(self, game: GameRecord) -> None:
        self.game = game
        self.calls: list[Path] = []

    def load_game(self, pgn_path: Path) -> GameRecord:
        self.calls.append(pgn_path)
        return self.game


class StubAnnotationStore:
    def __init__(self, annotations: GameAnnotations) -> None:
        self.annotations = annotations
        self.load_calls: list[tuple[Path, Path, GameRecord]] = []
        self.save_calls: list[tuple[Path, GameAnnotations]] = []

    def load_annotations(self, annotation_path: Path, pgn_path: Path, game: GameRecord) -> GameAnnotations:
        self.load_calls.append((annotation_path, pgn_path, game))
        return self.annotations

    def save_annotations(self, annotation_path: Path, annotations: GameAnnotations) -> None:
        self.save_calls.append((annotation_path, annotations))


def make_game() -> GameRecord:
    return GameRecord(
        headers=GameHeaders(event="Training"),
        move_pairs=[MovePair(1, "e4", "e5"), MovePair(2, "Nf3", "Nc6")],
    )


def test_default_annotation_path_appends_sidecar_suffix() -> None:
    service = ReviewService(StubGameLoader(make_game()), StubAnnotationStore(GameAnnotations("game.pgn")))

    assert service.default_annotation_path(Path("games/mygame.pgn")) == Path("games/mygame.pgn.plans.json")


def test_load_game_and_annotations_delegate_to_ports() -> None:
    game = make_game()
    annotations = GameAnnotations("game.pgn")
    loader = StubGameLoader(game)
    store = StubAnnotationStore(annotations)
    service = ReviewService(loader, store)
    pgn_path = Path("tests/testdata/mygame.pgn")
    annotation_path = Path("tests/testdata/mygame.pgn.plans.json")

    assert service.load_game(pgn_path) is game
    assert service.load_annotations(annotation_path, pgn_path, game) is annotations
    assert loader.calls == [pgn_path]
    assert store.load_calls == [(annotation_path, pgn_path, game)]


def test_add_block_appends_valid_block() -> None:
    game = make_game()
    annotations = GameAnnotations("game.pgn")
    service = ReviewService(StubGameLoader(game), StubAnnotationStore(annotations))

    block = service.add_block(
        annotations,
        game,
        kind="plan",
        label="Develop pieces",
        move_range=(1, 2),
        side="white",
        idea="Rapid development",
        trigger="Opening phase",
        end_condition="All minors developed",
        result="Equalized comfortably",
        opponent_plan="Contest the center",
        better_plan="Castle sooner",
        notes="Useful baseline plan",
    )

    assert annotations.blocks == [block]
    assert block.idea == "Rapid development"


def test_add_block_raises_for_invalid_block() -> None:
    game = make_game()
    annotations = GameAnnotations("game.pgn")
    service = ReviewService(StubGameLoader(game), StubAnnotationStore(annotations))

    with pytest.raises(SystemExit, match="Invalid block:"):
        service.add_block(
            annotations,
            game,
            kind="",
            label="",
            move_range=(0, 3),
            side="white",
            idea="",
            trigger="",
            end_condition="",
            result="",
            opponent_plan="",
            better_plan="",
            notes="",
        )

    assert annotations.blocks == []


def test_set_summary_replaces_summary() -> None:
    annotations = GameAnnotations("game.pgn", summary="Old")
    service = ReviewService(StubGameLoader(make_game()), StubAnnotationStore(annotations))

    service.set_summary(annotations, "New summary")

    assert annotations.summary == "New summary"
