from dataclasses import dataclass, field

from annotate.domain.segment import Segment


@dataclass
class Annotation:
    """Aggregate all authoring data for one annotated chess game.

    An annotation owns the source PGN together with the metadata needed
    to present and render that game from the author's perspective. It
    also owns the ordered list of :class:`Segment` objects that divide
    the game into named stretches of play for commentary and diagram
    placement.

    The ``create`` classmethod is the preferred constructor for new
    annotations. The caller supplies the ``annotation_id``, which in
    the CLI is system-assigned by the repository as one greater than the
    highest id currently in the store. The method also chooses a default
    diagram orientation when one is not supplied and seeds the annotation
    with a single initial segment that starts at ply 1.
    """

    annotation_id: int
    title: str
    author: str
    date: str                   # ISO 8601
    pgn: str
    player_side: str            # "white" | "black"
    diagram_orientation: str    # "white" | "black"
    segments: list[Segment] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        annotation_id: int,
        title: str,
        author: str,
        date: str,
        pgn: str,
        player_side: str,
        diagram_orientation: str | None = None,
    ) -> "Annotation":
        """Build a new annotation with an initial segment.

        ``annotation_id`` is supplied by the caller; in the CLI it comes
        from ``AnnotationRepository.next_id()``, which returns one greater
        than the highest id currently in the store.
        """
        if diagram_orientation is None:
            diagram_orientation = "black" if player_side == "black" else "white"
        initial_segment = Segment(start_ply=1)
        return cls(
            annotation_id=annotation_id,
            title=title,
            author=author,
            date=date,
            pgn=pgn,
            player_side=player_side,
            diagram_orientation=diagram_orientation,
            segments=[initial_segment],
        )
