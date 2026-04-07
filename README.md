# Chess Annotation System

A Python-based tool designed to transform PGN chess games into richly annotated, book-style PDF documents. Unlike many chess tools, this system focuses entirely on the author's own analysis and perspective, providing no engine evaluations or computer suggestions.

## Overview

The Chess Annotation System allows you to take a game you've played and divide it into thematic segments (e.g., "The Opening", "Central Liquidation", "The Endgame Grind"). For each segment, you can write Markdown-formatted commentary and choose to display a board diagram of the resulting position.

The final output is a professional PDF rendered with high-quality typography and diagrams, suitable for sharing with coaches or publishing.

## Features

*   **Iterative Authoring:** Use an interactive CLI (`chess-annotate`) to manage your annotations.
*   **Thematic Segmentation:** Split games at specific turning points to organize your thoughts.
*   **Markdown Commentary:** Write analysis using Markdown, which is then rendered into the final document.
*   **Board Diagrams:** Automatically generate SVG board diagrams at the end of any segment.
*   **External Editor Integration:** Launches your system `$EDITOR` (e.g., Vim, Nano) for writing commentary.
*   **Lichess Integration:** Quickly open the current game state on Lichess for deep analysis.
*   **Book-Quality PDF:** Uses `WeasyPrint` and custom CSS to produce print-ready PDF files.
*   **Hexagonal Architecture:** Cleanly separated domain logic from infrastructure (PGN parsing, file storage, PDF rendering).

## Installation

The project uses `setuptools`. You can install it locally in editable mode:

```bash
pip install -e .
```

### Dependencies
*   **python-chess**: For PGN handling and diagram generation.
*   **mistune**: For Markdown to HTML conversion.
*   **weasyprint**: For HTML to PDF rendering.
*   **pyyaml**: For configuration management.

## Usage

The system provides two main CLI entry points:

### 1. Authoring: `chess-annotate`
This launches an interactive REPL where you can create or edit annotations.

*   `new`: Create a new annotation by pointing to a `.pgn` file.
*   `open <id>`: Open an existing annotation session.
*   `list`: View all annotations in your store.
*   `split <move><w/b>`: Divide a segment at a specific move (e.g., `split 12w`).
*   `label <text>`: Name the current segment.
*   `comment`: Open your editor to write commentary for the selected segment.
*   `diagram on|off`: Toggle whether a diagram appears at the end of the segment.
*   `save`: Commit your working copy to the main store.

### 2. Rendering: `chess-render`
Render a saved annotation to a PDF file.

```bash
chess-render <annotation_id> --out my_game.pdf --size 400 --page a4
```

## Configuration

The system looks for a `config.yaml` file in your platform's standard config directory:
*   **Linux/macOS**: `~/.config/chess-annotator/config.yaml`
*   **Windows**: `%APPDATA%\chess-annotator\config.yaml`

Example configuration:
```yaml
author: "Your Name"
store_dir: "~/chess_work/annotations"
diagram_size: 360
page_size: "a4"
```

## Project Structure

The project follows a **Hexagonal Architecture** (Ports and Adapters) to ensure the core chess logic remains independent of third-party libraries:

*   `src/annotate/domain/`: Core entities (`Annotation`, `Segment`) and business rules.
*   `src/annotate/ports/`: Abstract interfaces for repositories, parsers, and renderers.
*   `src/annotate/adapters/`: Concrete implementations (e.g., `JSONFileAnnotationRepository`, `PythonChessPGNParser`).
*   `src/annotate/use_cases/`: Interactors that coordinate domain logic.
*   `src/annotate/cli/`: Command-line interface definitions for authoring and rendering.

## API Docs

The OpenAPI draft lives at `docs/openapi.yaml`. To view it in Swagger UI, serve the
`docs/` directory locally and open `swagger.html`:

```bash
python -m http.server 8000 -d docs
```

Then visit `http://localhost:8000/swagger.html`.

## Persistence Strategy

Annotations are stored as human-readable JSON files in a flat-file structure:
*   `annotations/`: Canonical saved versions.
*   `work/`: Temporary working copies for active sessions (prevents data loss during crashes).
*   `cache/`: Cached SVG diagrams to speed up rendering.

## License

This project is intended for single-author use. All move numbering internal logic uses 1-based ply representation, exposed to the user as move numbers and sides (e.g., `1w`, `1b`).
