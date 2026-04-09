import io

import chess.pgn

from annotate.domain.annotation import Annotation
from annotate.domain.segment import SegmentContent, SegmentView


def total_plies(pgn: str) -> int:
    game = chess.pgn.read_game(io.StringIO(pgn))
    if game is None:
        raise ValueError("Could not parse PGN")
    return sum(1 for _ in game.mainline_moves())


def game_headers(pgn: str) -> dict[str, str]:
    game = chess.pgn.read_game(io.StringIO(pgn))
    if game is None:
        raise ValueError("Could not parse PGN")
    return {str(key): str(value) for key, value in game.headers.items()}


def ply_from_move(move_number: int, side: str) -> int:
    if side not in ("white", "black"):
        raise ValueError(f"side must be 'white' or 'black', got {side!r}")
    side_offset = 1 if side == "white" else 2
    return (move_number - 1) * 2 + side_offset


def move_from_ply(ply: int) -> tuple[int, str]:
    if ply < 1:
        raise ValueError("ply must be >= 1")
    move_number = (ply + 1) // 2
    side = "white" if ply % 2 == 1 else "black"
    return move_number, side


def derive_segments(annotation: Annotation) -> list[SegmentView]:
    last_ply = total_plies(annotation.pgn)
    turning_points = annotation.turning_points
    segments: list[SegmentView] = []

    for index, start_ply in enumerate(turning_points):
        if start_ply > last_ply:
            raise ValueError(
                f"Turning point {start_ply} is beyond the game's last ply {last_ply}"
            )
        if index < len(turning_points) - 1:
            end_ply = turning_points[index + 1] - 1
        else:
            end_ply = last_ply
        content = annotation.segment_contents.get(start_ply, SegmentContent())
        segments.append(
            SegmentView(
                turning_point_ply=start_ply,
                start_ply=start_ply,
                end_ply=end_ply,
                content=content,
            )
        )
    return segments


def segment_end_ply(annotation: Annotation, index: int) -> int:
    return derive_segments(annotation)[index].end_ply


def find_segment_index(annotation: Annotation, ply: int) -> int:
    n = total_plies(annotation.pgn)
    if not (1 <= ply <= n):
        raise ValueError(f"Ply {ply} is out of range [1, {n}]")
    result = 0
    for i, start_ply in enumerate(annotation.turning_points):
        if start_ply <= ply:
            result = i
        else:
            break
    return result


def find_segment_by_turning_point(
    annotation: Annotation, turning_point_ply: int
) -> SegmentView:
    if turning_point_ply not in annotation.segment_contents:
        raise ValueError(f"No segment starts at ply {turning_point_ply}")
    index = annotation.turning_points.index(turning_point_ply)
    return derive_segments(annotation)[index]


def move_range_for_turning_point(
    annotation: Annotation, turning_point_ply: int
) -> tuple[int, int]:
    segment = find_segment_by_turning_point(annotation, turning_point_ply)
    return segment.start_ply, segment.end_ply


def san_move_range(pgn: str, start_ply: int, end_ply: int) -> str:
    game = chess.pgn.read_game(io.StringIO(pgn))
    if game is None:
        raise ValueError("Could not parse PGN")

    board = game.board()
    first_san: str | None = None
    last_san: str | None = None

    for i, move in enumerate(game.mainline_moves()):
        ply = i + 1
        if ply < start_ply:
            board.push(move)
            continue
        if ply > end_ply:
            break

        move_number = (ply - 1) // 2 + 1
        is_white = ply % 2 == 1
        san = board.san(move)
        formatted = f"{move_number}. {san}" if is_white else f"{move_number}...{san}"

        if first_san is None:
            first_san = formatted
        last_san = formatted
        board.push(move)

    if first_san is None:
        return ""
    if first_san == last_san:
        return first_san
    return f"{first_san} to {last_san}"


def format_move_list(pgn: str, start_ply: int, end_ply: int) -> str:
    game = chess.pgn.read_game(io.StringIO(pgn))
    if game is None:
        raise ValueError("Could not parse PGN")

    board = game.board()
    parts: list[str] = []
    first_in_segment = True

    for i, move in enumerate(game.mainline_moves()):
        ply = i + 1
        if ply < start_ply:
            board.push(move)
            continue
        if ply > end_ply:
            break

        move_number = (ply - 1) // 2 + 1
        is_white = ply % 2 == 1
        san = board.san(move)

        if is_white:
            parts.append(f"{move_number}. {san}")
        elif first_in_segment:
            parts.append(f"{move_number}...{san}")
        else:
            parts.append(san)

        first_in_segment = False
        board.push(move)

    return " ".join(parts)
