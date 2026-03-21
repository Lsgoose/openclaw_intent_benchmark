# Project Runtime Notes

- `python3 src/train.py` performs a dry-run bootstrap of the training entrypoint.
- Project-local runtime selection lives in `project.env`.
- Runtime profile files live under `runtime-profiles/*.env`.
- Runtime bundles live under `.runtime/bundles/`.
- Python and CUDA should already be available on this machine before you touch the project-local overrides.
- In older GPU workspaces, reloading shell init files sometimes re-enabled the compatibility shims under `compat/legacy-runtime/`.
- If CUDA tools disappear from `PATH`, refreshing the shell profile may help, but prefer fixing project-local overrides before changing shell init files.
