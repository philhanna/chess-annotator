# Chess Annotator — Design 2.0

*Status: Design in progress. This supersedes DESIGN.md (v1).*

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

Each segment has one required text annotation describing the author's plan or
thinking over that span of moves. The annotation is placed on the **last move**
of the segment — a retrospective summary of what happened.

---

## 3. Data Model

### 3.1 Turning Points

A turning point is a ply number. Ply 1 is white's first move; ply 2 is
black's first move; ply 3 is white's second move; and so on.

Turning points are independent of whose move falls at that ply. If the author
plays black, the first turning point (ply 1) falls on white's move.

### 3.2 Segments

Segments are **derived** from turning points. Given turning points at plies
`[p1, p2, p3, ...]`, the segments are:

- Segment 1: plies `p1` through `p2 - 1`
- Segment 2: plies `p2` through `p3 - 1`
- ...
- Segment N: plies `pN` through the game's last ply

End boundaries are never stored; they are always derived.

### 3.3 Annotation

Each segment has:

- **Label** — a short name for the plan or phase (e.g. "Queenside counterattack")
- **Annotation** — free-form text (plain text or Markdown) describing the
  author's thinking over that span of moves

Both are required. A segment with no label or no annotation is invalid.

Each segment has a `show_diagram` flag (default true). When enabled, a
board diagram is rendered at the segment's last ply using `python-chess`.
The author can toggle it off for segments where a diagram adds no value.

---

## 4. Persistence — Annotated PGN

The **annotated PGN** is the system's persistence layer and source of truth.
`python-chess` is used throughout for reading, writing, and manipulating PGN.

### 4.1 Two Files

The **original PGN** is never modified. It is imported once and kept as a
read-only reference. The server creates and owns the **annotated PGN**, which
starts as a copy of the original and accumulates the author's turning points
and annotations over time.

### 4.2 Encoding in PGN

The annotated PGN carries only one piece of annotation data: **segment
boundary markers**. At the first move of each segment, a `[%tp]` comment
marks the turning point:

```
14. Nf6+ { [%tp] } Kh8 15. Qh5 Rg8 16. Rg1
```

Nothing else — no labels, no annotation text, no flags — is stored in the
PGN. This keeps the PGN clean and avoids any concerns about format
constraints or comment length.

### 4.3 Annotation JSON

All segment content (label, annotation text, `show_diagram`) is stored in
a companion `annotation.json` file, keyed by the ply number of each
segment's turning point:

```json
{
  "segments": {
    "1":  { "label": "The opening",        "annotation": "My plan was to develop...", "show_diagram": true },
    "14": { "label": "Attack on the king", "annotation": "I decided to sacrifice...", "show_diagram": true },
    "25": { "label": "Endgame technique",  "annotation": "With the extra pawn...",    "show_diagram": false }
  }
}
```

The server always reads and writes `annotated.pgn` and `annotation.json`
together as a unit. The ply keys in the JSON must always correspond exactly
to the `[%tp]` markers in the PGN; the `GameRepository` adapter is
responsible for keeping them in sync.

### 4.4 File Layout

Each annotation lives in its own directory under a configurable store root:

```
<store_root>/
    <game-id>/
        original.pgn           ← read-only, never modified after import
        annotated.pgn          ← [%tp] boundary markers only
        annotation.json        ← labels, annotation text, show_diagram per segment
        annotated.pgn.work     ← present only when this game has an open session
        annotation.json.work   ← present only when this game has an open session
        output.pdf             ← regenerated on demand
```

The store root lives **outside the application's git repository**. It is
personal data, not project code. Its location is configured via an environment
variable or a config file.

The game identifier (directory name) is author-supplied at creation time.

### 4.5 Session Model

Multiple games may be open simultaneously. Each game tracks its own session
state independently via the presence of `.work` files.

**Open** — if no `.work` files exist, copy the main files to `.work` and begin
editing there. If `.work` files already exist (resumed after switching away or
a crash), load them as-is.

**Save** — overwrite the main files from the `.work` files; session remains open.

**Close** — if `.work` files differ from the main files, prompt the author to
save. Whether saved or discarded, delete the `.work` files.

**Exit at any time** — `.work` files persist on disk. The next `open` of that
game resumes exactly where work left off.

**List games** — scan the store and flag any game with `.work` files as
*in progress*.

**Save As** — create a new game-id directory, copy `original.pgn` there, and
copy the current `.work` files (or main files if no session is open) as the
new game's main files. The original game is untouched.

---

## 5. Use Cases

### Game Management
1. Import a new game from a PGN file
2. List all games in the store (with in-progress indicator)
3. Open an existing game to resume annotation
4. Save As — fork an annotation under a new name
5. Delete a game from the store

### Segment Authoring
6. Add a turning point (split the game at a ply)
7. Remove a turning point (merge two segments)
8. Set or edit a segment's label
9. Set or edit a segment's annotation text
10. Toggle the diagram on/off for a segment

### Session Control
11. Save (commit working copy to main files)
12. Close a game (with save prompt if unsaved changes)

### Output
13. Render the annotation to PDF
14. Upload the original PGN to Lichess and get back an analysis URL

### Navigation / Review
15. List all segments for the current game (move ranges, labels, annotation status)
16. View a single segment (move list, label, annotation, diagram preview)

---

## 6. Architecture — Hexagonal (Ports & Adapters)

### 5.1 Core Domain

- Domain model: turning points, segment derivation, annotation text
- Business rules: ply validation, segment boundary derivation, ordering invariants
- Use cases: create game, add/remove turning point, write/edit annotation, render document, upload to Lichess

`python-chess` is a domain library, not infrastructure. It is used freely
and prominently throughout the core for PGN parsing, board state, move list generation,SVG diagram rendering, and FEN extraction.

### 5.2 Ports

| Port | Responsibility |
|---|---|
| `GameRepository` | Load, save, list annotated PGNs from the store |
| `DiagramRenderer` | Render board position at a ply → SVG |
| `DocumentRenderer` | Annotated game → PDF |
| `LichessUploader` | Upload PGN to Lichess; return analysis URL |

### 5.3 Adapters

| Adapter | Port | Notes |
|---|---|---|
| `PGNFileGameRepository` | `GameRepository` | Reads/writes annotated PGN files on disk |
| `PythonChessDiagramRenderer` | `DiagramRenderer` | Uses `chess.svg` |
| `HTMLPDFDocumentRenderer` | `DocumentRenderer` | Pipeline: PGN → HTML → PDF |
| `LichessHTTPAdapter` | `LichessUploader` | HTTP POST to Lichess study/analysis API |
| `RESTAPIAdapter` | (inbound) | FastAPI; drives the domain use cases |

---

## 7. REST API

The REST API is the primary interface to the system. The CLI (for development)
and the web SPA are both clients of this API.

### 6.1 Resources

**Games**

| Method | Path | Description |
|---|---|---|
| `GET` | `/games` | List all games in the store |
| `POST` | `/games` | Create a new game from an uploaded PGN |
| `GET` | `/games/{id}` | Get game metadata and current segment list |
| `DELETE` | `/games/{id}` | Remove a game from the store |

**Turning Points**

| Method | Path | Description |
|---|---|---|
| `GET` | `/games/{id}/turning-points` | List all turning points (ply numbers) |
| `POST` | `/games/{id}/turning-points` | Add a turning point at a given ply |
| `DELETE` | `/games/{id}/turning-points/{ply}` | Remove a turning point |

**Segments**

| Method | Path | Description |
|---|---|---|
| `GET` | `/games/{id}/segments` | List all segments with their move ranges and annotations |
| `GET` | `/games/{id}/segments/{n}` | Get a single segment |
| `PUT` | `/games/{id}/segments/{n}/annotation` | Set or update the annotation for segment N |

**Rendering & Export**

| Method | Path | Description |
|---|---|---|
| `POST` | `/games/{id}/render` | Render the annotated game to PDF |
| `GET` | `/games/{id}/segment/{n}/preview` | Return HTML preview of segment N |
| `POST` | `/games/{id}/lichess` | Upload the original PGN to Lichess; return URL |

### 6.2 Ply vs. Move Notation

Internally, all positions are represented as ply numbers. The API accepts and
returns move notation in a human-readable form (e.g. `{ "move": 14, "side": "white" }`)
and converts to/from ply at the boundary using:

```
ply = (move_number - 1) * 2 + side_offset   # white=1, black=2
```

Ply values are never exposed in the API response.

---

## 8. Web Frontend (SPA)

A single-page JavaScript application served by the REST API server.

### 7.1 Layout

Two panels side by side:

- **Left — Command REPL**: The author types structured commands. Output is
  displayed inline. This mirrors the CLI experience but runs in the browser.
- **Right — Segment Preview**: A read-only HTML rendering of the segment
  currently being edited, showing the move list, annotation text, and (if
  applicable) a board diagram. This is the same HTML that feeds into the
  PDF pipeline.

### 7.2 Commands (REPL)

Commands mirror the REST API operations. Examples:

```
open my-game-vs-smith
segments
annotate 3
  (opens an inline text editor for segment 3's annotation)
turn 14w
  (adds a turning point at white's 14th move)
unturn 14w
  (removes it)
render
lichess
```

### 7.3 Lichess Page

A separate page handles Lichess upload: one button to POST the PGN, then
displays the returned analysis URL as a clickable link.

---

## 9. Rendering Pipeline

```
annotated PGN → HTML → PDF
```

| Stage | Tool | Notes |
|---|---|---|
| Move list extraction | `python-chess` | Algebraic notation for a ply range |
| Board diagrams | `python-chess` (`chess.svg`) | SVG at segment end position |
| HTML assembly | Jinja2 or similar | Template per segment: move list + annotation + diagram |
| PDF | WeasyPrint | CSS paged media for book-quality layout |

The HTML preview served by `GET /games/{id}/segments/{n}/preview` is the
intermediate HTML stage — convenient for the SPA right panel and requires
no additional rendering work.

---

## 10. File & Configuration

### 9.1 Store Location

The store root is resolved in this order:

1. `CHESS_ANNOTATOR_STORE` environment variable
2. `store_dir` in `~/.config/chess-annotator/config.yaml`
3. Built-in default: `~/chess-annotations/`

### 9.2 Config Keys

| Key | Description |
|---|---|
| `store_dir` | Path to the annotation store root |
| `author` | Author name (pre-filled at game creation) |

---

## 11. Key Design Decisions

| ID | Decision |
|---|---|
| D-001 | The annotated PGN is the persistence layer. No separate JSON or SQL store. |
| D-002 | Original PGN is never modified. The server owns the annotated PGN. |
| D-003 | Only segment boundary markers (`{ [%tp] }`) are stored in the PGN, on the first move of each segment. Labels, annotation text, and `show_diagram` live in a companion `annotation.json` file keyed by ply number. Eliminates all PGN format concerns. |
| D-004 | Segments are derived from turning points; end boundaries are never stored. |
| D-005 | Annotations are placed on the last move of each segment (retrospective framing). |
| D-006 | Turning points can fall on any ply, regardless of which side is moving. |
| D-007 | The REST API is the primary interface. CLI and web SPA are both clients. |
| D-008 | No chess engine, no AI. Author's thinking is the sole annotation source. |
| D-009 | `python-chess` is a domain library, used throughout the core. |
| D-010 | Store directory lives outside the application git repo (personal data). |
| D-011 | PDF pipeline: annotated PGN → HTML → PDF via WeasyPrint. HTML is also used for the SPA segment preview. |
| D-012 | Ply is the internal representation. API and UI speak move+side; conversion happens at the boundary. |
| D-013 | Each segment has a `show_diagram` boolean (default true). When enabled, a board diagram is rendered at the segment's last ply using `python-chess`. The author can toggle it off for segments where a diagram adds no value. |
| D-014 | Both label and annotation are required on every segment. A segment without either is invalid and cannot be rendered. |
| D-015 | Session state is tracked per game via `.work` files in the game directory. Their presence means a session is open. No store-level session file. Multiple games may be open simultaneously. |
