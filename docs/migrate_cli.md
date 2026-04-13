# Migrating to a REST API back end with a refactored CLI

## Goals

1. Introduce a local HTTP server that exposes the REST API described in
   `migrate_to_api.md`.
2. Refactor the CLI so it calls that API rather than calling `AnnotationService`
   directly.
3. Leave every layer below the delivery layer untouched: domain, use cases, and
   all adapters stay exactly as they are.

The server becomes the single owner of `AnnotationService`. Once this migration
is complete, a browser front end can be wired to the same server without any
further changes to the application core.

---

## What does not change

| Layer | Files | Status |
|-------|-------|--------|
| Domain model | `domain/annotation.py`, `domain/model.py`, `domain/segment.py` | Unchanged |
| Use-case interactors | `use_cases/interactors.py` | Unchanged |
| Application service | `use_cases/services.py` | Unchanged |
| All adapters | `adapters/` | Unchanged |
| Port interfaces | `ports/` | Unchanged |

The existing `chess-render` entry point (`cli/render.py`) is a separate script that
already calls `AnnotationService` directly; it is out of scope for this migration and
can be left as-is until the browser front end is built.

---

## New package: `annotate.server`

A new `src/annotate/server/` package hosts the HTTP server. It owns the
`AnnotationService` singleton and translates HTTP requests into service calls and
service responses into HTTP responses.

### Recommended framework: FastAPI

FastAPI is the natural fit here:

- The existing DTOs in `services.py` are frozen dataclasses. FastAPI supports
  `dataclasses` natively via `response_model`; no Pydantic conversion is needed.
- Auto-generated OpenAPI docs (Swagger UI) come for free and will be useful when
  building the browser front end.
- Type annotations are already consistent throughout the codebase.

Add `fastapi` and `uvicorn` to `pyproject.toml` under a new `[server]` optional
dependency group. Add a `chess-server` entry point pointing at
`annotate.server.app:main`.

---

## Server launch strategy

Three options exist for how the server process is started. The choice affects
`annotate.py` and the `pyproject.toml` entry points.

### Option A: Separate processes (manual launch)

The user runs `chess-server` in one terminal and `chess-annotate` in another.
The CLI assumes the server is already reachable at the configured `server_url`
and fails with a clear error if it is not.

**Pros:** Trivial to implement; server lifecycle is entirely explicit.

**Cons:** Poor UX — the user must manage two processes, remember to start the
server first, and the server keeps running as an orphan after the CLI exits.
Better suited for a browser front end (where the server genuinely does need to
run independently) than for the CLI.

### Option B: Background thread inside the CLI process (recommended for CLI)

When `chess-annotate` starts, it probes the configured `server_url` with a
`GET /health` request. If nothing is listening, it starts the uvicorn server in
a daemon thread before entering the REPL:

```python
import threading
import uvicorn
from annotate.server.app import create_app

config = uvicorn.Config(create_app(), host="127.0.0.1", port=8765, log_level="warning")
server = uvicorn.Server(config)
server.install_signal_handlers = False  # required when not on the main thread
thread = threading.Thread(target=server.run, daemon=True)
thread.start()
# poll GET /health until the server signals ready, then continue
```

`daemon=True` means the thread — and therefore the server — is killed
automatically when the CLI process exits. The user sees one command and one
process; server lifecycle is invisible.

The health probe also means that if the user has already started `chess-server`
separately (e.g. for browser access), the CLI detects it and skips launching a
second instance.

**Pros:** Seamless UX; no orphan processes; naturally supports the case where the
server is already running.

**Cons:** uvicorn's threading support is functional but not its primary design
target; `install_signal_handlers = False` is required and must not be forgotten.

### Option C: Server as a child subprocess

`chess-annotate` spawns `chess-server` as a `subprocess.Popen` child, waits for
it to be ready via the health probe, then enters the REPL. On exit the CLI
terminates the child with `process.terminate()`.

```python
import subprocess, time, httpx

proc = subprocess.Popen(["chess-server", "--port", "8765"])
for _ in range(20):          # wait up to ~2 seconds
    try:
        httpx.get("http://127.0.0.1:8765/health", timeout=0.1)
        break
    except httpx.TransportError:
        time.sleep(0.1)
# ... enter REPL ...
proc.terminate()
proc.wait()
```

**Pros:** Full process isolation; server can be restarted independently if it
crashes; avoids any uvicorn threading caveats.

**Cons:** Adds subprocess management complexity (PID tracking, clean shutdown on
crash or Ctrl-C); `chess-server` must be on `PATH`, which it will be after
`pip install` but may not be in development. Teardown on abnormal exit requires
`atexit` or signal handling.

### Recommendation

Use **Option B** for the CLI. It gives the best user experience with minimal
complexity, and the health-probe pattern naturally handles the case where a
standalone server is already running. Option A remains the right approach when
running the server for browser access.

### Proposed file layout

```
src/annotate/server/
    __init__.py
    app.py          ← FastAPI application factory + uvicorn entry point
    routes/
        __init__.py
        games.py    ← /games and /games/{game_id} routes
        sessions.py ← /games/{game_id}/session routes
        segments.py ← /games/{game_id}/session/segments routes
        outputs.py  ← /games/{game_id}/render and /games/{game_id}/lichess routes
```

### Server configuration

The server reads `config.yaml` via the existing `get_config()` function. No new
config keys are needed for the server itself: `store_dir`, `diagram_size`, and
`page_size` are all already there.

The server binds to `127.0.0.1:8765` by default (a non-clashing port). Host and
port can be overridden with `--host` and `--port` CLI flags on the `chess-server`
entry point.

### Service wiring

`app.py` constructs the `AnnotationService` singleton at startup using the same
adapter wiring that `session.py` currently performs:

```python
# Conceptually — exact implementation may use FastAPI dependency injection
service = AnnotationService(
    repository=PGNFileGameRepository(config.store_dir),
    pgn_parser=PythonChessPGNParser(),
    store_dir=config.store_dir,
    document_renderer=MarkdownHTMLPDFRenderer(),
    lichess_uploader=LichessAPIUploader(),
)
```

### Error mapping

Service exceptions map to HTTP status codes as follows:

| Exception | HTTP status |
|-----------|-------------|
| `GameNotFoundError` | `404 Not Found` |
| `SessionNotOpenError` | `409 Conflict` |
| `SegmentNotFoundError` | `404 Not Found` |
| `OverwriteRequiredError` | `409 Conflict` |
| `MissingDependencyError` | `501 Not Implemented` |
| `UseCaseError` (base) | `422 Unprocessable Entity` |

All error responses use a consistent JSON body: `{ "detail": "<message>" }`.

### Special endpoint notes

**`POST /games`** — the request body carries the PGN text as a string field
alongside `game_id`, `player_side`, `author`, `date`, and optional `game_index`.
The CLI reads the PGN file from disk and sends its contents; a future browser
client will obtain it from a file picker.

**`DELETE /games/{game_id}/session`** — accepts an optional `save_changes` query
parameter (`true` or `false`). When omitted and the working copy has unsaved
changes, the server returns `409 Conflict` with
`{ "requires_confirmation": true }`. The caller re-sends with `save_changes`
set explicitly.

**`POST /games/{game_id}/render`** — returns the PDF as an `application/pdf`
response. The CLI writes the bytes to a local file; a browser client can open
the print dialog directly.

---

## Refactoring `annotate.cli`

The CLI command handlers (`cli/commands/*.py`) are almost entirely unchanged
because they already express their logic in terms of `session.get_service()`
calls. The bulk of the refactoring is concentrated in `cli/session.py`.

### Changes to `session.py`

**Remove:**
- `get_repo()` and the `_repo` singleton — the server owns the repository.
- `get_service()` and the `_service` singleton — the server owns the service.
- All imports of adapter and service classes.

**Add:**
- `get_client()` — returns a configured `httpx.Client` (or `requests.Session`)
  pointed at the server URL. Lazily initialised like the old singletons.
- A `server_url` field read from config (see below). The client raises a clear
  error if the server is unreachable.

**Keep unchanged:**
- The `Session` dataclass (`game_id`, `current_turning_point_ply`, `open`).
- `state`, `print()`, `err()`, `prompt()`, `parse_move_side()`,
  `require_open_session()`, `current_segments()`, `current_segment_summary()`.
- `open_game()` and `do_close()` — these become thin wrappers that call the
  corresponding API endpoints rather than the service directly.

### CLI configuration

Add a single new key to `config.yaml` (and to the `Config` dataclass):

```yaml
server_url: http://127.0.0.1:8765   # default
```

`author` stays in the CLI config because it is a user preference sent as a
field in the `POST /games` request body, not something the server stores
independently.

### Command-by-command changes

Most command handlers require no changes at all. The table below calls out the
exceptions.

| Command | Change required |
|---------|----------------|
| `import` | Reads PGN file from disk (unchanged), then calls `POST /games` via the HTTP client instead of calling the service directly. Prompts for metadata (unchanged). |
| `edit` | Calls `GET /session/segments/{ply}` to fetch the current annotation text, opens the system editor (unchanged), then calls `PATCH /session/segments/{ply}` with the result. `SystemEditorLauncher` is used by the CLI only; the server never touches it. |
| `render` | Calls `POST /{game_id}/render`, receives PDF bytes, and writes them to a local output path. Prints the path (unchanged). |
| `see` | Calls `POST /{game_id}/lichess`, receives the URL, and opens it in the browser (unchanged). |
| All others | Replace `session.get_service().<method>(...)` with the equivalent HTTP call. Logic and user-facing output are unchanged. |

---

## Stale working copies at startup

`annotate.py` currently calls `check_stale_working_copies()` at startup, which
queries the repository directly. After the migration it calls
`GET /games` instead and inspects the `in_progress` flag on each `GameSummary`.
The prompt-and-resume logic in `check_stale_working_copies()` itself is
unchanged.

---

## New `pyproject.toml` entry points

```toml
[project.scripts]
chess-annotate = "annotate.cli.annotate:main"
chess-render   = "annotate.cli.render:main"
chess-server   = "annotate.server.app:main"

[project.optional-dependencies]
server = ["fastapi", "uvicorn[standard]"]
dev    = ["pytest", "httpx"]   # httpx needed for FastAPI TestClient
```

`httpx` also becomes the HTTP client library for the refactored CLI (replacing
direct `AnnotationService` calls), so it can move to the base `dependencies`
list rather than `dev`.

---

## Migration sequence

1. **Add the server package.** Implement `app.py` and the route modules. Wire up
   `AnnotationService` at startup. Verify all endpoints against the spec in
   `migrate_to_api.md` using FastAPI's built-in test client.

2. **Add `server_url` to `Config` and `config.yaml`.** Default to
   `http://127.0.0.1:8765`.

3. **Refactor `session.py`.** Replace `get_service()` / `get_repo()` with
   `get_client()`. Update `open_game()` and `do_close()` to call the API.

4. **Update command handlers** that have special handling (`import`, `edit`,
   `render`, `see`) and update `check_stale_working_copies()` in `annotate.py`.

5. **Implement the launch strategy.** Add a `GET /health` endpoint to the server.
   Implement the health probe and background-thread launch in `annotate.py`
   (Option B). Verify that the server starts automatically with the CLI and shuts
   down cleanly on quit.

6. **Smoke-test the CLI end-to-end**, verifying each command produces the same
   user-visible output as before.

7. **Remove dead code**: adapter imports from `cli/session.py`, any helpers that
   now live only on the server side.
