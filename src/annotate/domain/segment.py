from dataclasses import dataclass


@dataclass
class Segment:
    """Represent one authored segment of commentary within a game.

    A segment begins at ``start_ply`` and conceptually runs until the
    ply immediately before the next segment begins, or to the end of the
    game for the final segment. The segment stores only author-managed
    metadata: an optional label, free-form Markdown commentary, and a
    flag indicating whether a board diagram should be rendered for the
    segment's end position.
    """

    start_ply: int
    label: str | None = None
    commentary: str = ""
    show_diagram: bool = False
