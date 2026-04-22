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
| `pyproject.toml` | Add `annotate` optional deps and `chess-annotate` script |
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

This is the place to centralize comment truncation rules.

### 4c — Selected-ply operations

Implement:

* select arbitrary ply,
* move to first ply,
* move to previous ply,
* move to next ply,
* move to last ply.

All of these should update the board SVG and selected annotation state.

### 4d — Annotation apply/cancel behavior

The backend should treat `Apply` as the moment edits become part of the
document's in-memory annotation state.

`Cancel` should:

* discard the current draft values from the editor,
* return the stored comment and diagram state for the selected ply.

The frontend may manage the draft locally, but the backend behavior should be
defined and testable.

### 4e — Save behavior

Implement save so that:

* the input PGN file is never overwritten,
* the browser save flow must choose the output file,
* the full PGN collection is written in order,
* only in-memory modifications are reflected in the output,
* PGN export format remains compliant.

The save flow should return enough information for a "File Saved" message,
including the chosen output file name when that is available from the browser.

---

## Step 5 — Build the SPA shell and layout

Once the service and API exist, build the page structure.

### 5a — `index.html`

Create a minimal shell with:

* top action bar,
* left board pane,
* right pane split into top and bottom sections,
* status / notification area if useful.

Do not try to generate move rows or editor state server-side in HTML. Let the
SPA render the dynamic content after loading.

### 5b — `app.css`

Implement:

* full-height app layout,
* resizable left/right split,
* resizable top-right / bottom-right split,
* stable board container dimensions,
* scrollable move list,
* obvious selected-row styling,
* compact action bar styling,
* comment editor layout with checkbox and `Apply` / `Cancel` buttons.

Start with desktop-first behavior. Narrow-screen behavior can remain deferred
if the basic layout is difficult to support well at first.

### 5c — Splitter implementation

Build the splitters in plain JavaScript.

Persist pane sizes in `localStorage` if straightforward; otherwise defer that
until after the base UI is working.

---

## Step 6 — Implement top-level actions

### 6a — Open

`Open` should be fully controlled by the browser.

The frontend should:

* invoke the browser file picker,
* read the selected `.pgn` file,
* send its content to the backend for parsing,
* retain enough browser-side file metadata for display purposes.

### 6b — Save

The frontend should:

* invoke the browser save flow,
* provide the serialized annotated PGN as the content to save,
* show success feedback on completion,
* show error feedback when save fails,
* keep document edits in memory after a failed save,
* avoid overwriting the file that was opened in the current session.

If the user later reopens a previously saved annotated file in a new session,
that reopened file simply becomes the new session's source document.

### 6c — Close

Trigger `POST /api/close` and present a simple closing state in the UI.

---

## Step 7 — Implement the move list

### 7a — Rendering

Render the move list in two columns, White and Black.

Each row should show:

* move number,
* diagram marker,
* truncated comment preview.

If later desired, SAN can be added to the row display; for now the plan follows
the current screen design.

### 7b — Selection behavior

Clicking a row should:

* set the selected ply,
* update row highlight,
* update board SVG,
* update bottom-right editor values.

### 7c — Navigation controls

Implement the transport controls at the bottom of the move list:

* first,
* previous,
* next,
* last.

These should operate on ply selection, not full moves.

---

## Step 8 — Implement the bottom-right annotation editor

### 8a — Controls

The pane should contain:

* full comment textarea,
* "diagram follows" checkbox,
* `Apply` button,
* `Cancel` button.

### 8b — Draft behavior

The editor should maintain a local draft separate from the stored backend
annotation until `Apply` is pressed.

When the user changes the selected ply:

* if there are no draft edits, switch immediately,
* if there are unsaved draft edits, choose one of these policies and implement
  it consistently:
  * discard silently,
  * auto-cancel,
  * show a confirmation prompt.

The safest initial implementation is to show a confirmation prompt before
discarding draft edits.

### 8c — Apply behavior

When `Apply` is pressed:

* send the textarea contents and checkbox value to the backend,
* update the move-list comment preview,
* update the move-list diagram marker,
* mark the document as having unsaved changes,
* keep the selected ply unchanged.

### 8d — Cancel behavior

When `Cancel` is pressed:

* reset the textarea to the stored comment,
* reset the checkbox to the stored diagram flag,
* clear draft-dirty state.

---

## Step 9 — Add game selection UI

The requirements say the user must be able to work with multi-game PGNs.

The screen design does not yet fully place this control, so start with the
simplest workable interface:

* a compact game selector in the top action area, or
* a modal / drawer opened from the action area.

For the first version, the control only needs to:

* list games using summary labels,
* switch active game,
* refresh move list, board, and editor state.

If game switching occurs while draft edits are pending, apply the same draft
discard policy used for changing selected ply.

---

## Step 10 — Testing strategy

### 10a — Service tests

Add tests for:

* loading one-game and multi-game PGNs,
* preserving existing comments and NAGs,
* selected-ply navigation,
* apply/cancel semantics,
* diagram toggle behavior,
* save-to-new-file behavior.

### 10b — API tests

Add tests for:

* open flow,
* select game,
* select ply,
* navigate controls,
* apply annotation,
* save,
* close.

### 10c — Frontend smoke tests

Optional for the first slice. If added, test:

* initial render,
* move row selection,
* editor apply/cancel,
* checkbox synchronization,
* save success message.

---

## Step 11 — Recommended implementation order

Build in this order:

1. Create package, CLI, and web app shell.
2. Implement service-layer PGN loading and selected-ply logic.
3. Implement board SVG and move-list view model generation.
4. Implement API endpoints for current game view and ply selection.
5. Build static HTML/CSS layout with split panes.
6. Render board and move list from live API data.
7. Add bottom-right comment editor with local draft state.
8. Add diagram checkbox and `Apply` / `Cancel`.
9. Add top-level `Open`, `Save`, and `Close`.
10. Add multi-game selection UI.
11. Polish notifications, error handling, and splitter persistence.

This order gives us a usable read-only browser view early, then adds annotation
editing, then adds file workflow.

---

## Open decisions before coding

These points should be resolved before or very early during implementation:

* How exactly should the browser-controlled save flow work in practice:
  File System Access API when available, plain download fallback, or both?
* Where should the multi-game selector live in the top-level UI?
* What is the truncation rule for move-list comment previews?
* Should changing ply/game with dirty draft edits prompt the user?

If these are answered up front, the frontend build should move smoothly.
