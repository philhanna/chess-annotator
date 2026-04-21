# Implementation Plan: `chess-render` PDF Renderer

## Files to create or modify

| File | Action |
|------|--------|
| `pyproject.toml` | Add `[render]` optional deps and `chess-render` script |
| `src/annotate/adapters/pdf_renderer.py` | Create — full rendering pipeline |
| `src/annotate/render_cli.py` | Create — argparse entry point |
| `tests/test_pdf_renderer.py` | Create — unit and smoke tests |

---

## Step 1 — Update `pyproject.toml`

Add two stanzas:

```toml
[project.scripts]
chess-render = "annotate.render_cli:main"

[project.optional-dependencies]
render = ["reportlab", "svglib"]
```

Install with `pip install -e ".[render]"` to make the `chess-render` command available.

---

## Step 2 — Implement `src/annotate/adapters/pdf_renderer.py`

The module is self-contained. It imports `chess`, `chess.pgn`, `chess.svg`,
`reportlab`, and `svglib`. It exports a single public function: `render_pdf`.

### 2a — Data model

Three frozen dataclasses hold all parsed data. Define them at module level.

```python
@dataclass(frozen=True)
class PliedMove:
    ply: int                        # 1-based; odd = White, even = Black
    san: str                        # standard algebraic notation
    nag_symbol: str | None          # "!", "?", "!!", "??", "!?", "?!" or None
    diagram_board: chess.Board | None  # board after this move; set only when NAG 220 present
    comment: str                    # stripped comment text, "" when absent
```

```python
@dataclass(frozen=True)
class GameHeaders:
    white: str      # "" when tag is absent or "?"
    black: str
    event: str
    date: str       # raw PGN date string, e.g. "2026.03.30" or "????.??.??"
    opening: str    # "" when tag is absent
```

```python
@dataclass(frozen=True)
class Segment:
    moves: tuple[PliedMove, ...]  # all plies in this segment, in order
    comment: str                  # comment text; "" when this segment has no comment
    diagram_move: PliedMove | None  # first NAG-220 move in segment; None if absent
```

Use `tuple` for `moves` so `Segment` can be frozen.

`RenderModel` is a simple named container — a `dataclass(frozen=True)` with
fields `headers: GameHeaders` and `segments: tuple[Segment, ...]`.

### 2b — `_format_date(raw: str) -> str`

Converts a PGN date string to a human-readable form.

```
"2026.03.30"  →  "30 Mar 2026"
"2026.03.??"  →  "Mar 2026"
"2026.??.??"  →  "2026"
"????.??.??"  →  ""
```

Algorithm:

1. Split on `"."` to get `[year_s, month_s, day_s]`.
2. `year = None if "?" in year_s else int(year_s)`
3. `month = None if "?" in month_s else int(month_s)`
4. `day = None if "?" in day_s else int(day_s)`
5. Return:
   - `year is None` → `""`
   - `month is None` → `str(year)`
   - `day is None` → `calendar.month_abbr[month] + " " + str(year)`
   - all present → `f"{day:02d} {calendar.month_abbr[month]} {year}"`

Use `import calendar` (stdlib).

### 2c — `_parse_headers(game: chess.pgn.Game) -> GameHeaders`

Reads the tag roster from the parsed game object.

```python
def _tag(game, name):
    val = game.headers.get(name, "")
    return "" if val == "?" else val
```

Use this helper for `White`, `Black`, `Event`, `Date`. For `Opening`, use
`game.headers.get("Opening", "")` directly (no `?` substitution needed — an
absent Opening tag is an empty string, which is the sentinel for "omit").

### 2d — `_collect_moves(game: chess.pgn.Game) -> list[PliedMove]`

Walks the main line from the game root and returns one `PliedMove` per ply.

```python
NAG_SYMBOLS = {1: "!", 2: "?", 3: "!!", 4: "??", 5: "!?", 6: "?!"}
NAG_DIAGRAM = 220

moves = []
node = game
while node.variations:
    node = node.variations[0]
    ply = node.ply()
    san = node.san()
    nag_symbol = next(
        (NAG_SYMBOLS[n] for n in node.nags if n in NAG_SYMBOLS), None
    )
    has_diagram = NAG_DIAGRAM in node.nags
    diagram_board = node.board().copy() if has_diagram else None
    comment = node.comment.strip()
    moves.append(PliedMove(ply, san, nag_symbol, diagram_board, comment))
return moves
```

`node.board()` returns the board position after the move. `.copy()` is needed
because the underlying board object is mutated as traversal continues.

### 2e — `_build_segments(moves: list[PliedMove]) -> tuple[Segment, ...]`

Groups `PliedMove` objects into `Segment` objects.

Rules:
- The first segment always starts at moves[0].
- A new segment starts at every move (other than the first) whose `comment`
  is non-empty.
- Each segment's `comment` is the `comment` field of its first move.
- Each segment's `diagram_move` is the first move in the segment whose
  `diagram_board` is not `None`.

```python
def _build_segments(moves):
    if not moves:
        return ()

    groups: list[list[PliedMove]] = []
    current: list[PliedMove] = [moves[0]]

    for move in moves[1:]:
        if move.comment:
            groups.append(current)
            current = [move]
        else:
            current.append(move)
    groups.append(current)

    segments = []
    for group in groups:
        comment = group[0].comment
        diagram_move = next((m for m in group if m.diagram_board is not None), None)
        segments.append(Segment(
            moves=tuple(group),
            comment=comment,
            diagram_move=diagram_move,
        ))
    return tuple(segments)
```

### 2f — `parse_pgn(pgn_text: str) -> RenderModel`

Top-level parsing entry point.

```python
def parse_pgn(pgn_text: str) -> RenderModel:
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None:
        raise ValueError("PGN contains no game")
    headers = _parse_headers(game)
    moves = _collect_moves(game)
    segments = _build_segments(moves)
    return RenderModel(headers=headers, segments=segments)
```

### 2g — `_build_styles() -> dict[str, ParagraphStyle]`

Returns a dict mapping style name to `ParagraphStyle`. All fonts use the
built-in ReportLab PDF fonts (no external font files required).

```python
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

def _build_styles():
    return {
        "Title":    ParagraphStyle("Title",
                        fontName="Helvetica-Bold", fontSize=16,
                        alignment=TA_CENTER, spaceAfter=4),
        "Subtitle": ParagraphStyle("Subtitle",
                        fontName="Helvetica-Oblique", fontSize=12,
                        alignment=TA_CENTER, spaceAfter=4),
        "Moves":    ParagraphStyle("Moves",
                        fontName="Helvetica-Bold", fontSize=12,
                        alignment=TA_LEFT, spaceAfter=6),
        "Comment":  ParagraphStyle("Comment",
                        fontName="Helvetica", fontSize=12,
                        alignment=TA_LEFT, spaceAfter=6),
        "Caption":  ParagraphStyle("Caption",
                        fontName="Helvetica-Oblique", fontSize=11,
                        alignment=TA_CENTER, spaceAfter=4),
    }
```

### 2h — `_subtitle_text(headers: GameHeaders) -> str | None`

Builds the text for title line 2 (event + date), or returns `None` when both
are absent.

```python
def _subtitle_text(headers):
    date_str = _format_date(headers.date)
    parts = [p for p in [headers.event, date_str] if p]
    return ", ".join(parts) if parts else None
```

### 2i — `_title_flowables(headers: GameHeaders, styles: dict) -> list`

Returns a list of `Paragraph` and `Spacer` flowables for the title block.

```python
from reportlab.platypus import Paragraph, Spacer

def _title_flowables(headers, styles):
    flowables = []
    flowables.append(Paragraph(f"{headers.white} – {headers.black}", styles["Title"]))
    subtitle = _subtitle_text(headers)
    if subtitle:
        flowables.append(Paragraph(subtitle, styles["Subtitle"]))
    if headers.opening:
        flowables.append(Paragraph(headers.opening, styles["Subtitle"]))
    flowables.append(Spacer(0, 18))
    return flowables
```

Use an en dash (`–`, U+2013) between player names for typographic correctness.

### 2j — `_moves_text(segment: Segment) -> str`

Builds the complete move-sequence string for one segment.

```python
def _moves_text(segment):
    tokens = []
    for move in segment.moves:
        ply = move.ply
        move_number = (ply + 1) // 2
        san_with_nag = move.san + (move.nag_symbol or "")
        if ply % 2 == 1:
            # White move — always emit move number
            tokens.append(f"{move_number}. {san_with_nag}")
        else:
            # Black move
            if not tokens:
                # Segment starts on Black — prefix with "N..."
                tokens.append(f"{move_number}... {san_with_nag}")
            else:
                tokens.append(san_with_nag)
    return " ".join(tokens)
```

### 2k — `_caption_text(move: PliedMove) -> str`

```python
def _caption_text(move):
    move_number = (move.ply + 1) // 2
    if move.ply % 2 == 1:
        return f"After {move_number}. {move.san}"
    else:
        return f"After {move_number} ... {move.san}"
```

### 2l — `_diagram_flowables(diagram_move: PliedMove, orientation: str, styles: dict, text_width: float) -> list`

Generates the four diagram flowables: spacer, drawing, caption, spacer.

```python
import io
import chess.svg
from svglib.svglib import svg2rlg
from reportlab.platypus import Spacer, Table, TableStyle
from reportlab.lib import colors

def _diagram_flowables(diagram_move, orientation, styles, text_width):
    chess_orientation = chess.WHITE if orientation == "white" else chess.BLACK
    svg_text = chess.svg.board(
        diagram_move.diagram_board,
        orientation=chess_orientation,
        size=300,
    )
    drawing = svg2rlg(io.StringIO(svg_text))
    if drawing is None:
        import warnings
        warnings.warn(f"svglib failed to convert diagram at ply {diagram_move.ply}; skipping")
        return []

    # Scale to fit text_width while preserving aspect ratio
    scale = text_width / drawing.width
    drawing.width = text_width
    drawing.height = drawing.height * scale
    drawing.transform = (scale, 0, 0, scale, 0, 0)

    # Centre using a single-cell Table
    table = Table([[drawing]], colWidths=[text_width])
    table.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))

    caption = Paragraph(_caption_text(diagram_move), styles["Caption"])
    return [Spacer(0, 12), table, caption, Spacer(0, 12)]
```

### 2m — `_segment_flowables(segment: Segment, orientation: str, styles: dict, text_width: float) -> list`

Assembles all flowables for one segment in order: moves, diagram (if any),
comment (if any).

```python
def _segment_flowables(segment, orientation, styles, text_width):
    flowables = []
    flowables.append(Paragraph(_moves_text(segment), styles["Moves"]))
    if segment.diagram_move is not None:
        flowables.extend(_diagram_flowables(
            segment.diagram_move, orientation, styles, text_width
        ))
    if segment.comment:
        flowables.append(Paragraph(segment.comment, styles["Comment"]))
    return flowables
```

### 2n — `render_pdf(pgn_text: str, output_path: Path, orientation: str = "white") -> None`

Public entry point. Parses the PGN, builds the Platypus story, and writes the PDF.

```python
from pathlib import Path
from reportlab.lib.pagesizes import LETTER
from reportlab.platypus import SimpleDocTemplate

TEXT_WIDTH = 468.0   # 612 - 2×72 pt margins
MARGIN = 72.0

def render_pdf(pgn_text, output_path, orientation="white"):
    model = parse_pgn(pgn_text)
    styles = _build_styles()

    story = []
    story.extend(_title_flowables(model.headers, styles))
    for segment in model.segments:
        story.extend(_segment_flowables(segment, orientation, styles, TEXT_WIDTH))

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=LETTER,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=MARGIN,
    )
    doc.build(story)
```

---

## Step 3 — Implement `src/annotate/render_cli.py`

```python
import argparse
import sys
from pathlib import Path

from annotate.adapters.pdf_renderer import render_pdf


def _parse_args():
    parser = argparse.ArgumentParser(
        prog="chess-render",
        description="Render an annotated PGN file as a PDF.",
    )
    parser.add_argument("pgn_file", help="Path to the annotated .pgn input file")
    parser.add_argument("-o", "--output", required=True, help="Path for the PDF output file")
    parser.add_argument(
        "-r", "--orientation",
        choices=["white", "black"],
        default="white",
        help="Board diagram orientation (default: white)",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    pgn_path = Path(args.pgn_file)
    output_path = Path(args.output)

    if not pgn_path.exists():
        print(f"chess-render: file not found: {pgn_path}", file=sys.stderr)
        sys.exit(1)
    if not output_path.parent.exists():
        print(f"chess-render: output directory does not exist: {output_path.parent}", file=sys.stderr)
        sys.exit(1)

    try:
        pgn_text = pgn_path.read_text()
        render_pdf(pgn_text, output_path=output_path, orientation=args.orientation)
    except ValueError as exc:
        print(f"chess-render: {exc}", file=sys.stderr)
        sys.exit(1)
```

---

## Step 4 — Write `tests/test_pdf_renderer.py`

### Unit tests

**`_format_date`**

```python
def test_format_date_full():
    assert _format_date("2026.03.30") == "30 Mar 2026"

def test_format_date_no_day():
    assert _format_date("2026.03.??") == "Mar 2026"

def test_format_date_year_only():
    assert _format_date("2026.??.??") == "2026"

def test_format_date_all_missing():
    assert _format_date("????.??.??") == ""
```

**`_subtitle_text`**

```python
def test_subtitle_event_and_date():
    headers = GameHeaders(white="", black="", event="World Championship",
                          date="2026.03.30", opening="")
    assert _subtitle_text(headers) == "World Championship, 30 Mar 2026"

def test_subtitle_event_only():
    headers = GameHeaders(white="", black="", event="Blitz Open",
                          date="????.??.??", opening="")
    assert _subtitle_text(headers) == "Blitz Open"

def test_subtitle_date_only():
    headers = GameHeaders(white="", black="", event="",
                          date="2026.??.??", opening="")
    assert _subtitle_text(headers) == "2026"

def test_subtitle_neither():
    headers = GameHeaders(white="", black="", event="",
                          date="????.??.??", opening="")
    assert _subtitle_text(headers) is None
```

**`_moves_text`**

Build minimal `Segment` objects by constructing `PliedMove` instances directly.

```python
def _make_move(ply, san, nag_symbol=None, comment=""):
    return PliedMove(ply=ply, san=san, nag_symbol=nag_symbol,
                     diagram_board=None, comment=comment)

def test_moves_text_white_start():
    seg = Segment(
        moves=(_make_move(1, "e4"), _make_move(2, "d5"), _make_move(3, "exd5")),
        comment="",
        diagram_move=None,
    )
    assert _moves_text(seg) == "1. e4 d5 2. exd5"

def test_moves_text_black_start():
    seg = Segment(
        moves=(_make_move(4, "Qxd5"), _make_move(5, "Nc3")),
        comment="",
        diagram_move=None,
    )
    assert _moves_text(seg) == "2... Qxd5 3. Nc3"

def test_moves_text_nag_symbol():
    seg = Segment(
        moves=(_make_move(1, "e4"), _make_move(2, "d5", nag_symbol="!")),
        comment="",
        diagram_move=None,
    )
    assert _moves_text(seg) == "1. e4 d5!"

def test_moves_text_diagram_nag_not_shown():
    # NAG 220 sets diagram_board but not nag_symbol — nag_symbol should be None
    board = chess.Board()
    board.push_san("e4")
    move = PliedMove(ply=1, san="e4", nag_symbol=None, diagram_board=board, comment="")
    seg = Segment(moves=(move,), comment="", diagram_move=move)
    assert _moves_text(seg) == "1. e4"
```

**`_caption_text`**

```python
def test_caption_white_move():
    move = _make_move(ply=5, san="Nc3")
    assert _caption_text(move) == "After 3. Nc3"

def test_caption_black_move():
    move = _make_move(ply=6, san="Qd8")
    assert _caption_text(move) == "After 3 ... Qd8"

def test_caption_ply_1():
    move = _make_move(ply=1, san="e4")
    assert _caption_text(move) == "After 1. e4"
```

**`_build_segments`**

```python
def test_no_comments_one_segment():
    moves = [_make_move(1, "e4"), _make_move(2, "d5"), _make_move(3, "exd5")]
    segs = _build_segments(moves)
    assert len(segs) == 1
    assert segs[0].comment == ""
    assert len(segs[0].moves) == 3

def test_comment_on_move_1_one_segment():
    moves = [_make_move(1, "e4", comment="Good opening."), _make_move(2, "d5")]
    segs = _build_segments(moves)
    assert len(segs) == 1
    assert segs[0].comment == "Good opening."

def test_comment_splits_into_two_segments():
    moves = [
        _make_move(1, "e4"),
        _make_move(2, "d5"),
        _make_move(3, "Nc3", comment="White develops."),
        _make_move(4, "Nf6"),
    ]
    segs = _build_segments(moves)
    assert len(segs) == 2
    assert segs[0].comment == ""
    assert len(segs[0].moves) == 2
    assert segs[1].comment == "White develops."
    assert len(segs[1].moves) == 2

def test_multiple_comments_three_segments():
    moves = [
        _make_move(1, "e4"),
        _make_move(2, "d5", comment="Scandinavian."),
        _make_move(3, "exd5"),
        _make_move(4, "Qxd5", comment="Recapture."),
    ]
    segs = _build_segments(moves)
    assert len(segs) == 3

def test_first_diagram_per_segment_used():
    board = chess.Board()
    board.push_san("e4")
    board2 = chess.Board()
    board2.push_san("e4")
    board2.push_san("d5")
    m1 = PliedMove(ply=1, san="e4", nag_symbol=None, diagram_board=board, comment="")
    m2 = PliedMove(ply=2, san="d5", nag_symbol=None, diagram_board=board2, comment="")
    segs = _build_segments([m1, m2])
    assert segs[0].diagram_move is m1   # first $220, not second

def test_empty_moves_returns_empty():
    assert _build_segments([]) == ()
```

### Smoke test

```python
from pathlib import Path
from annotate.adapters.pdf_renderer import render_pdf

TESTDATA = Path(__file__).parent / "testdata"

def test_smoke_render_game1(tmp_path):
    pgn_text = (TESTDATA / "game1.pgn").read_text()
    out = tmp_path / "game1.pdf"
    render_pdf(pgn_text, output_path=out)
    assert out.exists()
    assert out.stat().st_size > 0

def test_smoke_render_game2(tmp_path):
    pgn_text = (TESTDATA / "game2.pgn").read_text()
    out = tmp_path / "game2.pdf"
    render_pdf(pgn_text, output_path=out)
    assert out.exists()
    assert out.stat().st_size > 0

def test_smoke_render_black_orientation(tmp_path):
    pgn_text = (TESTDATA / "game1.pgn").read_text()
    out = tmp_path / "game1_black.pdf"
    render_pdf(pgn_text, output_path=out, orientation="black")
    assert out.exists()
    assert out.stat().st_size > 0
```

---

## Implementation order

1. Update `pyproject.toml`; run `pip install -e ".[render]"` to pull in
   `reportlab` and `svglib`.
2. Implement `pdf_renderer.py` in this sequence:
   - Data model (`PliedMove`, `GameHeaders`, `Segment`, `RenderModel`)
   - `_format_date`
   - `_parse_headers`
   - `_collect_moves`
   - `_build_segments`
   - `parse_pgn` (composes the three above)
   - `_build_styles`
   - `_subtitle_text`
   - `_title_flowables`
   - `_moves_text`
   - `_caption_text`
   - `_diagram_flowables`
   - `_segment_flowables`
   - `render_pdf`
3. Implement `render_cli.py`.
4. Write `tests/test_pdf_renderer.py`.
5. Run `pytest` and fix failures.
6. Smoke-test the CLI: `chess-render tests/testdata/game1.pgn -o /tmp/game1.pdf`
   and open the output to verify layout visually.

---

## Notes and risks

**`svglib` and `io.StringIO`**: `svg2rlg` in some versions of `svglib` accepts
only a file path, not a file-like object. If that is the case, write the SVG
to a `tempfile.NamedTemporaryFile` and pass its name instead.

**`chess.svg.board` and `size` parameter**: The `size` parameter controls the
SVG viewport but does not affect the scale applied later. Using `size=300`
gives a well-structured SVG; the ReportLab scaling step adjusts the final size
to fit the text column.

**En dash in player names**: ReportLab's built-in PDF fonts include the en dash
(U+2013). If a font encoding error appears at build time, fall back to ` - `
(space-hyphen-space).

**`reportlab` `Paragraph` and HTML entities**: ReportLab's `Paragraph` class
interprets text as XML. Any `<`, `>`, or `&` characters in move text, comments,
or player names must be XML-escaped before being passed to `Paragraph`. Use
`html.escape(text)` on all user-supplied strings.
