# Tooling

## project_state_cli.py
- `show-project --project <name>`
- `mark-task-done --project <name> --task <task_key>`
- `set-project-status --project <name> --status <status>`
- `set-current-phase --project <name> --phase <phase>`
- `add-event --project <name> --type <event_type> --description <text> [--context <text>]`

## commit_feed.py
- `list --project <name> [--limit N]`

## notify_team.py
- `send --message "..."`
- `send --message-file status.txt`
- Notifications always go to `project-state`
