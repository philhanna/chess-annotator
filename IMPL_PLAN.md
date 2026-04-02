# Implementation Plan — Chess Annotation System

*Based on DESIGN.md. Phase 1 only.*

---

## Project Layout

```
chess-plan/
├── pyproject.toml
├── DESIGN.md
├── IMPL_PLAN.md
├── src/
│   └── annotate/
│       ├── __init__.py
│       ├── config.py
│       ├── domain/
│       │   ├── __init__.py
│       │   ├── annotation.py     ← Annotation dataclass
│       │   ├── segment.py        ← Segment dataclass
│       │   └── model.py          ← business-rule functions
│       ├── adapters/
│       │   ├── __init__.py
│       │   ├── json_file_annotation_repository.py  ← JSONFileAnnotationRepository
│       │   └── python_chess_pgn_parser.py          ← PythonChessPGNParser
│       ├── ports/
│       │   ├── __init__.py
│       │   ├── annotation_repository.py
│       │   ├── diagram_renderer.py
│       │   ├── document_renderer.py
│       │   ├── editor_launcher.py
│       │   └── pgn_parser.py
│       ├── use_cases/
│       │   └── __init__.py
│       └── cli/
│           ├── __init__.py
│           ├── annotate.py       ← chess-annotate REPL entry point
│           └── render.py         ← chess-render CLI entry point
└── tests/
    ├── __init__.py
    ├── domain/
    │   ├── __init__.py
    │   └── test_segment.py
    └── smoke/
        └── __init__.py
```

---

## pyproject.toml

Use `setuptools` as the build backend with package discovery rooted at `src/`.
Declare two entry points:

```toml
[project.scripts]
chess-annotate = "annotate.cli.annotate:main"
chess-render   = "annotate.cli.render:main"
```

Dependencies:

| Package | Purpose |
|---|---|
| `python-chess` | PGN parsing, move generation, SVG diagrams |
| `mistune` | Markdown → HTML |
| `weasyprint` | HTML → PDF |
| `pyyaml` | Config file parsing |

Dev dependencies: `pytest`.

Store directory is configured via env var `CHESS_ANNOTATE_STORE` or a `config.yaml` file in the platform config directory. Default: built-in platform default (see §7 of DESIGN.md).

---

## M1 — Foundation ✓ Complete

**Goal:** author can create, open, browse, and save annotations. No authoring or rendering.

### Step 1 — Project scaffold

- Create `pyproject.toml` with dependencies and entry points (above).
- Create the package directories and `__init__.py` files under `src/`.
- `pip install -e .[dev]` to wire up entry points.

### Step 2 — Domain model (`domain/annotation.py`, `domain/segment.py`, `domain/model.py`)

Two dataclasses:

**`Segment`**
```python
@dataclass
class Segment:
    start_ply: int
    label: str | None = None
    commentary: str = ""
    show_diagram: bool = False
```

**`Annotation`**
```python
@dataclass
class Annotation:
    annotation_id: str          # uuid4 string
    title: str
    author: str
    date: str                   # ISO 8601
    pgn: str
    player_side: str            # "white" | "black"
    diagram_orientation: str    # "white" | "black"
    segments: list[Segment]
```

Business rules implemented as plain functions in `model.py`:

- `total_plies(pgn: str) -> int` — parse PGN via `chess`, return ply count.
- `segment_end_ply(annotation: Annotation, index: int) -> int` — derive end boundary from next segment's `start_ply` or `total_plies`.
- `ply_from_move(move_number: int, side: str) -> int` — convert using `(move_number - 1) * 2 + (1 if side == "white" else 2)`.
- `move_from_ply(ply: int) -> tuple[int, str]` — inverse conversion, returns `(move_number, "white"|"black")`.
- `find_segment_index(annotation: Annotation, ply: int) -> int` — return index of segment containing `ply`.

Keep `Annotation` in `domain/annotation.py`, `Segment` in `domain/segment.py`, and the standalone business-rule functions in `domain/model.py`.

### Step 3 — Ports (`ports/`)

Abstract base classes (use `abc.ABC`):

```python
class AnnotationRepository(ABC):
    @abstractmethod
    def save(self, annotation: Annotation) -> None: ...
    @abstractmethod
    def load(self, annotation_id: str) -> Annotation: ...
    @abstractmethod
    def list_all(self) -> list[tuple[str, str]]: ...  # (id, title)
    @abstractmethod
    def exists_working_copy(self, annotation_id: str) -> bool: ...
    @abstractmethod
    def save_working_copy(self, annotation: Annotation) -> None: ...
    @abstractmethod
    def load_working_copy(self, annotation_id: str) -> Annotation: ...
    @abstractmethod
    def discard_working_copy(self, annotation_id: str) -> None: ...
    @abstractmethod
    def commit_working_copy(self, annotation_id: str) -> None: ...

class PGNParser(ABC):
    @abstractmethod
    def parse(self, pgn_text: str) -> dict: ...
    # Returns: {"white": str, "black": str, "date": str, "total_plies": int}
```

### Step 4 — JSON repository adapter (`adapters/json_file_annotation_repository.py`)

`JSONFileAnnotationRepository` implements `AnnotationRepository`.

- Store layout mirrors §4.2 of the design: `<store>/annotations/`, `<store>/work/`, `<store>/cache/`.
- Creates directories on first use.
- `save` writes to `annotations/<id>.json`; `save_working_copy` writes to `work/<id>.json`.
- `commit_working_copy` overwrites `annotations/<id>.json` from `work/<id>.json`, then deletes the working copy.
- `list_all` scans `annotations/` for `*.json` files and returns `(id, title)` pairs.
- JSON schema: exactly as in §4.4 of the design.
- Use `json.dumps(..., indent=2)` for human-readable output.
- Serialise/deserialise `Annotation` ↔ dict in a pair of pure functions: `to_dict` / `from_dict`.

### Step 5 — PGN parser adapter (`adapters/python_chess_pgn_parser.py`)

`PythonChessPGNParser` implements `PGNParser`.

- Parse PGN text with `chess.pgn.read_game(io.StringIO(pgn_text))`.
- Extract `White`, `Black`, `Date` headers.
- Count plies by iterating the main line.
- Raise `ValueError` with a descriptive message on parse failure.

### Step 6 — REPL skeleton (`cli/annotate.py`)

Implement the two-state REPL loop described in §6 of the design.

**State management:** a module-level `session` object (or a simple dataclass) holds:
- `annotation: Annotation | None`
- `dirty: bool`

**Command dispatch:** a dict mapping command name → handler function. Handler functions receive the remaining tokens from the input line.

Commands wired up in M1:

| Command | Notes |
|---|---|
| `new <path>` | Trigger interactive creation flow (§6.3). Calls `PGNParser`, builds `Annotation` with one segment, saves to working copy. |
| `open <filename>` | Load from `annotations/<filename>` into working copy; flag if working copy already exists. |
| `list` | Print table of all annotations (id, title). |
| `show` | Print segment table as per §6.4. Mark `(no label)` where absent. Show `[unsaved changes]` if dirty. |
| `save` | `commit_working_copy`; set `dirty = False`. |
| `close` | Prompt if dirty; discard working copy; clear session. |
| `help` | Print command list for current state. |
| `quit` | Same as `close` if session open, then `sys.exit(0)`. |

**Crash recovery:** at startup, scan `work/` for any `.json` files. If found, prompt: `Working copy found for '<title>'. Resume? (yes/no):`. Yes → load it into session. No → discard it.

**Input loop:** use `input("> ")` with a `try/except (EOFError, KeyboardInterrupt)` that triggers the quit path.

### Step 7 — M1 tests (`tests/domain/test_segment.py`)

Test `model.py` functions, importing `Annotation` and `Segment` from their standalone modules:

- `ply_from_move` / `move_from_ply` round-trip for white and black
- `segment_end_ply` with multiple segments and with the final segment
- `find_segment_index` for plies at segment starts, middles, and boundaries

---

## M2 — Authoring ✓ Complete

**Goal:** author can split/merge segments, label them, and write commentary.

### Step 8 — Split/merge use cases (`use_cases/interactors.py`)

**`split_segment(annotation, ply) -> Annotation`**

- Validate `ply` is in range `[2, total_plies]` and not already a `start_ply` of an existing segment.
- Find the containing segment index.
- Create two new segments: the earlier one keeps `label`, `commentary`, and resets `show_diagram = False`; the later one starts at `ply` with all fields empty.
- Return a new `Annotation` with the updated segment list (treat `Annotation` as immutable — use `dataclasses.replace` + list copy).

**`merge_segment(annotation, ply) -> tuple[Annotation, bool]`**

- `ply` must be the `start_ply` of a non-first segment.
- Check if the later segment has non-empty content (`label`, `commentary`, or `show_diagram`). Return `(annotation, False)` without merging if so — caller decides whether to warn.
- Otherwise remove the later segment; return `(new_annotation, True)`.

Both functions raise `ValueError` with a descriptive message for invalid inputs.

### Step 9 — REPL authoring commands

Add to the session-open command set:

**`split <move> <white|black>`**
- Convert to ply; call `split_segment`; set `dirty = True`.

**`merge <move> <white|black>`**
- Convert to ply; call `merge_segment`. If content present, print warning and prompt `Discard content of segment N? (yes/no):`. If confirmed, call `merge_segment` again (or implement a `force=True` variant).

**`label <segment#> <text>`**
- Segment numbers are 1-based in all UI (convert to 0-based for list indexing).
- Update `annotation.segments[n-1].label`; set `dirty = True`.

**`comment <segment#>`**
- Write current commentary to a temp file.
- Launch `$EDITOR` via `SystemEditorLauncher` (see Step 10).
- Read back the saved text; update `annotation.segments[n-1].commentary`; set `dirty = True`.

### Step 10 — Editor launcher (`adapters/editor_launcher.py`)

`SystemEditorLauncher` implements `EditorLauncher`:

```python
class EditorLauncher(ABC):
    @abstractmethod
    def edit(self, initial_text: str) -> str: ...
```

- Write `initial_text` to a `tempfile.NamedTemporaryFile` with `.md` suffix.
- Run `subprocess.run([os.environ.get("EDITOR", "vi"), tmp_path])`.
- Read and return the file contents after the editor exits.
- Clean up the temp file.

### Step 11 — M2 tests

Add to `tests/domain/test_segment.py`:

- `split_segment` — verify segment count, boundary derivation, content assignment, dirty handling
- `merge_segment` — verify segment count, content retention/discard, error on invalid ply
- Edge cases: split at first ply (should fail), merge first segment (should fail), split at existing boundary (should fail)

---

## M3 — Rendering

**Goal:** diagram generation, PDF pipeline, `chess-render` CLI, `diagram`/`orientation`/`see` commands.

### Step 12 — Diagram renderer (`adapters/diagram_renderer.py`)

`PythonChessDiagramRenderer` implements `DiagramRenderer`:

```python
class DiagramRenderer(ABC):
    @abstractmethod
    def render(self, pgn: str, end_ply: int, orientation: str,
               size: int, cache_dir: Path) -> Path: ...
    # Returns path to the SVG file
```

- Cache file path: `cache_dir / f"{end_ply}-{orientation}.svg"`.
- If cached file exists, return its path immediately.
- Otherwise: replay the game to `end_ply` using `chess.pgn` + board iteration, call `chess.svg.board(board, orientation=..., size=size)`, write SVG to cache path, return path.
- `orientation` maps `"white"` → `chess.WHITE`, `"black"` → `chess.BLACK`.

### Step 13 — Document renderer (`adapters/document_renderer.py`)

`MarkdownHTMLPDFRenderer` implements `DocumentRenderer`:

```python
class DocumentRenderer(ABC):
    @abstractmethod
    def render(self, annotation: Annotation, output_path: Path,
               diagram_size: int, page_size: str,
               store_dir: Path) -> None: ...
```

**Validation (Step 1):**
- Assert all segment labels are non-empty; raise `ValueError` listing segments missing labels.
- Assert PGN is parseable.

**Diagram rendering (Step 2):**
- For each segment with `show_diagram = True`:
  - Derive `end_ply` via `segment_end_ply`.
  - Call `DiagramRenderer.render(...)` with `cache_dir = store_dir / "cache" / annotation.annotation_id`.

**Markdown assembly (Step 3):**

Build a string. For each segment:

```
## {label}

{move_list}

{commentary}

{<svg>...</svg> inline, if show_diagram}

---
```

Move list generation: replay PGN to get SAN moves for the ply range. Format using standard algebraic notation with correct move numbers — e.g. for plies 3–6: `2. Nf3 Nc6 3. Bb5 a6`. Helper function `format_move_list(pgn, start_ply, end_ply) -> str`.

For inline SVG: read the cached `.svg` file and embed its content directly in the Markdown string (it will survive the Markdown → HTML conversion as a raw HTML block).

**HTML conversion (Step 4):** `mistune.html(markdown_str)`. Wrap in a full HTML document with `<link>` to the CSS stylesheet.

**CSS stylesheet:** write `src/annotate/adapters/chess_book.css` — a static asset included in the package via `pyproject.toml`. It provides:
- A4 or letter `@page` rule with margins and `counter(page)` footer
- Body font: Georgia or a CSS serif stack
- `h1`, `h2` styles for annotation title and segment headings
- `.move-list` class (monospace, slightly smaller) — applied by wrapping move list in a `<code class="move-list">` span during assembly
- `img, svg` centred with `display: block; margin: auto`
- `h2 { page-break-before: auto; break-before: avoid-page }` to discourage orphaned headings

**PDF rendering (Step 5):** `weasyprint.HTML(string=html_str).write_pdf(output_path)`.

### Step 14 — REPL rendering commands

Add to session-open commands:

**`diagram <segment#> on|off`**
- Set `annotation.segments[n-1].show_diagram`; set `dirty = True`.

**`orientation <white|black>`**
- Set `annotation.diagram_orientation`; set `dirty = True`.

**`see <move> <white|black>`**
- Derive ply; replay PGN to that ply; get FEN via `board.fen()`.
- Open `https://lichess.org/analysis/standard/<FEN>` with `webbrowser.open(url)`.

### Step 15 — `chess-render` CLI (`cli/render.py`)

```
chess-render <filename> [--size 360] [--page a4|letter] [--out <path>]
```

- Use `argparse`.
- `filename` is the annotation filename (e.g. `mygame.json`) or annotation ID, resolved against the store's `annotations/` directory.
- Load annotation via `JSONFileAnnotationRepository`.
- Call `MarkdownHTMLPDFRenderer.render(...)`.
- Print `Rendered: <output_path>` on success.

Default output path: `<annotation_id>.pdf` in the current working directory.

### Step 16 — M3 smoke test (`tests/smoke/test_render_smoke.py`)

One end-to-end test:
1. Create an `Annotation` with a known PGN (e.g. the first 10 moves of the Ruy Lopez, stored as a string constant in the test).
2. Add a second segment, set labels on both, add commentary to one, set `show_diagram = True` on one.
3. Call `MarkdownHTMLPDFRenderer.render(...)` with a `tmp_path` as output.
4. Assert the output file exists and `os.path.getsize(output) > 0`.

---

## Implementation Notes

### Ply boundary convention

`start_ply = 1` is ply 1 (White's first move). This is consistent with `ply_from_move(1, "white") == 1`. The initial segment on annotation creation always has `start_ply = 1`.

### Immutability discipline

Domain functions (`split_segment`, `merge_segment`) return new `Annotation` objects rather than mutating in place. The REPL replaces `session.annotation` with the returned value and sets `dirty = True`.

### Config resolution order

1. Env var `CHESS_ANNOTATE_STORE`
2. `store_dir` key in the platform config file (`~/.config/chess-plan/config.yaml`
   on Linux/macOS, `%APPDATA%\chess-plan\config.yaml` on Windows)
3. Built-in platform default

A `get_store_dir() -> Path` function in a small `config.py` module implements this. Both CLI tools call it at startup.

### Package data

When `chess_book.css` is added, include it as package data in `pyproject.toml`
using `setuptools` package-data configuration:

```toml
[tool.setuptools.package-data]
annotate = ["adapters/chess_book.css"]
```

Access at runtime via `importlib.resources.files("annotate.adapters").joinpath("chess_book.css")`.
