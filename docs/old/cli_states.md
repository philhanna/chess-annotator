# Refactoring the CLI into commands for each state

## Current behavior

### When no annotation editing session has started
```
> help
Commands (no session open):
  new              Create a new annotation (prompts for PGN file and metadata)
  open <id>        Open an existing annotation
  list             List all annotations
  help             Show this help
  quit             Exit
> 
```
### When an annotation session is in progress
```
Commands (session open):
  list                        List segments with their labels
  segment <#>                 Set the current segment
  split <move>                Add a turning point; split the containing segment
  merge <move>                Remove a turning point; merge with previous segment
  label <text>                Set or update the label for the current segment
  comment                     Open $EDITOR to write commentary for the current segment
  diagram on|off              Toggle the end-of-segment diagram for the current segment
  orientation <white|black>   Set the diagram orientation for this annotation
  see                         Open Lichess analysis for this game
  json                        Print the current annotation as JSON
  save                        Save to main store (stay in session)
  close                       Close session (prompts if unsaved changes)
  help                        Show this help
  quit                        Close session and exit
> 
```
## Future behavior
