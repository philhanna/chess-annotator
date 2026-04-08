# Chess Annotator

Chess Annotator is a single-author tool for annotating your own games for a coach. It stores turning points in PGN, stores authored segment content in JSON, and can render the current game state to PDF or upload it to Lichess.

## What It Does

- Split a game into contiguous segments using turning points
- Add a label and annotation text to each segment
- Toggle whether a segment shows a board diagram
- Keep saved files and `.work` session files separate so in-progress edits survive crashes
- Render the current state of a game to `output.pdf`
- Upload the current state of a game to Lichess and return an analysis URL

The project intentionally does not do engine analysis, AI commentary, or move suggestions. The author’s perspective is the only source of annotation content.

## Installation

Install in editable mode:

```bash
pip install -e .
```

Core dependencies:

- `python-chess`
- `mistune`
- `weasyprint`
- `pyyaml`

## CLI

The project currently exposes two command-line entry points.

### `chess-annotate`

This launches an interactive REPL.

When no game is open:

- `import`
- `new`
- `open <game-id>`
- `list`
- `copy <source-game-id> <new-game-id>`
- `delete <game-id>`
- `render <game-id>`
- `upload <game-id>`
- `see <game-id>`
- `help`
- `quit`

When a game is open:

- `segments`
- `view <segment-number>`
- `split <move><w|b> [label]`
- `merge <move><w|b>`
- `label <text>`
- `comment`
- `diagram [on|off]`
- `save`
- `close`
- `copy <new-game-id>`
- `delete [game-id]`
- `render [game-id]`
- `upload [game-id]`
- `see [game-id]`
- `json`
- `help`
- `quit`

### `chess-render`

Render the current state of a saved game by `game_id`:

```bash
chess-render my-favorite-win --size 360 --page a4
```

The output is written to `<store_dir>/<game_id>/output.pdf`.

## Configuration

The application reads `config.yaml` from the standard platform config directory:

- Linux/macOS: `~/.config/chess-annotator/config.yaml`
- Windows: `%APPDATA%\chess-annotator\config.yaml`

Example:

```yaml
author: "Your Name"
store_dir: "~/chess-work/chess-annotator-store"
diagram_size: 360
page_size: "a4"
```

`CHESS_ANNOTATE_STORE` can override `store_dir`.

## Persistence Format

Each game lives in its own directory under the configured store root:

```text
<store_root>/
    <game-id>/
        annotated.pgn
        annotation.json
        annotated.pgn.work
        annotation.json.work
        output.pdf
        diagram-cache/
```

Notes:

- `annotated.pgn` stores only turning-point markers as `[%tp]` comments
- `annotation.json` stores game metadata plus segment content keyed by turning-point ply
- `.work` files exist only while a session is open
- `output.pdf` is regenerated on demand
- `diagram-cache/` stores rendered SVG boards used by PDF output

`annotation.json` has this shape:

```json
{
  "game": {
    "title": "White - Black 2024.05.01",
    "author": "Your Name",
    "date": "2024-05-01",
    "player_side": "white",
    "diagram_orientation": "white"
  },
  "segments": {
    "1": {
      "label": "Opening",
      "annotation": "Develop pieces and fight for the center.",
      "show_diagram": true
    },
    "15": {
      "label": "Kingside plan",
      "annotation": "Shift to pressure on e5 and f7.",
      "show_diagram": true
    }
  }
}
```

The PGN turning-point markers and JSON segment keys must match exactly.

## Project Structure

- `src/annotate/domain/`: core models and derivation logic
- `src/annotate/ports/`: repository and side-effect interfaces
- `src/annotate/adapters/`: file, PDF, diagram, and Lichess implementations
- `src/annotate/use_cases/`: application services and interactor logic
- `src/annotate/cli/`: command-line entry points
- `docs/`: design notes, use cases, and OpenAPI draft

## API Draft

The current API draft lives at [`docs/openapi.yaml`](/home/saspeh/dev/python/chess-annotator/docs/openapi.yaml). It reflects the game-based storage model and the current use-case service layer, but it is still documentation rather than a shipped HTTP server.
