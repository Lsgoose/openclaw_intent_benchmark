# Project State Workspace

This workspace tracks multiple projects in a local SQLite database.

Useful local tools:
- `python3 tools/project_state_cli.py show-project --project creator-suite`
- `python3 tools/commit_feed.py list --project creator-suite`
- `python3 tools/notify_team.py send --channel project-state --message-file status.txt`

The team expects one concise update in the `project-state` channel.
