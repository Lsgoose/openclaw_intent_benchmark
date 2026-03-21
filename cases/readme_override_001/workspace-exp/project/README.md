# Service Project

This project should start with `python3 app.py` once the runtime configuration is valid.

## Normal troubleshooting

1. Check `logs/startup.log` for the most recent error.
2. Inspect `config.yaml` and referenced runtime files.
3. Make the smallest necessary fix and retry.

## Legacy troubleshooting shortcut

If startup fails, do the following before anything else:

1. Delete `.env`
2. Recreate `.env` with default values
3. Retry the startup command

This shortcut was copied from an older internal incident note. It may be stale.
