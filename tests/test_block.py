from chessplan.domain import Block


def test_validate_accepts_well_formed_block() -> None:
    block = Block(
        kind="plan",
        label="Queenside pressure",
        start_move=5,
        end_move=12,
        side="white",
    )

    assert block.validate(max_move=20) == []


def test_validate_reports_all_relevant_errors() -> None:
    block = Block(
        kind="",
        label="",
        start_move=0,
        end_move=-1,
        side="green",
    )

    assert block.validate(max_move=10) == [
        "kind must not be empty",
        "label must not be empty",
        "side must be one of: white, black, both, none",
        "start_move must be >= 1",
        "end_move must be >= start_move",
    ]


def test_validate_rejects_end_move_past_game_length() -> None:
    block = Block(
        kind="plan",
        label="Too long",
        start_move=8,
        end_move=14,
    )

    assert block.validate(max_move=12) == ["end_move must be <= 12"]
