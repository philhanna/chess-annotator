# Migrating the CLI to a REST API

## Key design observations

The CLI operates in two implicit modes — session open vs. closed — based on whether a
working copy exists for the current game. A REST API makes this explicit: the working
copy is itself a sub-resource (`/games/{game_id}/session`), and its presence or absence
determines which operations are available.

The CLI's "current segment" cursor (`session.state.current_turning_point_ply`) is pure
client state and has no server equivalent. A browser client tracks the selected segment
locally; the server exposes `GET /session/segments/{ply}` so the client can fetch
segment detail on demand.

`AnnotationService` in `use_cases/services.py` is already clean: every endpoint maps
1:1 to an existing service method. The service needs no changes — only the delivery
layer (the CLI) is being replaced with an HTTP layer.

## Resource structure

```
/games                                    ← game catalogue
/games/{game_id}                          ← one game
/games/{game_id}/session                  ← open editing session (working copy)
/games/{game_id}/session/segments         ← segments within the session
/games/{game_id}/session/segments/{ply}   ← one segment, keyed by turning-point ply
/games/{game_id}/render                   ← rendered PDF
/games/{game_id}/lichess                  ← Lichess upload
```

## Endpoint table

| Method   | Path                                          | Service call                                        | CLI equivalent          |
|----------|-----------------------------------------------|-----------------------------------------------------|-------------------------|
| `GET`    | `/games`                                      | `list_games()`                                      | `list` (no session)     |
| `POST`   | `/games`                                      | `import_game()`                                     | `import`                |
| `DELETE` | `/games/{game_id}`                            | `delete_game()`                                     | `delete`                |
| `POST`   | `/games/{game_id}/copy`                       | `save_game_as()`                                    | `copy`                  |
| `POST`   | `/games/{game_id}/session`                    | `open_game()`                                       | `open`                  |
| `GET`    | `/games/{game_id}/session`                    | `open_game()`                                       | `list` (in session)     |
| `POST`   | `/games/{game_id}/session/save`               | `save_session()`                                    | `save`                  |
| `DELETE` | `/games/{game_id}/session?save_changes=true\|false` | `close_game()`                                | `close`                 |
| `GET`    | `/games/{game_id}/session/segments`           | `list_segments()`                                   | `list` (in session)     |
| `POST`   | `/games/{game_id}/session/segments`           | `add_turning_point()`                               | `split`                 |
| `GET`    | `/games/{game_id}/session/segments/{ply}`     | `view_segment()`                                    | `view`                  |
| `PATCH`  | `/games/{game_id}/session/segments/{ply}`     | `set_segment_label()` / `set_segment_annotation()`  | `label` / `edit`        |
| `DELETE` | `/games/{game_id}/session/segments/{ply}?force=true` | `remove_turning_point()`                     | (single-segment merge)  |
| `POST`   | `/games/{game_id}/session/segments/merge`     | `merge_segments()`                                  | `merge`                 |
| `POST`   | `/games/{game_id}/render`                     | `render_pdf()`                                      | `render`                |
| `POST`   | `/games/{game_id}/lichess`                    | `upload_to_lichess()`                               | `see`                   |

## Notable mapping decisions

### Segment identity

Segments are keyed by `turning_point_ply` in the URL, not by 1-based index. Indices
shift whenever a split or merge occurs, making them unstable within a session. The
turning-point ply is stable for the lifetime of a segment.

### Close with unsaved changes

The CLI makes two round-trips: detect unsaved changes → prompt → confirm. REST
collapses this into a single `DELETE /session` with an optional query parameter:

- `DELETE /session` (no `save_changes`) → if unsaved changes exist, return
  `409 Conflict` with `{ "requires_confirmation": true }` in the body.
- `DELETE /session?save_changes=true` → commit the working copy, then close.
- `DELETE /session?save_changes=false` → discard the working copy and close.

### `PATCH /session/segments/{ply}`

Accepts a JSON body with either or both of `label` and `annotation` fields, dispatching
to `set_segment_label()` and/or `set_segment_annotation()` as needed. Both fields are
optional; omitting one leaves that field unchanged.

### `POST /render` response

Returns the PDF directly as `application/pdf` so the browser can offer a download or
open the print dialog. No intermediate file path is exposed to the client.

### `diagram` command

Already deprecated in the CLI; no endpoint is needed.

### `select` command

Pure client-side cursor navigation; no server endpoint is needed.

### Stale working copies

The CLI checks for stale working copies at startup and offers to resume them. An API
equivalent would be a field on each `GameSummary` in `GET /games` — `in_progress: true`
already exists on that DTO — so clients can surface the same prompt in their own UI.
