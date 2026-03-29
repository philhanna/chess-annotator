import json
from pathlib import Path

import pytest

from chessplan.adapters.json_annotations import JsonAnnotationStore
from chessplan.domain import Block, GameAnnotations, GameHeaders, GameRecord, MovePair


def make_game() -> GameRecord:
    return GameRecord(
        headers=GameHeaders(
            event="Live Chess",
            white="Alice",
            black="Bob",
            result="1-0",
        ),
        move_pairs=[MovePair(1, "e4", "e5")],
    )


def test_load_annotations_returns_default_metadata_when_file_missing(tmp_path: Path) -> None:
    store = JsonAnnotationStore()
    pgn_path = tmp_path / "game.pgn"
    annotation_path = tmp_path / "game.pgn.plans.json"

    annotations = store.load_annotations(annotation_path, pgn_path, make_game())

    assert annotations == GameAnnotations(
        pgn_path=str(pgn_path),
        event="Live Chess",
        white="Alice",
        black="Bob",
        result="1-0",
    )


def test_load_annotations_rejects_non_mapping_json(tmp_path: Path) -> None:
    store = JsonAnnotationStore()
    annotation_path = tmp_path / "bad.json"
    annotation_path.write_text('["not", "a", "mapping"]', encoding="utf-8")

    with pytest.raises(SystemExit, match="Invalid annotation file format"):
        store.load_annotations(annotation_path, tmp_path / "game.pgn", make_game())


def test_save_annotations_writes_expected_json(tmp_path: Path) -> None:
    store = JsonAnnotationStore()
    annotation_path = tmp_path / "saved.json"
    annotations = GameAnnotations(
        pgn_path="tests/testdata/mygame.pgn",
        summary="Convert development into attack.",
        blocks=[Block(kind="plan", label="Development", start_move=1, end_move=8)],
    )

    store.save_annotations(annotation_path, annotations)

    saved = json.loads(annotation_path.read_text(encoding="utf-8"))
    assert saved["summary"] == "Convert development into attack."
    assert saved["blocks"][0]["label"] == "Development"
