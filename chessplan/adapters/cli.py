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
import argparse
import sys
from pathlib import Path

from chessplan.domain import GameAnnotations, GameRecord
from chessplan.use_cases.review_service import ReviewService


def eprint(*args: object) -> None:
    print(*args, file=sys.stderr)


def print_game_moves(game: GameRecord) -> None:
    headers = game.headers
    print(f"Event: {headers.event}")
    print(f"White: {headers.white} ({headers.white_elo})")
    print(f"Black: {headers.black} ({headers.black_elo})")
    print(f"Date:  {headers.date}")
    print(f"Result: {headers.result}")
    if headers.termination:
        print(f"Termination: {headers.termination}")
    print()
    for pair in game.move_pairs:
        left = f"{pair.move_number}. {pair.white_san}" if pair.white_san else f"{pair.move_number}."
        right = pair.black_san or ""
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


def interactive_add_block(service: ReviewService, annotations: GameAnnotations, game: GameRecord) -> None:
    print()
    print("Add a plan block")
    print("Kinds: plan, gap, opponent, transition, note")
    kind = interactive_prompt("Kind", "plan")
    label = interactive_prompt("Label", "")
    move_range = interactive_prompt("Move range START-END", "")
    side = interactive_prompt("Side (white/black/both/none)", "white")
    idea = interactive_prompt("Idea", "")
    trigger = interactive_prompt("Trigger", "")
    end_condition = interactive_prompt("End condition", "")
    result = interactive_prompt("Result", "")
    opponent_plan = interactive_prompt("Opponent plan", "")
    better_plan = interactive_prompt("Better plan", "")
    notes = interactive_prompt("Notes", "")

    service.add_block(
        annotations,
        game,
        kind=kind,
        label=label,
        move_range=parse_range(move_range),
        side=side,
        idea=idea,
        trigger=trigger,
        end_condition=end_condition,
        result=result,
        opponent_plan=opponent_plan,
        better_plan=better_plan,
        notes=notes,
    )


def interactive_review(service: ReviewService, pgn_path: Path, annotation_path: Path) -> int:
    game = service.load_game(pgn_path)
    annotations = service.load_annotations(annotation_path, pgn_path, game)

    print_game_moves(game)
    print()
    print(f"Max fullmove number: {game.max_fullmove_number}")
    print(f"Annotation file: {annotation_path}")
    print()

    while True:
        print("Commands: add, summary, summary-text, lesson, delete, save, quit")
        command = input("> ").strip().lower()
        if command == "add":
            interactive_add_block(service, annotations, game)
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
            service.save_annotations(annotation_path, annotations)
            print("Saved.")
        elif command in {"quit", "exit"}:
            save_answer = interactive_prompt("Save before quitting? (y/n)", "y").lower()
            if save_answer.startswith("y"):
                service.save_annotations(annotation_path, annotations)
                print("Saved.")
            return 0
        else:
            print("Unknown command.")


def cmd_show(args: argparse.Namespace, service: ReviewService) -> int:
    game = service.load_game(Path(args.pgn))
    print_game_moves(game)
    return 0


def cmd_annotate(args: argparse.Namespace, service: ReviewService) -> int:
    pgn_path = Path(args.pgn)
    annotation_path = Path(args.annotations) if args.annotations else service.default_annotation_path(pgn_path)
    return interactive_review(service, pgn_path, annotation_path)


def cmd_summary(args: argparse.Namespace, service: ReviewService) -> int:
    pgn_path = Path(args.pgn)
    game = service.load_game(pgn_path)
    annotation_path = Path(args.annotations) if args.annotations else service.default_annotation_path(pgn_path)
    annotations = service.load_annotations(annotation_path, pgn_path, game)
    print_summary(annotations)
    return 0


def cmd_add_block(args: argparse.Namespace, service: ReviewService) -> int:
    pgn_path = Path(args.pgn)
    game = service.load_game(pgn_path)
    annotation_path = Path(args.annotations) if args.annotations else service.default_annotation_path(pgn_path)
    annotations = service.load_annotations(annotation_path, pgn_path, game)
    service.add_block(
        annotations,
        game,
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
    service.save_annotations(annotation_path, annotations)
    print("Block added.")
    return 0


def cmd_set_summary(args: argparse.Namespace, service: ReviewService) -> int:
    pgn_path = Path(args.pgn)
    game = service.load_game(pgn_path)
    annotation_path = Path(args.annotations) if args.annotations else service.default_annotation_path(pgn_path)
    annotations = service.load_annotations(annotation_path, pgn_path, game)
    service.set_summary(annotations, args.text)
    service.save_annotations(annotation_path, annotations)
    print("Summary saved.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Chessplan: plan-oriented chess review CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_show = subparsers.add_parser("show", help="show headers and numbered moves")
    parser_show.add_argument("pgn", help="path to PGN file containing exactly one game")
    parser_show.set_defaults(handler=cmd_show)

    parser_annotate = subparsers.add_parser("annotate", help="interactive review mode")
    parser_annotate.add_argument("pgn", help="path to PGN file containing exactly one game")
    parser_annotate.add_argument("--annotations", help="path to JSON annotation file")
    parser_annotate.set_defaults(handler=cmd_annotate)

    parser_summary = subparsers.add_parser("summary", help="print stored plan blocks and lessons")
    parser_summary.add_argument("pgn", help="path to PGN file containing exactly one game")
    parser_summary.add_argument("--annotations", help="path to JSON annotation file")
    parser_summary.set_defaults(handler=cmd_summary)

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
    parser_add.set_defaults(handler=cmd_add_block)

    parser_set_summary = subparsers.add_parser("set-summary", help="set one-line game summary")
    parser_set_summary.add_argument("pgn", help="path to PGN file containing exactly one game")
    parser_set_summary.add_argument("--annotations", help="path to JSON annotation file")
    parser_set_summary.add_argument("text", help="summary text")
    parser_set_summary.set_defaults(handler=cmd_set_summary)

    return parser


def main(argv: list[str] | None = None) -> int:
    from chessplan.bootstrap import build_review_service

    service = build_review_service()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args, service))
    except FileNotFoundError as exc:
        eprint(f"File not found: {exc.filename}")
        return 1
    except KeyboardInterrupt:
        eprint("Interrupted.")
        return 130
