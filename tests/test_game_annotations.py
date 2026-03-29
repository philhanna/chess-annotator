from chessplan.domain import Block, GameAnnotations


def test_to_json_dict_serializes_blocks() -> None:
    annotations = GameAnnotations(
        pgn_path="tests/testdata/mygame.pgn",
        event="Club game",
        white="White",
        black="Black",
        result="1-0",
        summary="Strong kingside attack.",
        big_lessons=["Attack sooner"],
        blocks=[
            Block(
                kind="plan",
                label="Attack",
                start_move=10,
                end_move=15,
                side="white",
                notes="Knight lift worked well.",
            )
        ],
    )

    assert annotations.to_json_dict() == {
        "pgn_path": "tests/testdata/mygame.pgn",
        "event": "Club game",
        "white": "White",
        "black": "Black",
        "result": "1-0",
        "summary": "Strong kingside attack.",
        "big_lessons": ["Attack sooner"],
        "blocks": [
            {
                "kind": "plan",
                "label": "Attack",
                "start_move": 10,
                "end_move": 15,
                "side": "white",
                "idea": "",
                "trigger": "",
                "end_condition": "",
                "result": "",
                "opponent_plan": "",
                "better_plan": "",
                "notes": "Knight lift worked well.",
            }
        ],
    }


def test_from_json_dict_uses_defaults_for_missing_optional_fields() -> None:
    annotations = GameAnnotations.from_json_dict(
        {
            "pgn_path": "tests/testdata/mygame.pgn",
            "blocks": [
                {
                    "kind": "transition",
                    "label": "Center breaks",
                    "start_move": 18,
                    "end_move": 21,
                }
            ],
        }
    )

    assert annotations.pgn_path == "tests/testdata/mygame.pgn"
    assert annotations.summary == ""
    assert annotations.big_lessons == []
    assert len(annotations.blocks) == 1
    assert annotations.blocks[0].side == "white"
    assert annotations.blocks[0].label == "Center breaks"
