# Chess Annotation System — Design Document

*Status: Design complete for Phase 1. Phase 2 stub retained.*

---

## 1. Purpose & Scope

A Python tool that transforms PGN chess games into richly annotated,
book-style PDF documents. The author works iteratively: dividing games
into named segments via turning points, writing Markdown commentary,
placing board diagrams, and rendering the result. Google Docs is a
secondary output target (Phase 2; deferred).

The system is for a single author (the user). It is not a multi-user
or collaborative platform. Every game annotated is one the author
played; the tool does not support annotating third-party games.

The system records the author's own analysis and thinking — the turning
points they identified, the plans they had in mind, and their commentary
on each phase of the game. It provides no chess intelligence of its own:
no engine evaluation, no move suggestions, no computer analysis. The
author's perspective is the sole source of annotation content.

---

## 2. Core Domain Model

> **Note on ply vs. move notation:** Ply is used as the internal representation
> throughout the domain model. All author-facing interfaces convert between
> move number + side (white/black) and ply at the boundary using
> `ply = (move_number - 1) * 2 + side` (white = 1, black = 2).
> Authors never see or enter raw ply numbers. (See D-011.)

### 2.1 Annotation

The root aggregate. Owns one PGN game and an ordered list of Segments.
Carries metadata (title, author, date, source PGN reference).

Attributes:

- `title` — author-supplied title
- `author` — author name
- `date` — date of the game
- `pgn` — full PGN source
- `player_side` — `white` or `black`. Required at creation time, set
  immediately after PGN import.
- `diagram_orientation` — `white` or `black`; who appears at the
  bottom of every diagram in this annotation. Defaults to `white`
  unless `player_side` is `black`, in which case it defaults to
  `black`. Can be overridden by the author at the Annotation level.
  Applies uniformly to all diagrams in the annotation.

On creation, an Annotation contains exactly one Segment spanning the
whole game (`start_ply = 1`). As analysis proceeds, the author adds
turning points by splitting segments.

### 2.2 Segment

The primary authoring object. Stored directly. Attributes:

- `start_ply` — the ply at which this segment begins (this is the
  turning point; it is metadata on the Segment, not a separate entity)
- `label` — author-supplied name describing the plan or theme for this
  stretch of moves (e.g., "The Queenside Counterattack begins").
  Optional during authoring; required at render time.
- `commentary` — free-form Markdown text (may be empty)
- `show_diagram` — boolean, default false. If true, a board diagram is
  rendered at the end of the segment, showing the position at the
  segment's end ply. Orientation is taken from the Annotation's
  `diagram_orientation`.

The segment's end boundary is **derived**: it runs from `start_ply` to
`next_segment.start_ply - 1`, or to the game's last ply for the final
segment. End boundaries are never stored.

A segment with no label, no commentary, and no diagram is valid
(placeholder status).

**Splitting:** When the author adds a turning point at ply N, the system
finds the segment containing ply N and splits it into two:
- The earlier half retains the original segment's label and commentary.
  `show_diagram` is reset to false on the earlier half.
- The later half (starting at ply N) is created empty.

**Merging:** The inverse operation — removing a turning point merges
two adjacent segments. The earlier segment's content is retained; the
later segment's content is discarded (or the author is warned).

### 2.3 RenderedDiagram

The output of rendering a segment's end position via `python-chess`.
Produced only when `show_diagram` is true. Orientation is taken from
the Annotation's `diagram_orientation`. Cached as an SVG file.
Regenerated when `show_diagram`, `diagram_orientation`, or the PGN
changes. Size is determined by the render invocation.

---

## 3. Architecture — Hexagonal (Ports & Adapters)

### 3.1 Core Domain (innermost ring)

- Domain model (§2 above)
- Business rules: segment derivation, ply validation, ordering invariants,
  render-time validation (all segment labels present)
- Use case interactors (load game, split segment, merge segment,
  write commentary, toggle diagram, render document)

### 3.2 Ports (interfaces defined by the core)

| Port | Responsibility |
|---|---|
| `AnnotationRepository` | Load, save, list Annotations |
| `DiagramRenderer` | Render position at a ply → SVG file |
| `DocumentRenderer` | Annotation → PDF |
| `PGNParser` | PGN text → internal game object |
| `EditorLauncher` | Open external editor, return saved text |

### 3.3 Adapters (implementations of ports)

| Adapter | Port | Notes |
|---|---|---|
| `JSONFileAnnotationRepository` | `AnnotationRepository` | Shared by both CLI tools |
| `PythonChessDiagramRenderer` | `DiagramRenderer` | Uses `python-chess` SVG output |
| `MarkdownHTMLPDFRenderer` | `DocumentRenderer` | Pipeline: domain → MD → HTML → PDF via WeasyPrint |
| `GoogleDocsRenderer` | `DocumentRenderer` | Phase 2; deferred |
| `LichessWebAdapter` | (Web UI only) | Phase 2; FEN-based Lichess analysis URLs |
| `SystemEditorLauncher` | `EditorLauncher` | Invokes `$EDITOR` (e.g., Vim) |

---

## 4. Persistence Strategy

### 4.1 Storage Technology

Annotations are stored as JSON files on disk, one file per annotation,
in a configurable main store directory. No database is used. The
file store is transparent, human-readable, and compatible with version
control (e.g. git) if the author chooses to use it. The store directory
is shared by both CLI tools (`chess-annotate` and `chess-render`),
configured via a config file or environment variable.

### 4.2 Directory Structure

```
<store>/
    annotations/
        <annotation_id>.json
        <annotation_id>.json
        ...
    work/
        <annotation_id>.json   ← working copy, present only during editing
    cache/
        <annotation_id>/
            <start_ply>-<orientation>.svg   ← rendered diagram cache
```

### 4.3 Editing Session Workflow

Opening an annotation copies the main store file into `work/`. All
edits are made against the working copy. The main store file is
untouched until the author explicitly saves.

- **Save** — working copy overwrites the main store file; session
  remains open.
- **Close** — session ends; if unsaved changes exist, the author is
  prompted to save. Declining discards the working copy.

A working copy present at startup (from a previous crashed session) is
flagged to the author, who can choose to resume or discard it.

`chess-render` reads the main store file directly and never touches
the working copy.

### 4.4 JSON Schema

Each annotation file contains a single JSON document:

```json
{
  "annotation_id": "uuid",
  "title": "My Game vs. Smith, 2024",
  "author": "John",
  "date": "2024-03-15",
  "pgn": "1. e4 e5 2. Nf3 ...",
  "player_side": "white",
  "diagram_orientation": "white",
  "segments": [
    {
      "start_ply": 1,
      "label": "The opening",
      "commentary": "White opens with e4. Black replies symmetrically.",
      "show_diagram": true
    }
  ]
}
```

### 4.5 Rendered Diagram Cache

Rendered SVG files are cached under `cache/<annotation_id>/` named
`<start_ply>-<orientation>.svg`. Size is supplied at render time.
Cached files are regenerated when `show_diagram`, `diagram_orientation`,
or the PGN changes.

---

## 5. Rendering Pipeline

### 5.1 Toolchain

| Stage | Tool | Notes |
|---|---|---|
| Move list generation | `python-chess` | Algebraic notation from PGN for a ply range |
| Diagram rendering | `python-chess` | SVG output at segment end ply |
| Markdown → HTML | `mistune` | Lightweight, extensible |
| HTML → PDF | `weasyprint` | CSS paged media for book-quality layout |
| Stylesheet | Custom CSS | Controls typography, page layout, diagram sizing |

### 5.2 Pipeline Steps

The pipeline transforms a fully validated Annotation into a PDF in
five steps:

**Step 1 — Validate**

Before rendering begins, the system validates:
- All segment labels are present
- The PGN is parseable

Any validation failure aborts the render with a clear error message.

**Step 2 — Render Diagrams**

For each segment where `show_diagram` is true:
- Derive the end ply from the segment boundary
- Check the diagram cache; regenerate if stale or absent
- Render the position at end ply to SVG using `python-chess`,
  with orientation from `diagram_orientation`
- Write to `cache/<annotation_id>/<start_ply>-<orientation>.svg`

**Step 3 — Build Markdown Document**

Assemble a single Markdown document from the Annotation. The document
structure is:

```
# {title}
{author} — {date}

---

## {segment label}
{move list for segment ply range}

{commentary}

[diagram SVG inline reference, if show_diagram is true]

---

## {next segment label}
...
```

Move lists are formatted in standard algebraic notation, with move
numbers shown correctly for both white and black moves. For example,
a segment spanning plies 3–6 renders as:
`2. Nf3 Nc6 3. Bb5 a6`

**Step 4 — Convert to HTML**

The Markdown document is converted to HTML using `mistune`. Diagram
SVG files are embedded inline in the HTML at this stage (not
referenced as external files), ensuring the PDF is self-contained.

**Step 5 — Render to PDF**

WeasyPrint renders the HTML document to PDF using a custom CSS
stylesheet. The stylesheet provides:

- **Page layout** — A4 or letter page size, margins suitable for
  a printed document, page numbers in the footer
- **Typography** — a serif body font appropriate for a chess book;
  segment labels styled as section headings
- **Move list styling** — monospace or semi-bold, visually distinct
  from commentary prose
- **Diagram sizing** — diagrams sized consistently, centred on the
  page, with a small caption showing the move number and side
- **Page breaks** — segments begin on a new page if they would
  otherwise be awkwardly split across pages

### 5.3 Render-Time Configuration

The following are supplied as `chess-render` command-line arguments:

- **Diagram size** — pixel dimension (square); default 360×360
- **Page size** — A4 or letter; default A4
- **Output path** — where to write the PDF

---

## 6. CLI Design (Phase 1)

### 6.1 Overview

The system provides two CLI entry points that share the same store:

- **`chess-annotate`** — interactive REPL for authoring annotations
- **`chess-render <filename> [options]`** — renders a named annotation
  to PDF from the command line; no REPL involved

```
$ chess-annotate
Chess Annotation System
Type 'help' for a list of commands.
> _
```

```
$ chess-render mygame.json --size 360 --page a4 --out mygame.pdf
```

### 6.2 REPL States

The REPL has two states. Valid commands differ by state.

**State 1 — No session open**

No annotation is loaded. The author can create, open, or list
annotations.

| Command | Description |
|---|---|
| `new <path/to/game.pgn>` | Create a new annotation from a PGN file |
| `open <filename>` | Open an existing annotation by filename |
| `list` | List all annotations in the store |
| `help` | Show available commands |
| `quit` | Exit the REPL |

**State 2 — Session open**

An annotation is loaded into the working copy. The author can edit,
view, save, or close.

| Command | Description |
|---|---|
| `show` | Display the current annotation state (see §6.4) |
| `split <move> <white\|black>` | Add a turning point; split the segment containing that move |
| `merge <move> <white\|black>` | Remove the turning point at that move; merge with previous segment |
| `label <segment#> <text>` | Set or update the label for a segment |
| `comment <segment#>` | Open `$EDITOR` to write/edit commentary for a segment |
| `diagram <segment#> on\|off` | Toggle the end-of-segment diagram for a segment |
| `orientation <white\|black>` | Override the annotation's diagram orientation |
| `see <move> <white\|black>` | Open Lichess analysis for the position after that move |
| `save` | Commit working copy to main store; stay in session |
| `close` | Close the session; prompt to save if unsaved changes exist |
| `help` | Show available commands |
| `quit` | If session open, same prompt as `close`; then exit |

### 6.3 Creating a New Annotation

The `new` command triggers an interactive creation flow:

```
> new /path/to/mygame.pgn
PGN loaded: 42 moves, White: Fischer, Black: Spassky

Title: My Game vs Spassky, 1972
Author: John
Date [1972-07-11]:
You played (white/black): white
Diagram orientation [white]:

Annotation created. 1 segment spanning moves 1–42 (white).
> _
```

Fields with defaults shown in brackets may be accepted by pressing
Enter. `player_side` has no default and must be answered.
`diagram_orientation` defaults as per D-023 and may be accepted or
overridden.

### 6.4 The Show Command

`show` displays the current annotation state in a compact table:

```
My Game vs Spassky, 1972  (white, 42 moves)  [unsaved changes]

  #  Moves          Label                          Commentary  Diagram
  1  1w – 10w       The opening                    yes         no
  2  11w – 18w      Queenside counterattack         no          yes
  3  19b – 22b      The critical moment             yes         yes
  4  23w – 42w      (no label)                      no          no

```

- Move ranges are displayed in move+side notation (e.g. `11w – 18w`)
- Segments missing a label are flagged with `(no label)`
- `[unsaved changes]` is shown in the header when the working copy
  differs from the main store

### 6.5 Error Handling

- Commands invalid in the current state print a short message:
  `Not available — no annotation is open.` or
  `Not available — an annotation is already open.`
- Invalid move numbers (out of range, wrong format) print a specific
  error and re-prompt
- `close` and `quit` with unsaved changes prompt:
  `You have unsaved changes. Save before closing? (yes/no):`

---

## 7. Application Configuration

Application configuration is stored in a YAML file at a platform-appropriate
location:

- **Linux / macOS:** `~/.config/chess-plan/config.yaml`
  (honours `$XDG_CONFIG_HOME` when set, per the XDG Base Directory
  Specification)
- **Windows:** `%APPDATA%\chess-plan\config.yaml`

### 7.1 Configuration Keys

| Key | Description |
|---|---|
| `store_dir` | Path to the annotation store directory |

### 7.2 Resolution Order

The store directory is resolved in this order:

1. `CHESS_ANNOTATE_STORE` environment variable
2. `store_dir` key in the config file
3. Built-in platform default

The config file is optional. If it is absent, the built-in default is used.
Both CLI tools (`chess-annotate` and `chess-render`) use the same resolution
logic via a shared `get_store_dir()` function in `config.py`.

---

## 8. Web UI & REST API (Phase 2)

*Deferred. To cover when Phase 2 begins:*

- REST API surface (mirrors CLI use cases)
- Lichess integration: `https://lichess.org/analysis/<FEN>` with `<moves>?color=black#<ply>`
- Interactive turning point definition (click on move in game view)
- Diagram toggle per segment

---

## 9. Development Plan

### 9.1 MVP Definition

The MVP is a fully working Phase 1 tool. It is considered complete
when the author can:

1. Import a PGN and create an annotation
2. Divide the game into named segments by adding turning points
3. Write Markdown commentary for each segment
4. Render the annotation to a book-quality PDF

Diagram support is considered MVP — the PDF output without diagrams
is functional but incomplete for the coach-sharing use case.

### 9.2 Phase 1 Milestones

**M1 — Foundation**

Domain model, JSON persistence, and REPL skeleton. No rendering.
Deliverables:
- `Annotation` and `Segment` domain objects
- JSON file store (`new`, `open`, `save`, `close`, `list`)
- REPL with state management and `show` command
- Crash recovery (stale working copy detection at startup)

At the end of M1: the author can create, open, browse, and save
annotations. No authoring or rendering yet.

**M2 — Authoring**

Full authoring command set. No rendering.
Deliverables:
- `split`, `merge`, `label`, `comment` commands
- `$EDITOR` integration for commentary
- Move+side → ply conversion at all input boundaries
- `show` updated to reflect commentary and label status

At the end of M2: the author can fully annotate a game — divide it
into segments, name each segment, and write commentary. The annotation
can be saved and reopened across sessions.

**M3 — Rendering**

Diagram generation and PDF rendering pipeline.
Deliverables:
- `python-chess` SVG diagram rendering
- Diagram cache management
- `diagram` and `orientation` commands in the REPL
- `see` command (Lichess analysis URL via FEN)
- Markdown → HTML → PDF pipeline (`mistune` + `weasyprint`)
- Custom CSS stylesheet for book-quality layout
- `chess-render` CLI tool with size, page size, and output path options

At the end of M3: the tool is complete for Phase 1. The author can
produce a PDF suitable for sharing with a coach.

### 9.3 Phase 2 (Future)

Phase 2 is not scheduled. It covers the web UI, REST API, and Lichess
integration described in §8. It will be designed when Phase 1 is
complete and in use.

### 9.4 Testing Strategy

Testing is kept minimal for Phase 1. The focus is on correctness of
the domain model and the rendering pipeline, not on coverage metrics.

- **Domain model** — light unit tests on segment splitting, merging,
  and boundary derivation. These are the most logic-dense parts of
  the system and worth testing explicitly.
- **Rendering pipeline** — one end-to-end smoke test per milestone:
  create an annotation, populate it, render to PDF, confirm the
  output exists and is non-empty.
- **CLI** — manual testing during development. Automated CLI tests
  can be added in the IDE as needed.

Full unit test coverage can be added at any time; the hexagonal
architecture keeps domain logic cleanly separated from I/O, making
it straightforward to test in isolation.

---

## 10. Open Questions

*No open questions at this time.*

---

## 11. Decisions Log

| ID | Decision | Rationale |
|---|---|---|
| D-001 | TurningPoints are thematic, author-named moments — not mechanical boundary markers | *Superseded by D-008. Retained for history.* |
| D-002 | Segments are derived, not stored | *Superseded by D-008. Retained for history.* |
| D-003 | DiagramRequests are owned by a Segment but their ply is unconstrained | *Superseded by D-020. Retained for history.* |
| D-004 | Commentary stored as Markdown, not embedded in PGN | Keeps the PGN clean and standard-compliant. Markdown is richer than PGN comment syntax and supports the book-page rendering goal. |
| D-005 | DiagramRequests are ply-anchored; segment ownership is authoring convenience only | *Superseded by D-020. Retained for history.* |
| D-006 | Segment labels are optional during authoring, required at render time | Allows fluid authoring without forcing premature naming. Render-time validation catches missing labels before output is produced. |
| D-007 | No versioning or snapshots in Phase 1 | Simplicity. A single-author tool with explicit save/close semantics does not need versioning machinery. Revisit in a later phase if needed. |
| D-008 | Segment is a first-class stored object; TurningPoint is not a separate domain entity | Nothing coheres to a TurningPoint except its role in defining segment boundaries. The turning point ply is stored as `start_ply` on the Segment. This keeps the model clean and the Segment as the primary authoring object. |
| D-009 | On creation, an Annotation has one Segment spanning the whole game (`start_ply = 1`). Adding a turning point splits the containing segment: earlier half retains authored content, later half starts empty. | Natural authoring flow: start with the whole game, progressively divide it. Keeping content with the earlier half preserves work already done. |
| D-010 | Segment end boundary is derived: `next_segment.start_ply - 1`, or game's last ply for the final segment. End boundaries are never stored. | Storing end boundaries redundantly would create consistency risk. Derivation is cheap and always correct. |
| D-011 | Ply is the internal representation throughout. All author-facing interfaces accept move number + side and convert using `ply = (move_number - 1) * 2 + side` (white = 1, black = 2). Ply values are never exposed to the author. | Authors think in moves and sides, not plies. Ply is an implementation detail; keeping the conversion at the boundary keeps the domain model clean while making the UI natural. |
| D-012 | *Superseded by D-025. Retained for history.* | |
| D-013 | Editing sessions operate against a working copy. `save` commits to the main store and keeps the session open. `close` ends the session; if unsaved changes exist, the author is prompted to save. Declining discards the working copy. No auto-save. A working copy found at startup indicates a crashed session and is flagged to the author. | Gives the author clear save/close semantics without versioning complexity. Keeping the session open after save supports continuous authoring. Crash recovery is handled gracefully. |
| D-014 | Diagram placement via inline commentary tokens | *Superseded by D-020. Retained for history.* |
| D-015 | One annotation renders to one PDF. `DocumentRenderer` takes a single Annotation. | Simplest correct model. Multi-annotation documents are not a use case. |
| D-016 | DiagramRequest owned by Annotation | *Superseded by D-020. Retained for history.* |
| D-017 | `size` and `format` are rendering configuration, not authoring attributes. They are supplied at render invocation time. | A diagram's appearance is an output decision that may vary by rendering target, not an authoring decision. |
| D-018 | Unresolved diagram token is a hard error at render time | *Superseded by D-020. Retained for history.* |
| D-019 | Commentary tokens use move+side+orientation notation | *Superseded by D-020. Retained for history.* |
| D-020 | DiagramRequest is eliminated as a domain object. A segment optionally ends with a diagram, expressed as `show_diagram` on the Segment. | Simpler model — diagram placement is always at the end of a segment, removing the need for token parsing or a separate diagram object. |
| D-021 | Segment has `show_diagram` (boolean, default false) as its only diagram attribute. Orientation is an Annotation-level concern. | Per-segment orientation overrides are unnecessary — orientation is consistent throughout an annotation. |
| D-022 | Annotation gains `player_side` — `white` or `black`. Required at creation time, set immediately after PGN import. | Captures the author's colour in the game. Drives diagram orientation default. |
| D-037 | `player_side` is restricted to `white` or `black`; `none` is not supported. Every annotated game is one the author played. | Simplifies the model. Annotating third-party games is not a use case for this tool. |
| D-023 | Annotation gains `diagram_orientation` — `white` or `black`. Defaults to `white` unless `player_side` is `black`. Applies uniformly to all diagrams in the annotation. Overridable at the Annotation level. | Consistent orientation throughout an annotation matches the author's perspective on the game. A single Annotation-level setting is simpler and sufficient. |
| D-024 | The system provides no chess intelligence. No engine evaluation, move suggestions, or computer analysis. The author's perspective is the sole source of annotation content. | The purpose of the system is to record and present the author's own thinking, not to augment or replace it. |
| D-025 | Annotations are stored as JSON files on disk, one per annotation, in a configurable store directory. No database is used. | Simpler than SQLite for a single-author tool with no querying needs. Files are human-readable, transparent, and compatible with version control if desired. |
| D-026 | Rendering toolchain: `python-chess` for move lists and diagrams, `mistune` for Markdown → HTML, custom CSS paged media stylesheet for layout, `weasyprint` for HTML → PDF. | WeasyPrint with CSS paged media produces book-quality output. The pipeline is simple, well-supported, and keeps each stage independently testable. |
| D-027 | Move list is auto-generated from the segment's ply range and rendered at the top of each segment, preceding commentary. | The author should not need to transcribe moves manually. The system derives the move list from the PGN and the segment boundaries. |
| D-028 | Google Docs pipeline deferred entirely. Not a Phase 1 or active design concern until explicitly revisited. | Simplifies scope. The PDF pipeline is sufficient for the coach-sharing use case. |
| D-029 | The CLI is a REPL with two states: no session open and session open. Valid commands differ by state. Invalid commands in the current state print a short explanatory message. | An interactive shell suits the extended authoring workflow. State-dependent commands prevent meaningless operations and guide the author naturally. |
| D-030 | New annotation creation is an interactive flow triggered by `new <path/to/game.pgn>`. The system prompts for title, author, date, player side, and diagram orientation. Fields with sensible defaults may be accepted by pressing Enter; `player_side` has no default and is required. | Interactive prompting is friendlier than requiring all fields as command-line arguments. Keeping `player_side` mandatory enforces the D-022 requirement at the right moment. |
| D-031 | Phase 1 is delivered in three milestones: M1 (Foundation), M2 (Authoring), M3 (Rendering). Each milestone produces a testable, meaningful increment. | Incremental delivery allows early validation of the domain model and persistence before investing in the rendering pipeline. |
| D-032 | Testing is minimal: light unit tests on domain model logic, one end-to-end smoke test per milestone, manual CLI testing. Full coverage can be added in the IDE as needed. | Appropriate for a single-author tool at this stage. The hexagonal architecture keeps domain logic isolated and testable independently when fuller coverage is desired. |
| D-033 | Rendering is a separate CLI tool (`chess-render`) distinct from the authoring REPL (`chess-annotate`). Both share the same store. `chess-render` reads the main store file directly and never touches the working copy. | Clean separation of authoring and rendering concerns. Rendering is a batch operation, not part of the interactive authoring session. |
| D-034 | `save` commits the working copy to the main store and keeps the session open. `close` ends the session, prompting to save if unsaved changes exist. `discard` is not a standalone command — declining to save on `close` is the discard path. | Matches the author's mental model: save is a checkpoint during work, close is when you are done. Eliminating `discard` as a separate command removes a destructive operation from the command surface. |
| D-035 | `see <move> <white\|black>` derives the FEN from the annotation's PGN at the specified ply (after the move is made) and opens `https://lichess.org/analysis/standard/<FEN>` in the default browser. Available in session state only. The move argument refers to the PGN, not to a segment. | Gives the author a quick path to Lichess analysis for any position in the game without leaving the REPL. Reuses the existing move+side input convention. |
| D-036 | Application configuration is stored in `config.yaml` under the platform's standard config directory: `~/.config/chess-plan/` on Linux/macOS (respecting `$XDG_CONFIG_HOME`), `%APPDATA%\chess-plan\` on Windows. The store directory can be overridden by an environment variable, the config file, or left to a built-in default, resolved in that order. | Following platform conventions keeps the tool well-behaved on each OS. YAML is human-readable and easy to edit by hand. The environment variable override is retained for scripting and CI use. |
