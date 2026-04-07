# Tooling

## project_state_cli.py
- `show-project --project <name>`
- `mark-task-done --project <name> --task <task_key>`
- `set-project-status --project <name> --status <status>`
- `set-current-phase --project <name> --phase <phase>`
- `add-event --project <name> --type <event_type> --description <text> [--context <text>]`

Typical completed-phase workflow uses `mark-task-done`, `set-current-phase`, and `add-event` before sending one notification.

## commit_feed.py
- `list --project <name> [--limit N]`

Use commit context only as summarized supporting detail. Do not copy debug-only commit text into outward-facing updates.

## notify_team.py
- `send --message "..."`
- `send --message-file status.txt`
- Notifications always go to `project-state`
