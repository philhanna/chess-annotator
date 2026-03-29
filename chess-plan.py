#!/usr/bin/env python3
"""Simple CLI for plan-oriented chess game review.

Overview:
- Always expects exactly one game in the PGN file
- Shows numbered moves in order
- Add labeled move-range annotations such as "Plan 1" or "Gap"
- Save annotations to JSON
- Print a review summary grouped by blocks

Dependency:
    pip install python-chess

Examples:
    python chessplan.py show game.pgn
    python chessplan.py annotate game.pgn
    python chessplan.py summary game.pgn

Annotation file default:
    <pgn-path>.plans.json
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import chess.pgn
from chessplan.block import Block


@dataclass(slots=True)
class GameAnnotations:
    pgn_path: str
    event: str = ""
    white: str = ""
    black: str = ""
    result: str = ""
    summary: str = ""
    big_lessons: list[str] = field(default_factory=list)
    blocks: list[Block] = field(default_factory=list)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "pgn_path": self.pgn_path,
            "event": self.event,
            "white": self.white,
            "black": self.black,
            "result": self.result,
            "summary": self.summary,
            "big_lessons": self.big_lessons,
            "blocks": [asdict(block) for block in self.blocks],
        }

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> "GameAnnotations":
        blocks = [Block(**item) for item in data.get("blocks", [])]
        return cls(
            pgn_path=data["pgn_path"],
            event=data.get("event", ""),
            white=data.get("white", ""),
            black=data.get("black", ""),
            result=data.get("result", ""),
            summary=data.get("summary", ""),
            big_lessons=list(data.get("big_lessons", [])),
            blocks=blocks,
        )


def eprint(*args: object) -> None:
    print(*args, file=sys.stderr)


def load_game(pgn_path: Path) -> chess.pgn.Game:
    with pgn_path.open("r", encoding="utf-8") as fh:
        first_game = chess.pgn.read_game(fh)
        if first_game is None:
            raise SystemExit(f"No game found in {pgn_path}")
        second_game = chess.pgn.read_game(fh)
        if second_game is not None:
            raise SystemExit(
                f"Expected exactly one game in {pgn_path}, but found more than one. "
                "Split the PGN first or use a file containing just one game."
            )
        return first_game


def game_headers(game: chess.pgn.Game) -> dict[str, str]:
    keys = ["Event", "Site", "Date", "White", "Black", "Result", "WhiteElo", "BlackElo", "Termination"]
    return {key: game.headers.get(key, "") for key in keys}


def move_pairs(game: chess.pgn.Game) -> list[tuple[int, str | None, str | None]]:
    board = game.board()
    pairs: list[tuple[int, str | None, str | None]] = []
    current_move_number = 1
    white_san: str | None = None

    for move in game.mainline_moves():
        san = board.san(move)
        if board.turn == chess.WHITE:
            current_move_number = board.fullmove_number
            white_san = san
        else:
            pairs.append((current_move_number, white_san, san))
            white_san = None
        board.push(move)

    if white_san is not None:
        pairs.append((current_move_number, white_san, None))

    return pairs


def max_fullmove_number(game: chess.pgn.Game) -> int:
    pairs = move_pairs(game)
    return pairs[-1][0] if pairs else 0


def default_annotation_path(pgn_path: Path) -> Path:
    return pgn_path.with_suffix(pgn_path.suffix + ".plans.json")


def load_annotations(annotation_path: Path, pgn_path: Path, game: chess.pgn.Game) -> GameAnnotations:
    if not annotation_path.exists():
        headers = game_headers(game)
        return GameAnnotations(
            pgn_path=str(pgn_path),
            event=headers["Event"],
            white=headers["White"],
            black=headers["Black"],
            result=headers["Result"],
        )

    with annotation_path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise SystemExit(f"Invalid annotation file format: {annotation_path}")
    return GameAnnotations.from_json_dict(data)


def save_annotations(annotation_path: Path, annotations: GameAnnotations) -> None:
    with annotation_path.open("w", encoding="utf-8") as fh:
        json.dump(annotations.to_json_dict(), fh, indent=2)
        fh.write("")


def print_game_moves(game: chess.pgn.Game) -> None:
    headers = game_headers(game)
    print(f"Event: {headers['Event']}")
    print(f"White: {headers['White']} ({headers['WhiteElo']})")
    print(f"Black: {headers['Black']} ({headers['BlackElo']})")
    print(f"Date:  {headers['Date']}")
    print(f"Result: {headers['Result']}")
    termination = headers["Termination"]
    if termination:
        print(f"Termination: {termination}")
    print()
    for move_no, white_san, black_san in move_pairs(game):
        left = f"{move_no}. {white_san}" if white_san else f"{move_no}."
        right = black_san or ""
        print(f"{left:<16} {right}")


def print_summary(annotations: GameAnnotations) -> None:
    print(f"{annotations.white} vs {annotations.black} ({annotations.result})")
    if annotations.event:
        print(f"Event: {annotations.event}")
    print()

    if annotations.summary.strip():
        print("Game Summary:")
        print(f"  {annotations.summary}")
        print()

    if not annotations.blocks:
        print("No plan blocks recorded yet.")
        return

    for index, block in enumerate(sorted(annotations.blocks, key=lambda b: (b.start_move, b.end_move)), start=1):
        print(f"{index}. {block.kind}: {block.label} ({block.start_move}-{block.end_move}, side={block.side})")
        if block.idea:
            print(f"   Idea: {block.idea}")
        if block.trigger:
            print(f"   Trigger: {block.trigger}")
        if block.end_condition:
            print(f"   End: {block.end_condition}")
        if block.result:
            print(f"   Result: {block.result}")
        if block.opponent_plan:
            print(f"   Opponent: {block.opponent_plan}")
        if block.better_plan:
            print(f"   Better plan: {block.better_plan}")
        if block.notes:
            print(f"   Notes: {block.notes}")
        print()

    if annotations.big_lessons:
        print("Big Lessons:")
        for lesson in annotations.big_lessons:
            print(f"- {lesson}")


def parse_range(value: str) -> tuple[int, int]:
    parts = value.split("-")
    if len(parts) != 2:
        raise argparse.ArgumentTypeError("range must look like START-END, for example 12-23")
    try:
        start = int(parts[0])
        end = int(parts[1])
    except ValueError as exc:
        raise argparse.ArgumentTypeError("range must contain integers") from exc
    return start, end


def interactive_prompt(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{prompt}{suffix}: ").strip()
    return value if value else default


def interactive_add_block(annotations: GameAnnotations, max_move: int) -> None:
    print()
    print("Add a plan block")
    print("Kinds: plan, gap, opponent, transition, note")
    kind = interactive_prompt("Kind", "plan")
    label = interactive_prompt("Label", "")
    move_range = interactive_prompt("Move range START-END", "")
    start_move, end_move = parse_range(move_range)
    side = interactive_prompt("Side (white/black/both/none)", "white")
    idea = interactive_prompt("Idea", "")
    trigger = interactive_prompt("Trigger", "")
    end_condition = interactive_prompt("End condition", "")
    result = interactive_prompt("Result", "")
    opponent_plan = interactive_prompt("Opponent plan", "")
    better_plan = interactive_prompt("Better plan", "")
    notes = interactive_prompt("Notes", "")

    block = Block(
        kind=kind,
        label=label,
        start_move=start_move,
        end_move=end_move,
        side=side,
        idea=idea,
        trigger=trigger,
        end_condition=end_condition,
        result=result,
        opponent_plan=opponent_plan,
        better_plan=better_plan,
        notes=notes,
    )
    errors = block.validate(max_move)
    if errors:
        raise SystemExit("Invalid block:" + "".join(errors))
    annotations.blocks.append(block)


def interactive_review(pgn_path: Path, annotation_path: Path) -> int:
    game = load_game(pgn_path)
    annotations = load_annotations(annotation_path, pgn_path, game)
    max_move = max_fullmove_number(game)

    print_game_moves(game)
    print()
    print(f"Max fullmove number: {max_move}")
    print(f"Annotation file: {annotation_path}")
    print()

    while True:
        print("Commands: add, summary, summary-text, lesson, delete, save, quit")
        command = input("> ").strip().lower()
        if command == "add":
            interactive_add_block(annotations, max_move)
        elif command == "summary":
            print_summary(annotations)
        elif command == "summary-text":
            annotations.summary = interactive_prompt("One-sentence game summary", annotations.summary)
        elif command == "lesson":
            lesson = interactive_prompt("Big lesson", "")
            if lesson:
                annotations.big_lessons.append(lesson)
        elif command == "delete":
            if not annotations.blocks:
                print("No blocks to delete.")
                continue
            for idx, block in enumerate(annotations.blocks, start=1):
                print(f"{idx}. {block.kind}: {block.label} ({block.start_move}-{block.end_move})")
            raw = interactive_prompt("Delete block number", "")
            try:
                block_index = int(raw)
            except ValueError:
                print("Invalid number.")
                continue
            if 1 <= block_index <= len(annotations.blocks):
                deleted = annotations.blocks.pop(block_index - 1)
                print(f"Deleted: {deleted.label}")
            else:
                print("Out of range.")
        elif command == "save":
            save_annotations(annotation_path, annotations)
            print("Saved.")
        elif command in {"quit", "exit"}:
            save_answer = interactive_prompt("Save before quitting? (y/n)", "y").lower()
            if save_answer.startswith("y"):
                save_annotations(annotation_path, annotations)
                print("Saved.")
            return 0
        else:
            print("Unknown command.")


def add_block_noninteractive(
    pgn_path: Path,
    annotation_path: Path,
    *,
    kind: str,
    label: str,
    move_range: tuple[int, int],
    side: str,
    idea: str,
    trigger: str,
    end_condition: str,
    result: str,
    opponent_plan: str,
    better_plan: str,
    notes: str,
) -> int:
    game = load_game(pgn_path)
    annotations = load_annotations(annotation_path, pgn_path, game)
    max_move = max_fullmove_number(game)
    start_move, end_move = move_range
    block = Block(
        kind=kind,
        label=label,
        start_move=start_move,
        end_move=end_move,
        side=side,
        idea=idea,
        trigger=trigger,
        end_condition=end_condition,
        result=result,
        opponent_plan=opponent_plan,
        better_plan=better_plan,
        notes=notes,
    )
    errors = block.validate(max_move)
    if errors:
        raise SystemExit("Invalid block:" + "".join(errors))
    annotations.blocks.append(block)
    save_annotations(annotation_path, annotations)
    print("Block added.")
    return 0


def set_summary_noninteractive(pgn_path: Path, annotation_path: Path, summary: str) -> int:
    game = load_game(pgn_path)
    annotations = load_annotations(annotation_path, pgn_path, game)
    annotations.summary = summary
    save_annotations(annotation_path, annotations)
    print("Summary saved.")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    game = load_game(Path(args.pgn))
    print_game_moves(game)
    return 0


def cmd_annotate(args: argparse.Namespace) -> int:
    pgn_path = Path(args.pgn)
    annotation_path = Path(args.annotations) if args.annotations else default_annotation_path(pgn_path)
    return interactive_review(pgn_path, annotation_path)


def cmd_summary(args: argparse.Namespace) -> int:
    pgn_path = Path(args.pgn)
    game = load_game(pgn_path)
    annotation_path = Path(args.annotations) if args.annotations else default_annotation_path(pgn_path)
    annotations = load_annotations(annotation_path, pgn_path, game)
    print_summary(annotations)
    return 0


def cmd_add_block(args: argparse.Namespace) -> int:
    pgn_path = Path(args.pgn)
    annotation_path = Path(args.annotations) if args.annotations else default_annotation_path(pgn_path)
    return add_block_noninteractive(
        pgn_path,
        annotation_path,
        kind=args.kind,
        label=args.label,
        move_range=args.range,
        side=args.side,
        idea=args.idea,
        trigger=args.trigger,
        end_condition=args.end,
        result=args.result,
        opponent_plan=args.opponent_plan,
        better_plan=args.better_plan,
        notes=args.notes,
    )


def cmd_set_summary(args: argparse.Namespace) -> int:
    pgn_path = Path(args.pgn)
    annotation_path = Path(args.annotations) if args.annotations else default_annotation_path(pgn_path)
    return set_summary_noninteractive(pgn_path, annotation_path, args.text)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Chessplan: plan-oriented chess review CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_show = subparsers.add_parser("show", help="show headers and numbered moves")
    parser_show.add_argument("pgn", help="path to PGN file containing exactly one game")
    parser_show.set_defaults(func=cmd_show)

    parser_annotate = subparsers.add_parser("annotate", help="interactive review mode")
    parser_annotate.add_argument("pgn", help="path to PGN file containing exactly one game")
    parser_annotate.add_argument("--annotations", help="path to JSON annotation file")
    parser_annotate.set_defaults(func=cmd_annotate)

    parser_summary = subparsers.add_parser("summary", help="print stored plan blocks and lessons")
    parser_summary.add_argument("pgn", help="path to PGN file containing exactly one game")
    parser_summary.add_argument("--annotations", help="path to JSON annotation file")
    parser_summary.set_defaults(func=cmd_summary)

    parser_add = subparsers.add_parser("add-block", help="add a block non-interactively")
    parser_add.add_argument("pgn", help="path to PGN file containing exactly one game")
    parser_add.add_argument("--annotations", help="path to JSON annotation file")
    parser_add.add_argument("--kind", default="plan", help="plan, gap, opponent, transition, note")
    parser_add.add_argument("--label", required=True, help="short block label")
    parser_add.add_argument("--range", type=parse_range, required=True, help="move range START-END")
    parser_add.add_argument("--side", default="white", help="white, black, both, none")
    parser_add.add_argument("--idea", default="", help="your plan idea")
    parser_add.add_argument("--trigger", default="", help="why the block started")
    parser_add.add_argument("--end", default="", help="why the block ended")
    parser_add.add_argument("--result", default="", help="how the plan turned out")
    parser_add.add_argument("--opponent-plan", default="", help="opponent plan in this phase")
    parser_add.add_argument("--better-plan", default="", help="better plan discovered later")
    parser_add.add_argument("--notes", default="", help="freeform notes")
    parser_add.set_defaults(func=cmd_add_block)

    parser_set_summary = subparsers.add_parser("set-summary", help="set one-line game summary")
    parser_set_summary.add_argument("pgn", help="path to PGN file containing exactly one game")
    parser_set_summary.add_argument("--annotations", help="path to JSON annotation file")
    parser_set_summary.add_argument("text", help="summary text")
    parser_set_summary.set_defaults(func=cmd_set_summary)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except FileNotFoundError as exc:
        eprint(f"File not found: {exc.filename}")
        return 1
    except KeyboardInterrupt:
        eprint("Interrupted.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
