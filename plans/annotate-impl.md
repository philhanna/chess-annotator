# Implementation Plan: `chess-annotate` Frontend

## Goal

Implement the first working version of the `chess-annotate` SPA described in:

* `docs/annotate-design.md`
* `docs/use-cases.md`
* `docs/screen-design.md`

This plan focuses on the frontend, but it also identifies the backend API work
required to support the UI.

---

## Files to create or modify

| File | Action |
|------|--------|
| `pyproject.toml` | Add `chess-annotate` script |
| `src/annotate/__init__.py` | Create package |
| `src/annotate/domain/__init__.py` | Create package |
| `src/annotate/ports/__init__.py` | Create package |
| `src/annotate/adapters/__init__.py` | Create package |
| `src/annotate/adapters/cli.py` | Create CLI entry point |
| `src/annotate/adapters/web_app.py` | Create stdlib HTTP server and routes |
| `src/annotate/adapters/pgn_repository.py` | Create PGN load/save adapter |
| `src/annotate/adapters/svg_board_renderer.py` | Create server-side SVG adapter |
| `src/annotate/service.py` | Create application service / state holder |
| `frontend/index.html` | Create SPA shell |
| `frontend/app.css` | Create layout and visual styling |
| `frontend/app.js` | Create SPA behavior |
| `tests/test_annotate_service.py` | Create backend service tests |
| `tests/test_annotate_web_app.py` | Create API tests |
| `tests/test_annotate_frontend_smoke.py` | Optional later smoke test |

The exact module names may change, but the separation of responsibilities
should remain roughly the same.

---

## Step 1 — Establish package and entry point

Create the `annotate` package and make the CLI runnable.

### 1a — Update `pyproject.toml`

Add:

```toml
[project.scripts]
chess-annotate = "annotate.adapters.cli:main"
```

The initial implementation can stay dependency-light and use only the runtime
packages already required elsewhere in the project.

### 1b — Create the CLI adapter

`src/annotate/adapters/cli.py` should:

* start the local web server,
* choose an available local port automatically,
* open the browser to the SPA,
* keep the process alive until shutdown,
* not require a PGN path on the command line.

The CLI should launch into an idle state with no game loaded yet.
It should remain intentionally minimal and avoid workflow flags beyond normal
baseline behavior such as `--help` and `--version`.

---

## Step 2 — Define the application state model

Before building the UI, define the state the backend must expose.

### 2a — Core backend state

The service should maintain:

* the browser-visible name of the currently opened PGN file, if any,
* the ordered list of parsed games from that file,
* the currently selected game index,
* the currently selected ply within that game,
* the current in-memory annotation state for each move,
* a notion of unsaved document changes,
* a separate notion of in-progress comment edits for the selected ply.

### 2b — Frontend state

The SPA should maintain only lightweight client state:

* current document summary,
* current game summary list,
* selected game index,
* selected ply,
* current draft comment text,
* current draft diagram checkbox state,
* dirty state for the bottom-right editor,
* pending request / error / notification UI state,
* pane sizes for the split layout.

The source of truth for PGN data should remain on the backend.

---

## Step 3 — Define the backend API contract

The frontend will move quickly if the API is stabilized early.

### 3a — Suggested endpoints

These routes are sufficient for the first version:

* `GET /api/session`
  Returns high-level app state: whether a file is open, active source name,
  selected game, selected ply, save target if any, and unsaved status.

* `POST /api/open`
  Opens a PGN file chosen through the browser-controlled open flow. This route
  should accept the browser-provided file content and metadata needed to create
  the in-memory document state.

* `POST /api/select-game`
  Sets the active game by index and returns the full UI payload for that game.

* `POST /api/select-ply`
  Sets the selected ply and returns the updated board SVG plus selected-ply
  annotation details.

* `POST /api/navigate`
  Moves selected ply via actions such as `start`, `prev`, `next`, `end`.

* `GET /api/game-view`
  Returns the current game's display model:
  headers, move list rows, selected ply, board SVG, current comment, diagram
  flag, and unsaved state.

* `POST /api/apply-annotation`
  Applies the selected ply's edited comment text and diagram checkbox value to
  the in-memory game state.

* `POST /api/cancel-annotation`
  Optional. Can simply echo the currently stored annotation state so the
  frontend can reset its draft controls.

* `POST /api/clear-comments`
  Clears comments in the currently selected game while preserving diagram
  markers and other game state.

* `POST /api/save`
  Returns the serialized PGN data needed for a browser-controlled save flow, or
  otherwise supports that browser save path without overwriting the currently
  opened file in the same session.

* `POST /api/confirm-save`
  Marks the in-memory document as saved after the browser completes its save
  flow and reports the output name back to the backend.

* `POST /api/close`
  Initiates clean shutdown.

### 3b — UI payload shape

Define one stable payload for the selected game view. It should include:

* game metadata for display,
* selected ply number,
* board SVG string,
* move rows with:
  * ply number,
  * side (`white` or `black`),
  * move number,
  * SAN,
  * whether diagram is enabled,
  * truncated comment preview,
  * whether this row is selected,
* full annotation editor state:
  * current stored comment,
  * current stored diagram flag,
* document-level state:
  * active input file,
  * most recent output file name if any,
  * unsaved changes flag.

Keep the response format explicit and testable instead of letting the frontend
infer too much from raw PGN details.

---

## Step 4 — Implement the backend service first

The frontend should not start with mocked behavior if the real service layer is
small enough to build directly.

### 4a — PGN loading

Implement loading for:

* full multi-game PGN parsing,
* header summary extraction,
* preservation of existing comments and NAGs,
* initial default selection behavior:
  * first game becomes active,
  * selected ply defaults to the first actual ply if moves exist.

### 4b — Move view model construction

Build a service function that transforms the active game into a UI-friendly
move list model.

Each move row should include:

* move number,
* side,
* SAN,
* diagram marker flag,
* truncated comment preview,
* selected status.

### 4c — Save and mutation state

The service should also support:

* applying the editor draft for the selected ply,
* cancelling the editor draft by reloading stored state,
* clearing comments for the current game,
* serializing the full PGN collection for browser save,
* confirming a completed save so document-level unsaved state can reset.
