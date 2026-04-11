import pytest

from annotate.domain.annotation import Annotation, GameId, TurningPoint
from annotate.domain.model import (
    derive_segments,
    find_segment_by_turning_point,
    find_segment_index,
    move_from_ply,
    move_range_for_turning_point,
    parse_diagram_tokens,
    ply_from_move,
    segment_end_ply,
    total_plies,
)
from annotate.domain.segment import SegmentContent
from annotate.use_cases.interactors import merge_segment, merge_segments_by_index, split_segment

_RUY_LOPEZ_PGN = (
    "[Event \"Test\"]\n"
    "[White \"White\"]\n"
    "[Black \"Black\"]\n"
    "[Result \"*\"]\n"
    "\n"
    "1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 "
    "6. Re1 b5 7. Bb3 d6 8. c3 O-O 9. h3 Nb8 10. d4 Nbd7 *\n"
)


@pytest.mark.parametrize(
    "move_number,side,expected_ply",
    [
        (1, "white", 1),
        (1, "black", 2),
        (2, "white", 3),
        (2, "black", 4),
        (10, "white", 19),
        (10, "black", 20),
    ],
)
def test_ply_from_move(move_number, side, expected_ply):
    assert ply_from_move(move_number, side) == expected_ply


@pytest.mark.parametrize(
    "ply,expected_move,expected_side",
    [
        (1, 1, "white"),
        (2, 1, "black"),
        (3, 2, "white"),
        (4, 2, "black"),
        (19, 10, "white"),
        (20, 10, "black"),
    ],
)
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


def test_total_plies():
    assert total_plies(_RUY_LOPEZ_PGN) == 20


def test_game_id_must_not_be_empty():
    with pytest.raises(ValueError):
        GameId("   ")


def test_turning_point_must_be_positive():
    with pytest.raises(ValueError):
        TurningPoint(0)


def make_annotation(*turning_points: int) -> Annotation:
    contents = {
        ply: SegmentContent()
        for ply in turning_points
    }
    return Annotation(
        game_id="test-game",
        title="Test",
        author="Tester",
        date="2024-01-01",
        pgn=_RUY_LOPEZ_PGN,
        player_side="white",
        turning_points=list(turning_points),
        segment_contents=contents,
    )


def test_annotation_defaults_to_first_turning_point():
    ann = Annotation.create(
        game_id="game-1",
        title="Test Game",
        author="Tester",
        date="2024-01-01",
        pgn=_RUY_LOPEZ_PGN,
        player_side="white",
    )
    assert ann.turning_points == [1]
    assert set(ann.segment_contents) == {1}


def test_annotation_rejects_non_matching_content_keys():
    with pytest.raises(ValueError):
        Annotation(
            game_id="test-game",
            title="Test",
            author="Tester",
            date="2024-01-01",
            pgn=_RUY_LOPEZ_PGN,
            player_side="white",
            turning_points=[1, 11],
            segment_contents={1: SegmentContent(label="Opening")},
        )


def test_derive_segments_single_segment():
    ann = make_annotation(1)
    segments = derive_segments(ann)
    assert len(segments) == 1
    assert segments[0].start_ply == 1
    assert segments[0].end_ply == 20


def test_derive_segments_multiple_segments():
    ann = make_annotation(1, 7, 15)
    segments = derive_segments(ann)
    assert [(seg.start_ply, seg.end_ply) for seg in segments] == [
        (1, 6),
        (7, 14),
        (15, 20),
    ]


def test_segment_end_ply():
    ann = make_annotation(1, 11, 15)
    assert segment_end_ply(ann, 0) == 10
    assert segment_end_ply(ann, 1) == 14
    assert segment_end_ply(ann, 2) == 20


def test_find_segment_index():
    ann = make_annotation(1, 11, 15)
    assert find_segment_index(ann, 10) == 0
    assert find_segment_index(ann, 11) == 1
    assert find_segment_index(ann, 14) == 1
    assert find_segment_index(ann, 15) == 2


def test_find_segment_index_out_of_range():
    ann = make_annotation(1)
    with pytest.raises(ValueError):
        find_segment_index(ann, 0)
    with pytest.raises(ValueError):
        find_segment_index(ann, 21)


def test_find_segment_by_turning_point():
    ann = make_annotation(1, 11)
    segment = find_segment_by_turning_point(ann, 11)
    assert segment.start_ply == 11
    assert segment.end_ply == 20


def test_move_range_for_turning_point():
    ann = make_annotation(1, 11)
    assert move_range_for_turning_point(ann, 1) == (1, 10)
    assert move_range_for_turning_point(ann, 11) == (11, 20)


def test_split_segment_produces_two_turning_points():
    ann = make_annotation(1)
    result = split_segment(ann, 11, "Middlegame")
    assert result.turning_points == [1, 11]
    assert result.segment_contents[11].label == "Middlegame"
    assert result.segment_contents[11].annotation == ""


def test_split_segment_preserves_earlier_content():
    ann = make_annotation(1)
    ann.segment_contents[1].label = "Opening"
    ann.segment_contents[1].annotation = "Some notes"

    result = split_segment(ann, 11, "Middlegame")
    earlier = result.segment_contents[1]
    assert earlier.label == "Opening"
    assert earlier.annotation == "Some notes"


def test_split_segment_at_ply_1_fails():
    ann = make_annotation(1)
    with pytest.raises(ValueError):
        split_segment(ann, 1, "Impossible")


def test_split_segment_out_of_range_fails():
    ann = make_annotation(1)
    with pytest.raises(ValueError):
        split_segment(ann, 21, "Too far")
    with pytest.raises(ValueError):
        split_segment(ann, 0, "Too early")


def test_split_segment_at_existing_boundary_fails():
    ann = make_annotation(1, 11)
    with pytest.raises(ValueError):
        split_segment(ann, 11, "Duplicate")


def test_merge_segment_basic():
    ann = make_annotation(1, 11)
    result, merged = merge_segment(ann, 11)
    assert merged is True
    assert result.turning_points == [1]


def test_merge_segment_returns_false_when_later_has_content():
    ann = make_annotation(1, 11)
    ann.segment_contents[11].label = "Middlegame"
    result, merged = merge_segment(ann, 11)
    assert merged is False
    assert result.turning_points == [1, 11]


def test_merge_segment_force_discards_later_content():
    ann = make_annotation(1, 11)
    ann.segment_contents[11].annotation = "Critical transition"
    result, merged = merge_segment(ann, 11, force=True)
    assert merged is True
    assert result.turning_points == [1]
    assert 11 not in result.segment_contents


# --- merge_segments_by_index ---

def test_merge_segments_by_index_adjacent_concatenates_labels():
    ann = make_annotation(1, 7, 15)
    ann.segment_contents[1].label = "Opening"
    ann.segment_contents[7].label = "Middlegame"
    result = merge_segments_by_index(ann, 1, 2)
    assert result.turning_points == [1, 15]
    assert result.segment_contents[1].label == "Opening Middlegame"


def test_merge_segments_by_index_adjacent_concatenates_annotations():
    ann = make_annotation(1, 7, 15)
    ann.segment_contents[1].annotation = "First note"
    ann.segment_contents[7].annotation = "Second note"
    result = merge_segments_by_index(ann, 1, 2)
    assert result.segment_contents[1].annotation == "First note\n\nSecond note"


def test_merge_segments_by_index_spans_three_segments():
    ann = make_annotation(1, 7, 11, 15)
    ann.segment_contents[1].label = "A"
    ann.segment_contents[7].label = "B"
    ann.segment_contents[11].label = "C"
    result = merge_segments_by_index(ann, 1, 3)
    assert result.turning_points == [1, 15]
    assert result.segment_contents[1].label == "A B C"


def test_merge_segments_by_index_omits_empty_labels():
    ann = make_annotation(1, 7, 15)
    ann.segment_contents[1].label = "Opening"
    ann.segment_contents[7].label = ""
    result = merge_segments_by_index(ann, 1, 2)
    assert result.segment_contents[1].label == "Opening"


def test_merge_segments_by_index_omits_empty_annotations():
    ann = make_annotation(1, 7, 15)
    ann.segment_contents[1].annotation = "First note"
    ann.segment_contents[7].annotation = ""
    result = merge_segments_by_index(ann, 1, 2)
    assert result.segment_contents[1].annotation == "First note"


def test_merge_segments_by_index_strips_whitespace():
    ann = make_annotation(1, 7, 15)
    ann.segment_contents[1].label = "  Opening  "
    ann.segment_contents[7].label = "  Middlegame  "
    ann.segment_contents[1].annotation = "  First note  "
    ann.segment_contents[7].annotation = "  Second note  "
    result = merge_segments_by_index(ann, 1, 2)
    assert result.segment_contents[1].label == "Opening Middlegame"
    assert result.segment_contents[1].annotation == "First note\n\nSecond note"


def test_merge_segments_by_index_invalid_m_equals_n():
    ann = make_annotation(1, 7, 15)
    with pytest.raises(ValueError):
        merge_segments_by_index(ann, 2, 2)


def test_merge_segments_by_index_invalid_m_greater_than_n():
    ann = make_annotation(1, 7, 15)
    with pytest.raises(ValueError):
        merge_segments_by_index(ann, 3, 2)


def test_merge_segments_by_index_n_out_of_range():
    ann = make_annotation(1, 7, 15)
    with pytest.raises(ValueError):
        merge_segments_by_index(ann, 2, 4)


def test_merge_segments_by_index_m_zero():
    ann = make_annotation(1, 7, 15)
    with pytest.raises(ValueError):
        merge_segments_by_index(ann, 0, 2)


# --- parse_diagram_tokens ---

def test_parse_diagram_tokens_empty_text():
    assert parse_diagram_tokens("") == []


def test_parse_diagram_tokens_no_tokens():
    assert parse_diagram_tokens("Develop pieces and control the center.") == []


def test_parse_diagram_tokens_single_white_move_default_orientation():
    tokens = parse_diagram_tokens("See the position. [[diagram 14w]]")
    assert len(tokens) == 1
    assert tokens[0].ply == 27   # move 14 white = ply 27
    assert tokens[0].orientation == "white"
    assert tokens[0].raw == "[[diagram 14w]]"


def test_parse_diagram_tokens_single_black_move_explicit_orientation():
    tokens = parse_diagram_tokens("[[diagram 5b black]]")
    assert len(tokens) == 1
    assert tokens[0].ply == 10   # move 5 black = ply 10
    assert tokens[0].orientation == "black"


def test_parse_diagram_tokens_explicit_white_orientation():
    tokens = parse_diagram_tokens("[[diagram 3w white]]")
    assert len(tokens) == 1
    assert tokens[0].orientation == "white"


def test_parse_diagram_tokens_multiple_tokens():
    text = "Before the fork: [[diagram 7w]]\n\nAfter the response: [[diagram 7b black]]"
    tokens = parse_diagram_tokens(text)
    assert len(tokens) == 2
    assert tokens[0].ply == 13   # move 7 white = ply 13
    assert tokens[0].orientation == "white"
    assert tokens[1].ply == 14   # move 7 black = ply 14
    assert tokens[1].orientation == "black"


def test_parse_diagram_tokens_duplicate_tokens():
    text = "[[diagram 1w]] and again [[diagram 1w]]"
    tokens = parse_diagram_tokens(text)
    assert len(tokens) == 2
    assert tokens[0].ply == tokens[1].ply == 1
