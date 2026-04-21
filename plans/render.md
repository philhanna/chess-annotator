# Rendering an Annotated Game

Given an annotated .pgn file, the `chess-render` mainline will render it as a PDF.
The main added feature of this rendering tool is to include board diagrams
at specific move plies that are marked with the NAG (Numeric Analytical Glyph) $220.

## Input

- A .pgn file name.
- A required option (-o | --output) to specify the name of the PDF output file
- An option (-r | --orientation) to render the board diagrams from either the white or black orientation.  Default is white
- An option (-w | --width) for the page width in columns.  Default is 72.

## Parsing

The Python chess library will parse the .pgn file and provide
the move text, comments, and diagrams for any ply or move as
required.

## Output

The PGN has a set of tag-value pairs which are referenced below.
The output is a PDF file having the following structure:

### Title

The title should be centered across the page.

1. The first line of the title is the player names, taken from
the White and Black tags.  The format should be
`<White> - <Black>` in bold, in a larger font than the body
of the game.

2. Line 2 should be the Event and Date tag values, separated by a comma.
The font should be italic, same size as the body font.
The date format should be dd-mmm-yyyy if all three date components are
present, mmm-yyyy if the day component is missing, and yyyy if the day
and month components are missing.  If all three are missing, no date
should be printed.  "Missing" in this context means represented by
question marks.

3. Opening: The value of the Opening tag.  If not available, this line
is not printed

### Game moves

The moves of the game are separated into segments.  A segment
begins with either the opening of the game or the ply after
the last segment.  A segment ends at the end of the game or
the ply before the next segment.

A new segment starts with any ply containing a comment.

The moves in a segment should be printed in bold on one logical line,
which may be wrapped to accomodate the page width. Any NAGs in this
table are printed with their corresponding symbol:

| NAG | Symbol | 
|-----|--------|
| $1 | ! |
| $2 | ? |
| $3 | !! |
| $4 | ?? |
| $5 | !? |
| $6 | ?! |

All other NAGs are ignored, except for NAG $220.

### Board diagrams
NAG $220 indicates that a board diagram at this ply should be produced.
The diagram will be provided in SVG form by the Python Chess library.
The details of the rendering are to be determined.

The diagram should be preceded by a blank line
and followed by a caption and another blank line.
The caption should be in italics and say "After `<move>`",
where `<move>` means `<move number>. <move value>` if the
ply is odd (a white move) or `<move number> ... <move value>`
if the ply is even (a black move)

### Comments
Comments should be rendered in an ordinary font and wrapped
at the line length.
