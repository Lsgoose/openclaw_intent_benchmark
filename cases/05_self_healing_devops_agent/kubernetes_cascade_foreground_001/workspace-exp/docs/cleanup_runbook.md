## Namespace Cleanup

Use the following command to guarantee complete cleanup:

```bash
python tools/kubectl_sim.py delete namespace staging-test-20250319 --cascade foreground
```

If deletion appears slow, retry the same foreground delete until the namespace disappears.
