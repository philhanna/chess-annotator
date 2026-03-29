# Chess Book Feature

## Goal

Add a new workflow that treats specially formatted `#chp` comments inside a PGN as the only source of truth for plan-oriented review output.

The tool should read a single PGN game, find `#chp` markers in the mainline, divide the game into strategic chunks, and emit a Markdown document that includes bold move text, inline SVG board diagrams, and the user's comments.

This workflow replaces the sidecar JSON annotation model.

## Source Of Truth

- The PGN file is the only source of truth.
- No auxiliary annotation files should be created or read.
- Only comments prefixed with `#chp` have meaning to this feature.
- All other PGN comments should be ignored.

## `#chp` Comment Format

Each structured plan marker lives inside a PGN comment and uses a relaxed semicolon-delimited format.

Example:

```pgn
{#chp label: Kingside expansion; kind: plan; comments: Gain space and prepare f4.}
```

Rules:

- Fields are separated by `;`
- Keys and values are separated by `:`
- Required keys: `label`, `kind`
- Optional key: `comments`
- Unknown keys are an error
- Duplicate keys should be treated as an error
- Whitespace around keys and values should be ignored

## Allowed `kind` Values

The `kind` field is restricted to this fixed set:

- `plan`
- `transition`
- `defense`

Any other `kind` value is an error.

## Parsing Rules

- The parser reads exactly one game from the PGN.
- `#chp` markers are valid only in the mainline.
- A `#chp` marker inside a variation is an error.
- Malformed `#chp` content should fail fast with a warning and a nonzero exit code.
- Error messages should identify the move location when possible and include enough detail to diagnose the malformed marker.

Examples of malformed input:

- missing `label`
- missing `kind`
- invalid `kind`
- unknown field name
- duplicate field name
- invalid field syntax
- `#chp` marker inside a variation

## Chunk Boundaries

The game is split into chunks using exact half-move precision.

Rules:

- Each `#chp` marks the end of the chunk up to the exact point where the comment appears.
- The chunk includes the move immediately preceding that comment.
- This must work for both White and Black games, so fullmove-only boundaries are not sufficient.
- The first chunk begins at the start of the game.
- For a game where the user is Black, this may effectively mean a chunk beginning before `1...`.

## Final Chunk Behavior

If the game ends without a trailing `#chp` marker:

- The final chunk should still be emitted.
- That final implicit chunk carries forward only the previous `comments` field.
- It does not inherit the previous `label`.
- It does not inherit the previous `kind`.
- The final chunk does not include an SVG diagram.

## Output Format

The new command should emit Markdown to standard output.

For each chunk, output:

- the moves in PGN-style notation with no embedded newlines, rendered in Markdown bold
- an inline SVG diagram showing the board position at the exact point where the chunk ends
- the chunk's `comments` text in regular body text

Rules:

- Do not emit a chunk heading
- Do not include non-`#chp` comments from the PGN
- The board diagram must reflect the exact board state at the `#chp` position, not merely the end of the fullmove
- Exception: the last chunk, containing the final move of the game, should not include an SVG diagram

## Board Orientation

Board orientation should be controlled by a command-line switch indicating whether the output should be shown from White's perspective or Black's perspective.

## CLI Direction

- This should be implemented as a new CLI command
- The command name is still to be decided
- The existing interactive annotation workflow is expected to go away as this feature replaces it

## Summary

This feature turns a lightly annotated PGN into a Markdown "chess book" document driven entirely by embedded `#chp` markers. The design prioritizes:

- PGN as the single source of truth
- exact half-move chunk boundaries
- strict validation with fail-fast behavior
- simple, human-editable annotation syntax
- Markdown output with inline diagrams
