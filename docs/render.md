# Design: `chess-render` PDF Renderer

## Overview

`chess-render` is a standalone command-line tool that reads an annotated PGN file
and produces a PDF document. The PDF contains a formatted game score with move
comments and inline board diagrams at plies marked with NAG `$220`.

This tool operates directly on a PGN file with no dependency on any application
service layer.

---

## Command-Line Interface

```
chess-render <pgn-file> -o <output.pdf> [-r {white,black}]
```

| Argument | Long form | Required | Default | Description |
|----------|-----------|----------|---------|-------------|
| `pgn-file` | — | yes | — | Path to the annotated `.pgn` input file |
| `-o` | `--output` | yes | — | Path for the PDF output file |
| `-r` | `--orientation` | no | `white` | Board diagram orientation: `white` or `black` |

The tool reads the first game in the PGN file. Variations and sidelines are
ignored; only the main line is rendered. If parsing fails or the file does not
exist, the tool exits with a non-zero status and a message to stderr.

---

## Architecture

The renderer is implemented as two new modules:

```
src/render/
  adapters/
    pdf_renderer.py   ← rendering pipeline
  render_cli.py           ← argparse entry point
```

### New dependencies

| Package | Purpose |
|---------|---------|
| `reportlab` | PDF generation (Platypus story, paragraphs, styles) |
| `svglib` | Convert SVG chess diagrams to ReportLab `Drawing` objects |

These are added to `pyproject.toml` as an optional `[render]` extra so that
the base package stays lightweight.

---

## Data Flow

```
PGN file
   │
   ▼
chess.pgn.read_game()          ← python-chess parses headers, moves, NAGs, comments
   │
   ▼
RenderModel (dataclass)        ← all data needed for layout decisions
   │
   ├── GameHeaders
   └── list[Segment]           ← each segment = run of moves + optional diagram ply + optional comment
   │
   ▼
PDFBuilder                     ← drives ReportLab Platypus story
   │
   ├── _render_title()
   └── _render_segment()  ×N
         ├── _render_moves()
         ├── _render_diagram()   (when segment has a $220 ply)
         └── _render_comment()   (when segment has a comment)
```

---

## PGN Parsing

Use `chess.pgn.read_game()` on an `io.StringIO` of the file contents.

### Headers extracted

| PGN Tag | Usage |
|---------|-------|
| `White` | Title line 1 |
| `Black` | Title line 1 |
| `Event` | Title line 2 |
| `Date` | Title line 2 (reformatted) |
| `Opening` | Title line 3 (omitted if absent) |

### Move traversal

Walk the main line only via `node.variations[0]` at each step. At each node,
record:

- `ply` — `node.ply()` (1-based; odd = White, even = Black)
- `san` — `node.san()`
- `nags` — `node.nags` (set of integer NAG codes)
- `comment` — `node.comment.strip()` (empty string if absent)

### Segment boundaries

A **segment** is a maximal run of consecutive moves ending at (and including)
the ply that opens the next segment's comment, or at the end of the game.

- The first segment starts at ply 1.
- A new segment starts at every ply whose `comment` is non-empty.
- The comment belongs to the segment that starts at that ply.

### NAG handling

```python
NAG_SYMBOLS = {1: "!", 2: "?", 3: "!!", 4: "??", 5: "!?", 6: "?!"}
NAG_DIAGRAM = 220
```

All other NAG codes are silently ignored.

For `$220`: if a segment contains more than one ply marked `$220`, only the
first one encountered is used for the diagram. Subsequent `$220` marks in the
same segment are ignored.

---

## Output Document

### Page geometry

ReportLab `SimpleDocTemplate` with letter-size pages (612 × 792 pt) and
72 pt (1 inch) margins on all sides, giving a text area of 468 × 648 pt.

### Paragraph styles

| Style name | Font | Size | Alignment |
|------------|------|------|-----------|
| `Title` | Helvetica-Bold | 16 pt | center |
| `Subtitle` | Helvetica-Oblique | 12 pt | center |
| `Moves` | Helvetica-Bold | 12 pt | left |
| `Comment` | Helvetica | 12 pt | left |
| `Caption` | Helvetica-Oblique | 11 pt | center |

### Title section

Three optional `Paragraph` flowables followed by a `Spacer(0, 18)`.

**Line 1 — Player names** (always printed)

```
<White> - <Black>
```

Style: `Title`.

**Line 2 — Event and date**

Style: `Subtitle`. Date reformatting rules:

| PGN `Date` value | Rendered as |
|------------------|-------------|
| `2026.03.30` | `30 Mar 2026` |
| `2026.03.??` | `Mar 2026` |
| `2026.??.??` | `2026` |
| `????.??.??` | *(date portion omitted)* |

Build the line as `"<Event>, <date>"` when both are available, `"<Event>"` when
only the event is known, `"<date>"` when only the date is known. Omit line 2
entirely when neither is available. Treat `?` tag values as absent.

**Line 3 — Opening**

Printed only when the `Opening` tag is present and non-empty. Style: `Subtitle`.

### Game moves section

For each segment, emit flowables in this order:

1. Move sequence (`Moves` style)
2. Board diagram, if the segment has a `$220` ply (see below)
3. Comment, if the segment has a comment (`Comment` style)

**Move sequence format**

Build a single string for the whole segment:

```
<move_number>. <white_san>[<nag>] [<black_san>[<nag>]] <move_number+1>. ...
```

- If the segment starts on a Black ply, prefix the first move number with
  `...`: e.g. `5... Nf6`.
- NAG symbols are appended directly to the SAN with no space: `d5!`, `exd5?`.
- Move numbers appear before every White move.
- The string is passed to a `Paragraph`, which ReportLab wraps automatically.

### Board diagrams

Triggered by the first `$220` NAG encountered in a segment.

**Diagram generation**

```python
import chess.svg
svg_text = chess.svg.board(
    board,                                        # chess.Board at this ply
    orientation=chess.WHITE or chess.BLACK,       # from --orientation
    size=300,
)
```

Convert to a ReportLab `Drawing` via
`svglib.svglib.svg2rlg(io.StringIO(svg_text))`.
Scale the drawing to fit within the text column width (468 pt) while preserving
aspect ratio. Centre it horizontally using a `Table` with one cell.

**Diagram layout**

Emit these flowables in order, between the move sequence and the comment:

1. `Spacer(0, 12)`
2. Centred `Drawing`
3. `Paragraph(caption_text, Caption)`
4. `Spacer(0, 12)`

**Caption format**

- White move (odd ply): `After <move_number>. <san>`
- Black move (even ply): `After <move_number> ... <san>`

Move number = `(ply + 1) // 2`.

Examples: ply 5 → `After 3. Nc3`; ply 6 → `After 3 ... Qd8`.

### Comments

Each segment comment is a `Paragraph` in `Comment` style. ReportLab wraps
text automatically; no manual wrapping is needed.

---

## Entry Point

`render_cli.py`:

```python
def main() -> None:
    args = _parse_args()
    pgn_text = Path(args.pgn_file).read_text()
    render_pdf(pgn_text, output_path=Path(args.output),
               orientation=args.orientation)
```

`pyproject.toml` additions:

```toml
[project.scripts]
chess-render = "render.render_cli:main"

[project.optional-dependencies]
render = ["reportlab", "svglib"]
```

---

## Key Design Decisions

**Why not route through an application service?**
`chess-render` is a one-shot file-to-PDF tool. Routing it through a service
layer would require a repository, sessions, and working copies — none of which
are relevant here. The renderer reads a PGN file directly and writes a PDF.

**Why Platypus (flowable story) and not the low-level canvas?**
Platypus handles paragraph wrapping and page breaks automatically, which is
exactly what is needed for variable-length comments and a document that may
span multiple pages.

**Why centre diagrams?**
The diagram is a fixed-aspect square. Centring it gives clean visual separation
from the surrounding text and avoids awkward inline placement within a text
column.

**Why `svglib` rather than rasterising to PNG?**
`svglib` keeps the diagram as a vector object inside the PDF, producing sharp
output at any print resolution without an intermediate raster step.

---

## Error Handling

| Condition | Behaviour |
|-----------|-----------|
| PGN file does not exist | Exit 1, message to stderr |
| PGN file contains no games | Exit 1, message to stderr |
| `--output` parent directory does not exist | Exit 1, message to stderr |
| `svglib` conversion fails for a diagram | Log warning; skip diagram, continue |
| `Opening` tag absent | Silently omit title line 3 |
| Missing or `?` header values | Handled per title-section rules above |
