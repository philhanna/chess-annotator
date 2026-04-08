# Changelog

All notable changes to this project will be documented in this file.

## [0.3.0] - 2026-04-08

### Added
- Typing a bare integer in session mode selects the current segment by number.
- PGN file path can now be passed directly to the `import` command on the command line.

### Changed
- `view` command uses the current segment and takes no argument.
- Black move notation no longer includes a space after the ellipsis (e.g. `2...dxe4`).
- `render` and `see` in session mode always use the current game; no argument accepted.
- `upload` command removed from both modes; use `see` instead.
- `delete` command removed from session mode.
- Leading and trailing quote marks are stripped from the `label` command argument.

## [1.1.0] - 2026-04-02

### Changed
- Annotation IDs are now integers, system-assigned as one greater than the
  highest ID currently in the store (previously UUID strings).
- Game title is now constructed automatically from the PGN headers
  (`White - Black Date`) rather than being prompted interactively. Any
  missing header value is substituted with `N/A`.
- Store and config directories renamed from `chess-plan` to `chess-annotator`
  to reflect the current project name.
- The `new` command no longer takes a PGN file path as a command-line
  argument; it now prompts for the path interactively as its first step.
- Author is now read directly from `config.yaml` rather than being prompted
  interactively when creating a new annotation.
- Move arguments for `split`, `merge`, and `see` now use a compact single-
  token format (`5w` / `5b`) instead of two separate tokens (`5 white` /
  `5 black`).

### Improved
- The `see` command now imports the full PGN to Lichess and opens the game
  at the requested position, replacing the previous FEN-based analysis URL.

## [1.0.0] - Initial release

### Added
- M1 — Foundation: domain model (`Annotation`, `Segment`), hexagonal
  architecture with ports and adapters, JSON file repository, YAML
  configuration with XDG/platform-standard paths.
- M2 — Authoring CLI (`chess-annotate`): interactive REPL with `new`,
  `open`, `list`, `split`, `merge`, `label`, `commentary`, `diagram`,
  `orientation`, `see`, `save`, `discard`, and `quit` commands. Working-copy
  lifecycle with stale-copy recovery on startup.
- M3 — Rendering pipeline (`chess-render`): Markdown → HTML → PDF renderer
  with SVG chess diagram generation, diagram caching, and configurable page
  and diagram sizes.
