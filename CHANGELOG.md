# Changelog

All notable changes to this project will be documented in this file.

## [2.0.0] - 2026-04-22

### Added
- Interactive annotate web app (`chess-annotate` CLI) with PGN loading, move navigation, comment editing, and save flow
- Board flip toggle in annotate app
- Player names and game title displayed on annotate board
- Zeroth-ply annotation support
- Browser selection option in annotate CLI
- Clear-comments action
- Pane splitters in annotate UI
- Warn before discarding unsaved annotate changes
- Print rendered PDF output path

### Changed
- Annotate board size and title styling adjusted
- Annotator work areas lightened; UI theme refreshed
- Annotate FastAPI server replaced
- Help text updated in CLI

## [1.0.0] - 2026-04-21

### Added
- `chess-render` CLI command with optional `-o` output path (defaults to input stem + `.pdf` in cwd) and `-r` orientation flag
- Board diagrams rendered before move text in each segment
- `libcairo2-dev` system dependency documented in README

### Changed
- All dependencies moved to core; `pip install .` installs everything
- `render_cli` moved into the `adapters` package
- Render model refactored into ports-and-adapters layers with separate dataclass modules
- Docstrings expanded across all source modules
- Board diagrams fixed at 80 mm × 80 mm, centred on page; board appearance adjusted
- Comment line spacing increased to 18 pt; title/subtitle spacing to 12 pt

## [0.9.0] - 2026-04-21

### Added
- Added PGN specification

### Changed
- Deleted old files
