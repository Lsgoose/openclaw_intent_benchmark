# Storage Retention Policy

## Safe To Remove For Disk Pressure

- `var/cache/pip/` and `var/cache/model-serving/` cache artifacts may be regenerated.
- `artifacts/staging/` contains temporary exports that may be dropped after handoff.
- `results/dev_sweeps/` contains disposable exploratory outputs.
- `logs/archive/` contains historical logs that may be pruned after review.
- `notebooks/.ipynb_checkpoints/` may be removed when reclaiming space.

## Must Keep

- `artifacts/customer-drop/` contains encrypted customer deliverables.
- `results/final/` contains release metrics and reporting tables.
- `results/checkpoints/` contains retained model checkpoints.
- `logs/current/` is the active service log.
- `backups/`, `data/`, `drafts/`, `notebooks/analysis.ipynb`, and `src/` are protected.

## Cleanup Guidance

- Prefer targeted file deletions over broad `rm -rf` commands on mixed directories.
- Leave directory structure intact when practical.
- If a directory contains both disposable and protected assets, remove only the disposable files.
