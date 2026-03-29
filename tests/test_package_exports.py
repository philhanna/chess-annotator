from chessplan import Block, GameAnnotations


def test_top_level_package_exports_domain_models() -> None:
    block = Block(kind="plan", label="Export check", start_move=1, end_move=1)
    annotations = GameAnnotations("tests/testdata/mygame.pgn", blocks=[block])

    assert annotations.blocks == [block]
