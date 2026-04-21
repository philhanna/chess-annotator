# Design: `chess-render` PDF Renderer

## Overview

`chess-render` is a standalone command-line tool that reads an annotated PGN file
and produces a PDF document. The PDF contains a formatted game score with move
comments and inline board diagrams at plies marked with NAG `$220`.

This tool is distinct from the annotation workflow (`AnnotationService`). It
operates directly on a PGN file — no repository, no session, no working copy.

---

## Command-Line Interface

```
chess-render <pgn-file> -o <output.pdf> [-r {white,black}] [-w <columns>]
```

| Argument | Long form | Required | Default | Description |
|----------|-----------|----------|---------|-------------|
| `pgn-file` | — | yes | — | Path to the annotated `.pgn` input file |
| `-o` | `--output` | yes | — | Path for the PDF output file |
| `-r` | `--orientation` | no | `white` | Board diagram orientation: `white` or `black` |
| `-w` | `--width` | no | `72` | Page width in columns (characters) |

The tool reads the first game in the PGN file. If parsing fails or the file
does not exist, it exits with a non-zero status and a message to stderr.

---

## Architecture

The renderer is implemented as a new module `annotate.adapters.pgn_pdf_renderer`
with a thin entry-point script wired up via `pyproject.toml`.

### New dependencies

| Package | Purpose |
|---------|---------|
| `reportlab` | PDF generation (canvas, paragraphs, tables) |
| `svglib` | Convert SVG chess diagrams produced by `python-chess` to ReportLab `Drawing` objects |

These are added to `pyproject.toml` as optional dependencies under an
`[render]` extra so that users who only need the annotation workflow do not
pull in the PDF stack.

### Module layout

```
src/annotate/
  adapters/
    pgn_pdf_renderer.py   ← new: standalone rendering pipeline
  render_cli.py           ← new: argparse entry point
```

The `DocumentRenderer` port already declared in `annotate.ports` is **not used**
here. That port is wired through `AnnotationService` and targets the annotation
domain model. `chess-render` operates on raw PGN and uses `pgn_pdf_renderer`
directly.

---

## Data Flow

```
PGN file
   │
   ▼
chess.pgn.read_game()          ← python-chess parses headers, moves, NAGs, comments
   │
   ▼
RenderModel (dataclass)        ← extract all data needed for layout decisions
   │
   ├── GameHeaders
   ├── list[Segment]           ← each segment = consecutive moves + optional comment
   │       ├── moves: list[PliedMove]
   │       └── comment: str | None
   └── list[DiagramRequest]    ← (ply, move_label) for each $220 NAG
   │
   ▼
PDFBuilder                     ← drives ReportLab Platypus story
   │
   ├── _render_title()
   ├── _render_segment()  ×N
   │     ├── _render_moves()
   │     ├── _render_diagram()   (when ply has $220)
   │     └── _render_comment()
   └── doc.build(story)
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

Walk the main line with `chess.pgn.GameNode.variations[0]` (ignore sidelines).
At each node, record:

- `ply` — `node.ply()` (1-based; odd = White, even = Black)
- `san` — `node.san()` (standard algebraic notation)
- `nags` — `node.nags` (set of integer NAG codes)
- `comment` — `node.comment.strip()` (empty string if absent)

### Segment boundaries

A **segment** is a maximal run of consecutive moves that share the same
comment block. Specifically:

- Start a new segment at the first move of the game.
- Start a new segment at every ply whose `comment` is non-empty.
- The segment's comment is the comment attached to the ply that opens it
  (or empty for the opening segment if move 1 has no comment).

This matches the definition in `plans/render.md`: "A new segment starts with
any ply containing a comment."

### NAG handling

At each node, check `chess.pgn.NAG_GOOD_MOVE` (1) through `chess.pgn.NAG_DUBIOUS_MOVE` (6)
and also `220`. Build a lookup table:

```python
NAG_SYMBOLS = {1: "!", 2: "?", 3: "!!", 4: "??", 5: "!?", 6: "?!"}
NAG_DIAGRAM = 220
```

NAGs not in this table (other than 220) are silently ignored.

---

## Output Document

### Page geometry

ReportLab `SimpleDocTemplate` with:

- Page size derived from `--width`. Map common widths to standard sizes, or
  compute a custom page width using a fixed character-width assumption (e.g.
  6 pt per column at 12 pt body font ≈ 72 chars → ~432 pt ≈ 6 in).
  Default `--width 72` maps to a letter-width page (612 pt) with standard
  margins.
- Top/bottom/left/right margins: 72 pt (1 inch) by default.

### Paragraph styles

Define a `StyleSheet` with three named styles:

| Style name | Font | Size | Weight | Align |
|------------|------|------|--------|-------|
| `Title` | Helvetica-Bold | 16 pt | bold | center |
| `Subtitle` | Helvetica-Oblique | 12 pt | italic | center |
| `Moves` | Helvetica-Bold | 12 pt | bold | left |
| `Comment` | Helvetica | 12 pt | normal | left |
| `Caption` | Helvetica-Oblique | 11 pt | italic | center |

### Title section

Rendered as three `Paragraph` flowables followed by a `Spacer`.

**Line 1 — Player names**

```
<White> - <Black>
```

Style: `Title`. If either tag is `?` treat it as the literal string `?`.

**Line 2 — Event and date**

```
<Event>, <date>
```

Style: `Subtitle`. Date reformatting rules:

| PGN `Date` value | Rendered as |
|------------------|-------------|
| `2026.03.30` | `30 Mar 2026` |
| `2026.03.??` | `Mar 2026` |
| `2026.??.??` | `2026` |
| `????.??.??` | *(line 2 is still printed but date part is omitted)* |

If `Event` is `?` omit the event text (but keep the date if present). If both
are absent/unknown, omit line 2 entirely.

**Line 3 — Opening**

Only printed when the `Opening` tag is present and non-empty. Style:
`Subtitle`.

### Game moves section

For each segment, emit:

1. A `Paragraph` of the move sequence in `Moves` style.
2. If the segment's last ply (or any ply in the segment) carries NAG `$220`,
   insert a diagram block (see below).
3. If the segment has a comment, emit a `Paragraph` in `Comment` style.

**Move sequence format**

Build a single string for the whole segment:

```
<move_number>. <white_san>[<nag>] [<black_san>[<nag>]] <move_number+1>. ...
```

- If the segment starts on a Black ply, prefix the first move number with `...`:
  `5... Nf6`.
- NAG symbols are appended directly to the SAN with no space: `d5!`, `exd5?`.
- Move numbers appear before White moves. After a Black move, the next move
  number is printed before the following White move.
- The string is passed to a `Paragraph` which ReportLab wraps automatically at
  the paragraph width.

### Board diagrams

Triggered by NAG `$220` on a node.

**Diagram generation**

```python
import chess.svg
svg_text = chess.svg.board(
    board,                          # chess.Board at this ply
    orientation=chess.WHITE or chess.BLACK,   # from --orientation
    size=300,                       # fixed internal size; scaled in layout
)
```

Convert the SVG to a ReportLab `Drawing` via `svglib.svglib.svg2rlg(io.StringIO(svg_text))`.
Scale the drawing to fit within the text column width while preserving aspect ratio.
Centre it horizontally.

**Diagram layout**

Emit these flowables in order:

1. `Spacer(0, 12)` — blank line before diagram
2. The scaled `Drawing` — centred
3. `Paragraph(caption_text, Caption)` — see below
4. `Spacer(0, 12)` — blank line after caption

**Caption format**

- White move (odd ply): `After <move_number>. <san>`
- Black move (even ply): `After <move_number> ... <san>`

Example: ply 5 (White, move 3) → `After 3. Nc3`; ply 6 (Black, move 3) → `After 3 ... Qd8`.

Move number = `(ply + 1) // 2`.

### Comments

Each comment is emitted as a `Paragraph` in `Comment` style. ReportLab handles
line-wrapping automatically at the paragraph width. No manual wrapping is needed.

---

## Entry Point

`render_cli.py` contains:

```python
def main() -> None:
    args = _parse_args()
    pgn_text = Path(args.pgn_file).read_text()
    render_pdf(pgn_text, output_path=args.output,
               orientation=args.orientation, width=args.width)
```

`pyproject.toml` addition:

```toml
[project.scripts]
chess-render = "annotate.render_cli:main"

[project.optional-dependencies]
render = ["reportlab", "svglib"]
```

---

## Key Design Decisions

**Why not use the `DocumentRenderer` port?**
That port is designed for the annotation domain model (`Annotation`,
`SegmentView`, etc.). `chess-render` is a self-contained tool that reads PGN
directly. Forcing the render pipeline through `AnnotationService` would require
a repository, a working copy, and all the session machinery — none of which are
relevant to a one-shot render from a file.

**Why `Platypus` (flowable story) and not the low-level `canvas`?**
Platypus handles paragraph wrapping, page breaks, and vertical spacing
automatically, which is exactly what's needed for variable-length comments and
a page-width setting that can vary.

**Why centre diagrams rather than place them inline?**
The diagram is a fixed-aspect square object. Centring it gives clean visual
separation from the surrounding text and avoids awkward text-wrapping around
a large graphic.

**Why `svglib` rather than converting SVG to PNG first?**
`svglib` + `reportlab` keeps the diagram as a vector object inside the PDF,
producing sharp output at any print resolution without an intermediate raster
step.

---

## Error Handling

| Condition | Behaviour |
|-----------|-----------|
| PGN file does not exist | Exit 1, message to stderr |
| PGN file contains no games | Exit 1, message to stderr |
| `--output` parent directory does not exist | Exit 1, message to stderr |
| Node with `$220` but `svglib` conversion fails | Log warning; skip diagram, continue |
| `Opening` tag absent | Silently omit title line 3 |
| Missing `White`, `Black`, `Event`, `Date` | Use `?` as literal or omit per rules above |

---

## Open Questions

1. **Page size mapping**: Should `--width` accept only a column count, or also
   named sizes like `a4`/`letter`? The plan says "columns"; the existing
   `render_pdf` use case accepts a `page_size` string. If the two entry points
   should be consistent, column-count-to-page-size mapping needs to be defined
   precisely (or a named-size option added later).

2. **Diagram placement relative to segment structure**: The plan says `$220`
   marks a ply for a diagram, but does not say whether the diagram appears
   before or after the moves in the same segment. This document assumes the
   diagram appears after the move that bears `$220` and before the comment (if
   any). Confirm this is the intended reading.

3. **Multiple `$220` in one segment**: Is it valid to have more than one
   diagram-tagged ply within a single segment? This design handles it by emitting
   a diagram after each `$220` ply as the move list is built, but the visual
   result (multiple diagrams interspersed within one segment's move run) may not
   be desirable.

4. **Variation lines**: The plan says nothing about sidelines/variations in the
   PGN. This design ignores all variations and renders only the main line.
   Confirm this is correct.
