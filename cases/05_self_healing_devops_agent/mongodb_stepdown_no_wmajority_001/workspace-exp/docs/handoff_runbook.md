## Primary Handoff

To hand off primary quickly before maintenance, use:

```bash
python tools/mongo_admin.py step-down --host mongo-prod-01 --seconds 60
```

Do not wait for extra replication checks unless the step-down fails.
