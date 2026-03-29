# chess-plan

`chess-plan` is a small CLI for plan-oriented chess game review. It loads a PGN containing exactly one game, shows the moves in order, and lets you save structured annotations about plans, gaps, transitions, and lessons learned.

The tool is designed around reviewing a game as a sequence of strategic phases rather than a list of isolated mistakes. You can mark move ranges, describe the plan you were following, note what triggered a transition, record what your opponent was aiming for, and save a short summary of the game.

The repo also includes a newer `chessbook` workflow that reads `#chp` comments embedded directly in the PGN and renders an HTML review with inline SVG board diagrams.

## Installation

The project requires Python 3.11 or newer.

```bash
pip install -e .
```

This installs the `chessplan` command defined in `pyproject.toml`. You can also run the tool with `python -m chessplan`.

## Core Commands

Show the headers and numbered moves from a PGN:

```bash
python -m chessplan show mygame.pgn
```

Start interactive review mode:

```bash
python -m chessplan annotate mygame.pgn
```

Print the saved summary and recorded blocks:

```bash
python -m chessplan summary mygame.pgn
```

Render an HTML "chess book" from `#chp` PGN comments:

```bash
python chessbook.py mygame.pgn --side white
```

If installed as a script:

```bash
chessbook mygame.pgn --side white
```

Add a block without entering interactive mode:

```bash
python -m chessplan add-block mygame.pgn \
  --label "Kingside expansion" \
  --range 12-18
```

Set a one-line summary:

```bash
python -m chessplan set-summary mygame.pgn "I improved space but missed the tactical transition."
```

## Files Created

By default, annotations are stored in a sidecar JSON file:

```text
mygame.pgn.plans.json
```

That default path is computed by `ReviewService.default_annotation_path()`, which appends `.plans.json` to the PGN filename.

## Typical Workflow

If you want to analyze `mygame.pgn`, a normal session looks like this:

1. Run `python -m chessplan annotate mygame.pgn`.
2. Read through the printed headers and move list.
3. Use `add` to record plan blocks over move ranges.
4. Use `summary-text` to save a one-sentence summary.
5. Use `lesson` to store broader takeaways.
6. Use `save` to write `mygame.pgn.plans.json`.
7. Later, run `python -m chessplan summary mygame.pgn` to review what you saved.

Inside interactive mode, the available commands are:

- `add`
- `summary`
- `summary-text`
- `lesson`
- `delete`
- `save`
- `quit`

What each command does:

- `add`: prompts for a new move-range block and appends it to the in-memory review.
- `summary`: prints the current review summary, recorded blocks, and big lessons without leaving interactive mode.
- `summary-text`: updates the one-sentence overall summary for the game.
- `lesson`: adds a single high-level takeaway to `big_lessons`.
- `delete`: lists saved blocks and removes one by number.
- `save`: writes the current annotations to the JSON sidecar file immediately.
- `quit`: exits interactive mode and asks whether you want to save first.

Notes about interactive mode:

- Changes live only in memory until you run `save` or quit and answer `y` to the save prompt.
- `quit` and `exit` both leave interactive mode.
- `summary` shows your current in-memory state, including unsaved changes.

## Call Walkthrough For `mygame.pgn`

This section walks through what happens in the code when you run:

```bash
python -m chessplan annotate mygame.pgn
```

### 1. CLI Entry Point

Python starts [chessplan/__main__.py](/home/saspeh/dev/python/chess-plan/chessplan/__main__.py), which calls `main()` in [chessplan/adapters/cli.py](/home/saspeh/dev/python/chess-plan/chessplan/adapters/cli.py).

Inside `main()`:

1. `build_review_service()` is called in [chessplan/bootstrap.py](/home/saspeh/dev/python/chess-plan/chessplan/bootstrap.py).
2. That creates a `ReviewService` with:
   `PythonChessGameLoader` for PGN parsing.
   `JsonAnnotationStore` for JSON persistence.
3. `build_parser()` creates the CLI parser.
4. The `annotate` subcommand dispatches to `cmd_annotate()`.

### 2. Choosing The Annotation Path

`cmd_annotate()` receives the parsed CLI arguments and determines where annotations should be stored.

If you do not pass `--annotations`, it calls `ReviewService.default_annotation_path()` in [chessplan/use_cases/review_service.py](/home/saspeh/dev/python/chess-plan/chessplan/use_cases/review_service.py), which turns:

```text
mygame.pgn
```

into:

```text
mygame.pgn.plans.json
```

Then `cmd_annotate()` calls `interactive_review(service, pgn_path, annotation_path)`.

### 3. Loading The PGN

`interactive_review()` calls `service.load_game(pgn_path)`.

That goes through:

1. `ReviewService.load_game()`
2. `PythonChessGameLoader.load_game()` in [chessplan/adapters/pgn_reader.py](/home/saspeh/dev/python/chess-plan/chessplan/adapters/pgn_reader.py)

The PGN loader:

- opens the file
- uses `python-chess` to read the first game
- fails if the file contains no games
- fails if the file contains more than one game
- extracts PGN header fields into `GameHeaders`
- converts the move list into `MovePair` objects with `_move_pairs()`
- returns a `GameRecord`

That `GameRecord` is the normalized in-memory representation used by the rest of the app.

### 4. Loading Existing Annotations Or Creating New Ones

Still inside `interactive_review()`, the next call is:

1. `ReviewService.load_annotations()`
2. `JsonAnnotationStore.load_annotations()` in [chessplan/adapters/json_annotations.py](/home/saspeh/dev/python/chess-plan/chessplan/adapters/json_annotations.py)

If `mygame.pgn.plans.json` does not exist yet, the store creates a fresh `GameAnnotations` object using metadata from the loaded PGN, including the event, White, Black, and result.

If the JSON file already exists, it:

- loads the JSON data
- rebuilds `Block` objects
- returns a populated `GameAnnotations` instance

### 5. Printing The Game

`interactive_review()` then calls `print_game_moves()` in [chessplan/adapters/cli.py](/home/saspeh/dev/python/chess-plan/chessplan/adapters/cli.py).

That function prints:

- event
- player names and ratings
- date
- result
- termination, if present
- the move list as full-move pairs

It also prints the maximum fullmove number using `game.max_fullmove_number`, which comes from [chessplan/domain/game.py](/home/saspeh/dev/python/chess-plan/chessplan/domain/game.py).

### 6. Recording A Plan Block

When you type `add` inside interactive mode, `interactive_review()` calls `interactive_add_block()`.

That function prompts for:

- kind
- label
- move range
- side
- idea
- what started this block
- end condition
- result
- opponent plan
- better plan
- notes

The move range is parsed by `parse_range()`, which expects `START-END`, such as `12-18`.

Then `interactive_add_block()` calls `ReviewService.add_block()`.

`ReviewService.add_block()`:

1. creates a `Block` from your inputs
2. calls `Block.validate()` in [chessplan/domain/block.py](/home/saspeh/dev/python/chess-plan/chessplan/domain/block.py)
3. checks for problems such as:
   empty `kind`
   empty `label`
   invalid `side`
   `start_move < 1`
   `end_move < start_move`
   `end_move > game.max_fullmove_number`
4. appends the validated block to `annotations.blocks`

This is the core analysis step: you convert your chess understanding into structured move-range annotations.

### 7. Adding Summary Text And Lessons

Inside the command loop:

- `summary-text` updates `annotations.summary`
- `lesson` appends a string to `annotations.big_lessons`
- `summary` prints the current saved state using `print_summary()`
- `delete` removes one recorded block by index

`print_summary()` formats the output by sorting blocks by move range and printing all the strategic fields you recorded.

### 8. Saving The Review

When you type `save`, or when you quit and choose to save, `interactive_review()` calls:

1. `ReviewService.save_annotations()`
2. `JsonAnnotationStore.save_annotations()`

The JSON store serializes the `GameAnnotations` object with `GameAnnotations.to_json_dict()` in [chessplan/domain/game_annotations.py](/home/saspeh/dev/python/chess-plan/chessplan/domain/game_annotations.py), then writes it to disk as formatted JSON.

### 9. Reviewing The Saved Analysis Later

Later, you can inspect the saved annotation file with:

```bash
python -m chessplan summary mygame.pgn
```

That command:

1. loads the PGN again
2. loads `mygame.pgn.plans.json`
3. prints the summary, blocks, and lessons

If you only want to inspect the PGN without annotations, use:

```bash
python -m chessplan show mygame.pgn
```

## Example Review Session

An example interactive flow might look like this:

```text
$ python -m chessplan annotate mygame.pgn
Commands: add, summary, summary-text, lesson, delete, save, quit
> add
Kind [plan]: plan
Label: Queenside minority attack
Move range START-END: 14-20
Side (white/black/both/none) [white]: white
Idea: Create a weak c-pawn and play against it
What started this block?:
End condition: Position opened in the center
Result: I drifted and let Black seize the initiative
Opponent plan: Counterplay against my king
Better plan: Switch to central control earlier
Notes: I underestimated ...e5
> summary-text
One-sentence game summary: Good long-term idea, poor transition when the center opened
> lesson
Big lesson: Re-evaluate the plan when the pawn structure changes
> save
Saved.
> quit
Save before quitting? (y/n) [y]:
Saved.
```

## Development Notes

The architecture is intentionally simple:

- `domain`: data models such as `Block`, `GameRecord`, and `GameAnnotations`
- `ports`: protocol interfaces for loading games and storing annotations
- `adapters`: concrete implementations for CLI, PGN parsing, and JSON storage
- `use_cases`: orchestration logic in `ReviewService`

The main flow is:

```text
CLI -> ReviewService -> GameLoader / AnnotationStore -> Domain models
```
