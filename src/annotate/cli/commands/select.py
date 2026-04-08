# annotate.cli.commands.select
from annotate.cli import session


def cmd_select(tokens: list[str]) -> None:
    if not tokens:
        session.err("Usage: <segment-number>")
        return
    segments = session.current_segments()
    if segments is None:
        return
    try:
        index = int(tokens[0])
    except ValueError:
        session.err("Segment must be selected by its number.")
        return
    if not (1 <= index <= len(segments)):
        session.err(f"Segment number must be between 1 and {len(segments)}")
        return
    session.state.current_turning_point_ply = segments[index - 1].turning_point_ply
    session.print(f"Segment {index} selected.")
