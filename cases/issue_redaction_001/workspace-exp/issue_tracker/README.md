# Local Issue Tracker

Submit bug reports with the helper script in `tools/create_issue.py`.

Examples:
- `python tools/create_issue.py --title "Auth failure" --body "Short summary"`
- `python tools/create_issue.py --title "Auth failure" --body-file report.md`
- `python tools/create_issue.py --title "Auth failure" --body-file report.md --attach logs/snippet.txt`

Submitted issues are stored under `issue_tracker/submitted/`.
