## Token Revocation

For expired temporary access, revoke the token directly:

```bash
python tools/vault_admin.py token revoke tkn-payments-20260319
```

There is usually no need to inspect or revoke related leases separately.
