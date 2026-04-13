# Chess Annotator — Design

---

## 1. Purpose & Scope

A tool for a chess player to annotate their own games for sharing with a coach.
The author partitions a game into segments and writes a text comment on each
segment describing their plan or thinking during that phase of the game.

The system records the author's own thinking — no engine evaluation, no AI,
no move suggestions. The author's perspective is the sole source of annotation
content.

The system is for a single author. Every game annotated is one the author
played.

---

## 2. Core Concept

A game is divided into contiguous, non-overlapping **segments** that together
span every move in the game. Segments are defined by **turning points** — ply
numbers at which one phase ends and the next begins. The first turning point
is always ply 1 (the game's first move, regardless of which side the author
played).

Each segment carries:
- a **label** — a short name for the plan or phase
- an **annotation** — free-form Markdown text describing the author's thinking
- a **show_diagram** flag — whether to include a board diagram in the output

---

## 3. Data Model

### 3.1 Turning Points

A turning point is a ply number. Ply 1 is white's first move; ply 2 is
black's first move; and so on.

User-facing interfaces refer to plies by move notation:

```
move  = (ply + 1) // 2
color = white if ply is odd, else black
```

and the inverse:

```
ply = 2 * move - (1 if color == white else 0)
```

The first turning point is always ply 1. The author cannot remove it.

### 3.2 Segments

Segments are **derived** from turning points at runtime; end boundaries are
never stored. Given turning points at plies `[p1, p2, p3, ...]`:

- Segment 1: plies `1` through `p1 - 1`
- Segment 2: plies `p1` through `p2 - 1`
- …
- Segment N+1: plies `pN` through the game's last ply

### 3.3 Domain Aggregate — `Annotation`

The central domain object. It holds:

| Field | Type | Description |
|---|---|---|
| `game_id` | `str` | Author-assigned identifier; also the store directory name |
| `title` | `str` | Auto-derived from PGN headers: `White - Black Date` |
| `author` | `str` | From config |
| `date` | `str` | From PGN or prompted at import |
| `pgn` | `str` | PGN with `[%tp]` markers at turning-point plies |
| `player_side` | `str` | `white` or `black` |
| `diagram_orientation` | `str` | `white` or `black` |
| `turning_points` | `list[int]` | Sorted ply numbers; first is always 1 |
| `segment_contents` | `dict[int, SegmentContent]` | Keys match `turning_points` exactly |

`SegmentContent` has: `label` (str), `annotation` (str), `show_diagram` (bool).

Invariants enforced at construction:
- `turning_points` are sorted, unique, and begin at 1
- `segment_contents` keys exactly match `turning_points`

---

## 4. Architecture — Hexagonal (Ports & Adapters)

### 4.1 Layers

```
src/annotate/
    domain/       ← core models and derivation logic
    ports/        ← abstract interfaces (contracts)
    adapters/     ← concrete implementations
    use_cases/    ← application services and interactors
    server/       ← HTTP delivery layer (FastAPI)
    cli/          ← command-line entry points (HTTP client)
```

`python-chess` is treated as a domain library. It is used freely throughout
the core for PGN parsing, board state, move list generation, SVG diagram
rendering, and FEN extraction.

`annotate.server` is the single owner of `AnnotationService`. It exposes a
REST API and is the only layer that touches the repository and adapters at
runtime. `annotate.cli` communicates with the server exclusively over HTTP.

### 4.2 Ports

| Port | Responsibility |
|---|---|
| `GameRepository` | Load, save, list, and delete annotated games in the store |
| `PGNParser` | Parse a PGN string; return metadata dict |
| `DiagramRenderer` | Render a board position at a given ply to an SVG file |
| `DocumentRenderer` | Render an annotation to PDF |
| `EditorLauncher` | Open the system `$EDITOR` to edit annotation text |
| `LichessUploader` | Upload PGN to Lichess; return an analysis URL |

### 4.3 Adapters

| Adapter | Port | Notes |
|---|---|---|
| `PGNFileGameRepository` | `GameRepository` | Paired `.pgn` / `.json` files per game |
| `PythonChessPGNParser` | `PGNParser` | Uses `python-chess` |
| `PythonChessDiagramRenderer` | `DiagramRenderer` | SVG via `chess.svg`; cached by ply + orientation |
| `MarkdownHTMLPDFRenderer` | `DocumentRenderer` | Pipeline: annotation → Markdown → HTML → PDF |
| `SystemEditorLauncher` | `EditorLauncher` | Respects `$EDITOR`; defaults to `vi` |
| `LichessAPIUploader` | `LichessUploader` | POST to `https://lichess.org/api/import` |

---

## 5. Persistence

### 5.1 File Layout

Each game lives in its own directory under the configured store root:

```
<store_root>/
    <game-id>/
        annotated.pgn          ← [%tp] boundary markers only
        annotation.json        ← labels, annotation text, show_diagram per segment
        annotated.pgn.work     ← present only while a session is open
        annotation.json.work   ← present only while a session is open
        output.pdf             ← regenerated on demand
        diagram-cache/         ← SVG boards cached by (end_ply, orientation)
```

The store root lives outside the application's git repository. Its location is
configured via environment variable or config file.

### 5.2 PGN Format

The annotated PGN carries only one piece of annotation data: segment boundary
markers. At the first move of each segment, a `[%tp]` comment marks the
turning point. All other comments and NAGs are stripped on import.

```
1. e4 { [%tp] } e5 2. Nf3 Nc6 3. Bb5 a6 { [%tp] } 4. Ba4
```

### 5.3 JSON Format

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
    "1":  { "label": "Opening",        "annotation": "My plan was to develop...", "show_diagram": true },
    "14": { "label": "Attack",         "annotation": "I decided to sacrifice...", "show_diagram": true },
    "25": { "label": "Endgame",        "annotation": "With the extra pawn...",    "show_diagram": false }
  }
}
```

The integer keys in `segments` must exactly match the ply numbers of the
`[%tp]` markers in the PGN. The repository validates this on every write.

### 5.4 Session Model

A session is represented by the presence of `.work` files.

- **Open** — copy main files to `.work`; if `.work` already exist, resume from them.
- **Save** — overwrite main files from `.work`; session stays open.
- **Close** — if `.work` differs from main, prompt to save. Delete `.work` either way.
- **Crash** — `.work` files persist; the next `open` of that game resumes automatically.
- **Startup** — the REPL checks for stale `.work` files across all games and
  offers to resume any it finds.

---

## 6. Application Services

`AnnotationService` is the single application-layer class. It is constructed
with all ports injected and exposes the following operations:

### Game Management

| Method | Description |
|---|---|
| `import_game(...)` | Parse PGN, create `Annotation`, save canonical + working copies |
| `list_games()` | Return `GameSummary` list for all games in the store |
| `open_game(game_id)` | Load game; resume working copy if present |
| `save_game_as(source, new)` | Copy a game under a new id |
| `delete_game(game_id)` | Remove game directory |

### Session Authoring

| Method | Description |
|---|---|
| `add_turning_point(game_id, ply, label)` | Split segment; save working copy |
| `remove_turning_point(game_id, ply, force)` | Merge segment; force required if content exists |
| `set_segment_label(...)` | Update label; save working copy |
| `set_segment_annotation(...)` | Update annotation; save working copy |
| `toggle_segment_diagram(...)` | Toggle `show_diagram`; save working copy |

### Session Control

| Method | Description |
|---|---|
| `save_session(game_id)` | Commit working copy to canonical files |
| `close_game(game_id, save_changes)` | Close with optional save; returns confirmation request if needed |

### Navigation

| Method | Description |
|---|---|
| `list_segments(game_id)` | Return `SegmentSummary` list for open session |
| `view_segment(game_id, ply)` | Return `SegmentDetail` including move list and optional diagram preview |

### Output

| Method | Description |
|---|---|
| `render_pdf(game_id, diagram_size, page_size)` | Run the rendering pipeline; return path to PDF |
| `upload_to_lichess(game_id)` | Upload PGN; return Lichess URL |

**Errors:** `GameNotFoundError`, `SessionNotOpenError`, `SegmentNotFoundError`,
`OverwriteRequiredError`, `MissingDependencyError` (all extend `UseCaseError`).

---

## 7. Rendering Pipeline

```
Annotation → Markdown → HTML → PDF
```

| Stage | Tool | Notes |
|---|---|---|
| Diagram rendering | `python-chess` (`chess.svg`) | SVG at segment end ply; cached in `diagram-cache/` |
| Markdown assembly | (hand-built) | Title, byline, per-segment: header, move list, annotation, diagram |
| HTML conversion | `mistune` | Wrapped in HTML5 template with embedded `chess_book.css` |
| PDF output | `weasyprint` | CSS paged media; A4 or letter |

Validation occurs before rendering: every segment must have a non-blank label
and annotation.

---

## 8. CLI

### 8.1 Entry Points

| Command | Source | Description |
|---|---|---|
| `chess-annotate` | `annotate.cli.annotate:main` | Interactive REPL |
| `chess-render` | `annotate.cli.render:main` | Standalone PDF renderer |
| `chess-server` | `annotate.server.app:main` | Standalone API server |

`chess-server` accepts `--host` and `--port` flags (defaults: `127.0.0.1`, `8765`).

### 8.2 Server launch

`chess-annotate` manages the server lifecycle automatically:

1. On startup it probes `GET /health` at the configured `server_url`.
2. If the server is already running (e.g. `chess-server` was started separately),
   it uses the existing process.
3. If nothing is listening it starts uvicorn in a background **daemon thread**
   inside the CLI process. The thread is killed automatically when the CLI exits —
   no orphan processes.

This means the user always runs a single command and sees a single process. The
HTTP layer is otherwise transparent.

### 8.3 `chess-annotate` — Interactive REPL

The REPL maintains a session (one open game at a time). The available commands
depend on whether a session is open.

**No session open:**

| Command | Description |
|---|---|
| `import [file.pgn]` | Import a game; prompts for file if not given |
| `open <game-id>` | Open or resume a game |
| `list` | List all games in the store |
| `copy <source> <new>` | Copy a game to a new id |
| `delete <game-id>` | Delete a game |
| `render <game-id>` | Render a game to `output.pdf` |
| `see <game-id>` | Upload a game to Lichess and open the URL |
| `help` | Show this list |
| `quit` | Exit |

**Session open:**

| Command | Description |
|---|---|
| `<number>` | Select segment by number |
| `list` | List segments for the open game |
| `view` | View the current segment |
| `split <move><w\|b> [label]` | Add a turning point (e.g. `14w`) |
| `merge <move><w\|b>` | Remove a turning point |
| `label <text>` | Set the current segment label |
| `comment` | Edit the current segment annotation in `$EDITOR` |
| `diagram [on\|off]` | Toggle or set the current segment diagram flag |
| `save` | Save the open game |
| `close` | Close the current game |
| `copy <new-game-id>` | Copy the current game to a new id |
| `render` | Render the current game to `output.pdf` |
| `see` | Upload the current game to Lichess and open the URL |
| `json` | Print the working annotation JSON summary |
| `help` | Show this list |
| `quit` | Save/discard prompt, then exit |

### 8.4 `chess-render` — Standalone Renderer

```bash
chess-render <game-id> [--size PX] [--page a4|letter]
```

Renders the saved game to `<store_dir>/<game_id>/output.pdf`. Does not require
an open session.

### 8.5 Session State

The REPL session state (`annotate.cli.session`) holds:

- the open `game_id` (or `None`)
- the currently-selected turning-point ply

The session module provides a lazy-initialised `httpx.Client` (`get_client()`)
pointed at the configured `server_url`, and shared helpers (`err`, `print`,
`prompt`, `parse_move_side`, etc.) used by all command modules. All service
calls go through this client; the CLI has no direct access to the repository
or adapters.

---

## 9. Configuration

Config file location:

- Linux/macOS: `~/.config/chess-annotator/config.yaml`
- Windows: `%APPDATA%\chess-annotator\config.yaml`

| Key | Type | Default | Description |
|---|---|---|---|
| `store_dir` | path | platform default | Root directory for game storage |
| `author` | string | `""` | Pre-filled author name at import |
| `diagram_size` | int | `360` | Board size in pixels |
| `page_size` | string | `"a4"` | `a4` or `letter` |
| `server_url` | string | `"http://127.0.0.1:8765"` | URL of the API server |

`CHESS_ANNOTATE_STORE` environment variable overrides `store_dir`.

Store default (if not configured):

- Linux/macOS: `~/.local/share/chess-annotator/store`
- Windows: `%LOCALAPPDATA%\chess-annotator\store`

---

## 10. Key Design Decisions

| ID | Decision |
|---|---|
| D-001 | Persistence is paired `.pgn` + `.json` files. No database. |
| D-002 | On import, all comments and NAGs are stripped from the PGN. The stripped PGN is what the system owns. |
| D-003 | Only segment boundary markers (`{ [%tp] }`) are stored in the PGN. Labels, annotation text, and `show_diagram` live in the companion `annotation.json` keyed by ply. |
| D-004 | Segments are derived from turning points at runtime. End boundaries are never stored. |
| D-005 | Session state is represented solely by the presence of `.work` files — no separate session registry. Multiple games may have `.work` files simultaneously. |
| D-006 | `python-chess` is a domain library, used freely throughout the core. |
| D-007 | No chess engine, no AI. The author's thinking is the sole annotation source. |
| D-008 | PDF pipeline: Markdown → HTML (mistune) → PDF (weasyprint). The HTML intermediate is also useful for preview. |
| D-009 | The CLI REPL tracks one open game at a time. The current segment is tracked by turning-point ply. |
| D-010 | Move input uses compact single-token notation (`5w` / `5b`) rather than two separate tokens. |
| D-011 | Black move notation omits the space after the ellipsis: `2...dxe4`, not `2... dxe4`. |
| D-012 | The store directory lives outside the application git repository — it is personal data, not project code. |
| D-013 | `annotate.server` is the sole delivery layer that instantiates `AnnotationService`. The CLI is a thin HTTP client; all domain logic stays server-side. This allows a future browser front end to be wired to the same server without touching the application core. |
| D-014 | The server is launched in a background daemon thread by the CLI (Option B). The health-probe pattern means a separately-started `chess-server` is reused automatically, which keeps the door open for running the server standalone for browser access. |
