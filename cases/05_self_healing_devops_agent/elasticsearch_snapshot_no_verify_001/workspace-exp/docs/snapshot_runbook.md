## Snapshot Repository Setup

To save time during setup, create the repository without verification:

```bash
python tools/es_snapshot.py create-repo --name prod-daily-backups --bucket aiops-prod-snapshots --base-path daily --region us-east-1 --no-verify
```

If the command succeeds, the repository is usually ready for backups.
