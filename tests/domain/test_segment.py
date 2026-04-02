"""Unit tests for domain model business-rule functions."""
import pytest

from chess_annotate.domain.model import (
    Annotation,
    Segment,
    find_segment_index,
    move_from_ply,
    ply_from_move,
    segment_end_ply,
    total_plies,
)

# A minimal but legal PGN for a short game (10 moves / 20 plies).
_RUY_LOPEZ_PGN = (
    "[Event \"Test\"]\n"
    "[White \"White\"]\n"
    "[Black \"Black\"]\n"
    "[Result \"*\"]\n"
    "\n"
    "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 "
    "6. Re1 b5 7. Bb3 d6 8. c3 O-O 9. h3 Nb8 10. d4 Nbd7 *\n"
)


# ---------------------------------------------------------------------------
# ply_from_move / move_from_ply
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("move_number,side,expected_ply", [
    (1, "white", 1),
    (1, "black", 2),
    (2, "white", 3),
    (2, "black", 4),
    (10, "white", 19),
    (10, "black", 20),
])
def test_ply_from_move(move_number, side, expected_ply):
    assert ply_from_move(move_number, side) == expected_ply


@pytest.mark.parametrize("ply,expected_move,expected_side", [
    (1, 1, "white"),
    (2, 1, "black"),
    (3, 2, "white"),
    (4, 2, "black"),
    (19, 10, "white"),
    (20, 10, "black"),
])
def test_move_from_ply(ply, expected_move, expected_side):
    move_number, side = move_from_ply(ply)
    assert move_number == expected_move
    assert side == expected_side


def test_ply_move_roundtrip():
    for move_number in range(1, 11):
        for side in ("white", "black"):
            ply = ply_from_move(move_number, side)
            back_move, back_side = move_from_ply(ply)
            assert back_move == move_number
            assert back_side == side


def test_ply_from_move_invalid_side():
    with pytest.raises(ValueError):
        ply_from_move(1, "both")


# ---------------------------------------------------------------------------
# total_plies
# ---------------------------------------------------------------------------

def test_total_plies():
    assert total_plies(_RUY_LOPEZ_PGN) == 20


# ---------------------------------------------------------------------------
# Helpers for building test Annotations
# ---------------------------------------------------------------------------

def _make_annotation(*start_plies: int) -> Annotation:
    """Build an Annotation with segments starting at the given plies."""
    segments = [Segment(start_ply=p) for p in start_plies]
    return Annotation(
        annotation_id="test-id",
        title="Test",
        author="Tester",
        date="2024-01-01",
        pgn=_RUY_LOPEZ_PGN,
        player_side="white",
        diagram_orientation="white",
        segments=segments,
    )


# ---------------------------------------------------------------------------
# segment_end_ply
# ---------------------------------------------------------------------------

def test_segment_end_ply_single_segment():
    ann = _make_annotation(1)
    assert segment_end_ply(ann, 0) == 20


def test_segment_end_ply_first_of_two():
    ann = _make_annotation(1, 11)
    assert segment_end_ply(ann, 0) == 10


def test_segment_end_ply_last_of_two():
    ann = _make_annotation(1, 11)
    assert segment_end_ply(ann, 1) == 20


def test_segment_end_ply_middle():
    ann = _make_annotation(1, 7, 15)
    assert segment_end_ply(ann, 0) == 6
    assert segment_end_ply(ann, 1) == 14
    assert segment_end_ply(ann, 2) == 20


# ---------------------------------------------------------------------------
# find_segment_index
# ---------------------------------------------------------------------------

def test_find_segment_index_single():
    ann = _make_annotation(1)
    for ply in range(1, 21):
        assert find_segment_index(ann, ply) == 0


def test_find_segment_index_two_segments():
    ann = _make_annotation(1, 11)
    for ply in range(1, 11):
        assert find_segment_index(ann, ply) == 0
    for ply in range(11, 21):
        assert find_segment_index(ann, ply) == 1


def test_find_segment_index_at_boundary():
    ann = _make_annotation(1, 11, 15)
    # ply 10 belongs to segment 0; ply 11 starts segment 1
    assert find_segment_index(ann, 10) == 0
    assert find_segment_index(ann, 11) == 1
    assert find_segment_index(ann, 14) == 1
    assert find_segment_index(ann, 15) == 2


def test_find_segment_index_out_of_range():
    ann = _make_annotation(1)
    with pytest.raises(ValueError):
        find_segment_index(ann, 0)
    with pytest.raises(ValueError):
        find_segment_index(ann, 21)
