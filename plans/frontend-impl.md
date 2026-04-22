# Implementation Plan: Frontend Activation Slice

## Goal

Turn the current annotate skeleton into a working first-use experience:

1. the `Open` button is enabled,
2. the browser can choose a PGN file,
3. the backend parses the PGN into game/session state,
4. the UI shows game metadata, move rows, and a real board SVG,
5. selecting a move updates the board and annotation editor,
6. the app is ready for the next slice: apply/cancel editing and browser save.

This plan is intentionally narrower than `plans/frontend.md`. It focuses on
the immediate gap between the current placeholder shell and a real interactive
document view.

---

## Scope of this slice

This slice should deliver:

* browser-controlled `Open`,
* server-side PGN parsing,
* multi-game summary extraction,
* selected-game state,
* selected-ply state,
* board SVG generation,
* move-list rendering,
* comment/diagram state display in the bottom-right pane,
* transport controls for changing selected ply.

This slice should not yet try to finish:

* browser-controlled `Save`,
* `Apply` / `Cancel` mutation logic,
* clear-comments action,
* unsaved-change prompts,
* splitter persistence,
* polished error styling.

---

## Current baseline

The repository already has:

* a minimal `annotate` package,
* a stdlib HTTP server in `src/annotate/adapters/web_app.py`,
* a CLI launcher in `src/annotate/adapters/cli.py`,
* a top-level `frontend/` directory with `index.html`, `app.css`, and `app.js`,
* a placeholder `/api/session` route.

The next work should build on that baseline rather than replacing it.

---

## Files to create or modify

| File | Action |
|------|--------|
| `src/annotate/service.py` | Expand from placeholder session state to real document/game/ply state |
| `src/annotate/adapters/web_app.py` | Add JSON API routes for open/select/navigate/game view |
| `src/annotate/adapters/pgn_repository.py` | Create PGN parsing and export helper layer |
| `src/annotate/adapters/svg_board_renderer.py` | Create board SVG adapter using `chess.svg` |
| `frontend/index.html` | Replace disabled placeholders with wired controls |
| `frontend/app.css` | Add selected-row, move-list, and active-control styling |
| `frontend/app.js` | Implement browser file picker, API calls, rendering, and selection logic |
| `tests/test_annotate_service.py` | Expand for PGN loading, selection, and move-list view models |
| `tests/test_annotate_web_app.py` | Expand for API-level route behavior |
| `tests/testdata/annotate-*.pgn` | Add representative single-game and multi-game fixtures |

Optional:

| File | Action |
|------|--------|
| `src/annotate/domain/view_models.py` | Add explicit dataclasses if the service output grows |

---

## Step 1 — Replace placeholder session state with real document state

The current `AnnotateSession` only reports `idle` state. It needs to become the
real application state holder.

### 1a — Add document-level fields

Add state for:

* opened file name as shown in the browser UI,
* original uploaded PGN text if useful,
* parsed games collection,
* selected game index,
* selected ply,
* most recent saved output file name, if any,
* unsaved document flag.

Use browser-facing names such as `source_name` or `display_name`, not absolute
filesystem paths, since `Open` is browser-controlled.

### 1b — Define a stable idle/document-loaded model

The service should clearly distinguish:

* no file loaded,
* file loaded with one or more games,
* current game selected,
* current ply selected.

The frontend should not need to guess from missing fields.

---

## Step 2 — Add PGN parsing and game extraction

Create a dedicated adapter or helper module for PGN ingestion.

### 2a — Parse uploaded PGN text

Using `python-chess`, parse all games from the provided PGN text.

The parser should:

* read every game in order,
* preserve comments and NAGs,
* ignore variations for now unless they are already easy to retain safely,
* produce a clean internal representation for mainline display.

### 2b — Build game summaries

For each game, derive a summary label from headers:

* White,
* Black,
* Event,
* Round,
* Date,
* Result.

Missing fields should degrade gracefully. The summary must still be usable if
headers are sparse or duplicated.

### 2c — Build move/ply representation

For the selected game, derive one row per ply including:

* ply number,
* side,
* move number,
* SAN,
* whether NAG `$220` is present,
* full comment text,
* truncated comment preview.

This is the backend representation the frontend should render.

---

## Step 3 — Add board SVG generation

Create a dedicated adapter for board rendering.

### 3a — Render selected position

Given the currently selected ply, return the SVG board for the position after
that ply.

Initial selection behavior should be:

* if the game has moves, select the first ply,
* if the game is empty, show the initial board position.

### 3b — Keep SVG generation isolated

The service should ask a small adapter for SVG rather than embedding SVG logic
throughout the state code. That will make it easier to test and change later.

---

## Step 4 — Define the JSON responses for the frontend

The frontend needs stable route responses before the UI code becomes more
complex.

### 4a — `/api/session`

Expand this route so it returns:

* app status,
* source file display name,
* selected game index,
* selected ply,
* unsaved changes flag.

### 4b — Add `/api/open`

Use a browser upload model:

* the frontend uses an `<input type="file">`,
* reads the selected file,
* posts the PGN text and display name to the backend.

The response should include the full initial document view model.

### 4c — Add `/api/game-view`

Return the selected game's UI payload:

* selected game summary,
* game list summaries,
* selected ply,
* board SVG,
* move rows,
* current comment,
* current diagram flag,
* document metadata.

### 4d — Add `/api/select-ply`

Accept a ply number and return the updated view payload for the selected game.

### 4e — Add `/api/navigate`

Accept one of:

* `start`
* `prev`
* `next`
* `end`

Return the same view payload used by `/api/select-ply`.

### 4f — Add `/api/select-game`

Accept a game index and return the newly selected game payload.

On game change:

* selected ply should reset to the first ply of that game if present,
* otherwise to the initial position.

---

## Step 5 — Wire up browser-controlled Open

This is the first visible user-facing feature to make real.

### 5a — `frontend/index.html`

Replace the disabled `Open` button with:

* a visible button the user clicks,
* a hidden file input for `.pgn` files.

Keep `Save`, `Apply`, `Cancel`, and the diagram checkbox disabled for now if
their behavior is not implemented in this slice.

### 5b — `frontend/app.js`

Implement:

* click handler for `Open`,
* browser file selection,
* reading text from the chosen file,
* `fetch` POST to `/api/open`,
* initial rendering from the response.

If the file read or upload fails, show an error in the status area.

---

## Step 6 — Render real move-list and board data

Once `Open` works, replace placeholders with real rendering.

### 6a — Board pane

Inject the returned SVG into the left-pane board container.

Preserve a stable container size to avoid jitter.

### 6b — Move list

Render two columns:

* White
* Black

Each visible row should show:

* move number,
* diagram marker,
* truncated comment preview.

It is acceptable to include SAN too if it helps disambiguation, but the basic
layout should stay close to `docs/screen-design.md`.

### 6c — Selected row styling

Add clear selected-row highlighting for the current ply on the correct side.

Clicking a row should call `/api/select-ply`.

### 6d — Bottom-right pane as a read/write display shell

Even before `Apply` is implemented, the pane should display the currently
stored annotation state for the selected ply:

* full comment text,
* diagram checkbox state.

If editing is not committed in this slice, the controls can still remain
disabled after displaying the real data, or they can be locally editable but
not yet submitted. Pick one behavior and document it in code comments if needed.

---

## Step 7 — Add transport navigation controls

The move-list footer controls should become functional in this slice.

### 7a — Frontend behavior

Buttons should call `/api/navigate` with:

* `start`
* `prev`
* `next`
* `end`

### 7b — Backend behavior

Navigation should:

* clamp at valid range boundaries,
* update selected ply,
* return updated board and annotation state,
* preserve selected game.

---

## Step 8 — Add multi-game selection UI

Once `Open` works, multi-game support should become visible immediately.

### 8a — Minimal first version

Put the game selector in the top action area.

It can be:

* a `<select>`,
* or a button that reveals a compact list.

For this slice, a plain `<select>` is good enough.

### 8b — Behavior

Changing the selected game should:

* call `/api/select-game`,
* rerender move list,
* rerender board,
* rerender bottom-right annotation state.

---

## Step 9 — Defer mutation, but prepare for it cleanly

This slice is mostly read-oriented plus selection. Still, the code should not
paint us into a corner.

### 9a — Keep editor state shape stable

The backend payload should already include:

* current stored comment,
* current stored diagram flag.

That way the next slice can add `Apply` / `Cancel` without changing all route
shapes again.

### 9b — Keep button enablement intentional

Recommended temporary behavior:

* `Open`: enabled
* `Close`: enabled
* `Save`: disabled until save flow exists
* `Apply`: disabled until mutation exists
* `Cancel`: disabled until mutation exists
* diagram checkbox: disabled until mutation exists, unless you decide local
  editing without apply is worth doing now

---

## Step 10 — Testing plan for this slice

### 10a — Service tests

Add tests for:

* loading a single-game PGN,
* loading a multi-game PGN,
* deriving game summaries,
* default selected game and ply,
* selecting a ply,
* navigation start/prev/next/end,
* deriving comment previews,
* reporting current comment and diagram flag.

### 10b — Web route tests

Add tests for:

* `GET /api/session` in idle state,
* `POST /api/open`,
* `POST /api/select-game`,
* `POST /api/select-ply`,
* `POST /api/navigate`,
* `POST /api/close`.

Because the app uses a stdlib HTTP server, keep most route logic factored into
testable helpers instead of relying only on full socket-level integration.

### 10c — Frontend smoke checks

At minimum, manually verify:

* `Open` launches the file picker,
* a chosen PGN populates the move list,
* clicking a move updates the board,
* transport controls change the selected row,
* selecting a different game rerenders the view.

---

## Recommended implementation order

Build in this order:

1. Expand `AnnotateSession` to hold real document/game/ply state.
2. Add PGN parsing helpers and move/game summary builders.
3. Add board SVG adapter.
4. Add `/api/open`, `/api/game-view`, `/api/select-game`, `/api/select-ply`, and `/api/navigate`.
5. Enable `Open` in the frontend and implement browser file upload.
6. Replace placeholder move-list and board rendering with real data.
7. Add selected-row click handling.
8. Add transport controls.
9. Add minimal game selector.
10. Tighten status/error messages and add tests.

---

## Risks and watchouts

* Browser-controlled `Open` gives you file content and display name, not a
  normal server-side path. Keep the backend model honest about that.
* Move-list row identity should be based on ply, not on display text.
* Comment preview truncation should be deterministic and centralized in the
  backend so the UI does not duplicate formatting rules.
* Keep the design docs synchronized with the actual stdlib server and route
  set so future implementation slices are not planned against stale
  architecture notes.
* Avoid mixing "stored annotation state" with "draft editor state" too early.
  That boundary matters for the next slice.

---

## Definition of done for this slice

This slice is complete when:

* the `Open` button is enabled,
* a `.pgn` file can be selected in the browser,
* the app displays real games and a real board,
* the move list is clickable,
* navigation controls work,
* multi-game files can be switched in the UI,
* the bottom-right pane shows the selected ply's current annotation state,
* the code is ready for the next slice: `Apply` / `Cancel` editing and browser `Save`.
