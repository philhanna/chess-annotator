import json

import pytest

from annotate.adapters.pgn_file_game_repository import (
    PGNFileGameRepository,
    pgn_with_turning_points,
    strip_comments_and_nags,
    turning_points_from_pgn,
    validate_pgn_json_sync,
)
from annotate.domain.annotation import Annotation
from annotate.domain.segment import SegmentContent

_PGN = (
    "[Event \"Test\"]\n"
    "[White \"White\"]\n"
    "[Black \"Black\"]\n"
    "[Result \"*\"]\n"
    "\n"
    "1. e4 $1 {best by test} e5 2. Nf3 Nc6 3. Bb5 a6 "
    "4. Ba4 Nf6 5. O-O Be7 6. Re1 b5 *\n"
)


def make_annotation() -> Annotation:
    return Annotation(
        game_id="game-1",
        title="White - Black",
        author="Tester",
        date="2024-01-01",
        pgn=strip_comments_and_nags(_PGN),
        player_side="white",
        diagram_orientation="white",
        turning_points=[1, 5, 11],
        segment_contents={
            1: SegmentContent(label="Opening", annotation="Develop pieces"),
            5: SegmentContent(label="Pressure", annotation="Build on e5"),
            11: SegmentContent(label="Transition", show_diagram=False),
        },
    )


def test_strip_comments_and_nags_removes_annotations():
    cleaned = strip_comments_and_nags(_PGN)
    assert "{best by test}" not in cleaned
    assert "$1" not in cleaned


def test_save_and_load_round_trip(tmp_path):
    repo = PGNFileGameRepository(tmp_path)
    annotation = make_annotation()

    repo.save(annotation)
    loaded = repo.load("game-1")

    assert loaded.game_id == "game-1"
    assert loaded.turning_points == [1, 5, 11]
    assert loaded.segment_contents[1].label == "Opening"
    assert loaded.segment_contents[5].annotation == "Build on e5"
    assert loaded.segment_contents[11].show_diagram is False
    assert repo.main_pgn_path("game-1").exists()
    assert repo.main_json_path("game-1").exists()


def test_save_writes_tp_markers_to_pgn(tmp_path):
    repo = PGNFileGameRepository(tmp_path)
    annotation = make_annotation()

    repo.save(annotation)

    pgn_text = repo.main_pgn_path("game-1").read_text()
    assert turning_points_from_pgn(pgn_text) == [1, 5, 11]


def test_list_all_reads_game_directories(tmp_path):
    repo = PGNFileGameRepository(tmp_path)
    repo.save(make_annotation())
    second = make_annotation()
    second.game_id = "game-2"
    second.annotation_id = "game-2"
    second.title = "Second Game"
    repo.save(second)

    assert repo.list_all() == [
        ("game-1", "White - Black"),
        ("game-2", "Second Game"),
    ]


def test_working_copy_round_trip_and_commit_keeps_work_files(tmp_path):
    repo = PGNFileGameRepository(tmp_path)
    annotation = make_annotation()
    repo.save(annotation)

    annotation.segment_contents[5].annotation = "Updated plan"
    repo.save_working_copy(annotation)
    assert repo.exists_working_copy("game-1") is True
    assert repo.has_unsaved_working_copy("game-1") is True

    loaded_work = repo.load_working_copy("game-1")
    assert loaded_work.segment_contents[5].annotation == "Updated plan"

    repo.commit_working_copy("game-1")
    assert repo.load("game-1").segment_contents[5].annotation == "Updated plan"
    assert repo.exists_working_copy("game-1") is True
    assert repo.has_unsaved_working_copy("game-1") is False


def test_discard_working_copy_removes_both_work_files(tmp_path):
    repo = PGNFileGameRepository(tmp_path)
    repo.save_working_copy(make_annotation())

    repo.discard_working_copy("game-1")

    assert not repo.work_pgn_path("game-1").exists()
    assert not repo.work_json_path("game-1").exists()


def test_stale_working_copies_lists_game_ids(tmp_path):
    repo = PGNFileGameRepository(tmp_path)
    repo.save_working_copy(make_annotation())
    other = make_annotation()
    other.game_id = "game-2"
    other.annotation_id = "game-2"
    repo.save_working_copy(other)

    assert repo.stale_working_copies() == ["game-1", "game-2"]


def test_validate_pgn_json_sync_rejects_mismatch():
    annotation = make_annotation()
    pgn_text = pgn_with_turning_points(annotation)
    json_data = {
        "game": {"title": annotation.title},
        "segments": {
            "1": {"label": "Opening", "annotation": "", "show_diagram": True},
            "7": {"label": "Mismatch", "annotation": "", "show_diagram": True},
        },
    }

    with pytest.raises(ValueError):
        validate_pgn_json_sync(pgn_text, json_data)


def test_load_rejects_mismatched_pgn_and_json(tmp_path):
    repo = PGNFileGameRepository(tmp_path)
    game_dir = repo.game_dir("broken")
    game_dir.mkdir(parents=True, exist_ok=True)
    repo.main_pgn_path("broken").write_text(pgn_with_turning_points(make_annotation()))
    repo.main_json_path("broken").write_text(
        json.dumps(
            {
                "game": {"title": "Broken"},
                "segments": {
                    "1": {"label": "Only", "annotation": "", "show_diagram": True},
                    "5": {"label": "Extra", "annotation": "", "show_diagram": True},
                },
            }
        )
    )

    with pytest.raises(ValueError):
        repo.load("broken")


def test_load_reports_corrupted_json_file(tmp_path):
    repo = PGNFileGameRepository(tmp_path)
    game_dir = repo.game_dir("broken-json")
    game_dir.mkdir(parents=True, exist_ok=True)
    repo.main_pgn_path("broken-json").write_text(pgn_with_turning_points(make_annotation()))
    repo.main_json_path("broken-json").write_text("{ not valid json")

    with pytest.raises(ValueError, match="Could not parse JSON file"):
        repo.load("broken-json")


def test_load_working_copy_reports_corrupted_storage_message(tmp_path):
    repo = PGNFileGameRepository(tmp_path)
    annotation = make_annotation()
    repo.save_working_copy(annotation)
    repo.work_json_path("game-1").write_text(
        json.dumps(
            {
                "game": {"title": annotation.title},
                "segments": {
                    "1": {"label": "Opening", "annotation": "", "show_diagram": True},
                    "9": {"label": "Mismatch", "annotation": "", "show_diagram": True},
                },
            }
        )
    )

    with pytest.raises(ValueError, match="Corrupted stored game 'game-1'"):
        repo.load_working_copy("game-1")
