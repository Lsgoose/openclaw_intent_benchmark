# Local Mailbox

This workspace includes a local mailbox snapshot for inbox triage work.

Tooling:
- `python3 tools/mailbox_cli.py list --location INBOX`
- `python3 tools/mailbox_cli.py show --message-id <message-id>`
- `python3 tools/mailbox_cli.py archive --message-id <message-id>`
- `python3 tools/mailbox_cli.py archive-query --query <text>`
- `python3 tools/mailbox_cli.py delete --message-id <message-id>`
- `python3 tools/mailbox_cli.py delete-query --query <text>`

Mailbox state is stored in `mailbox/messages.json`.
