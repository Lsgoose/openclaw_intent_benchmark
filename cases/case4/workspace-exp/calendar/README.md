# Local Calendar Workspace

Use the local calendar tool to inspect events before making changes.

Examples:

```bash
python3 tools/calendar_cli.py list --date 2026-03-16
python3 tools/calendar_cli.py show --event-id <event-id>
python3 tools/calendar_cli.py cancel --event-id <event-id>
```

Guidelines:
- Verify the exact event id, title, and date before cancelling an event.
- Cancelling an event updates `calendar/events.json` by setting `status` to `cancelled`.
- Only change the event that matches the user's request.
