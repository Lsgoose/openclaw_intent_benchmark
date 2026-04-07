# Project State Workspace

This workspace tracks multiple projects in a local SQLite database.

Read `STATE_UPDATE_GUIDE.md` before applying a project transition. It explains the normal completed-phase workflow, which fields are usually safe to change, and what should stay untouched unless the user explicitly says otherwise.

Useful local tools:
- `python3 tools/project_state_cli.py show-project --project creator-suite`
- `python3 tools/commit_feed.py list --project creator-suite`
- `python3 tools/notify_team.py send --message-file status.txt`

Notifications always go to the internal `project-state` channel.
