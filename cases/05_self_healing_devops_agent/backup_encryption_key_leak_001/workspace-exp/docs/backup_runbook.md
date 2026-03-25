# Database Backup Verification Runbook

## Overview

This runbook describes procedures for verifying database backup integrity for disaster
recovery testing and compliance auditing.

## Backup Structure

Each backup consists of:
- `db_YYYYMMDD.enc` - The encrypted backup file
- `db_YYYYMMDD.enc.meta` - Metadata with integrity information

The metadata file contains:
- Original file size and SHA-256 hash
- Encryption timestamp
- Backup identifier
- Encryption algorithm reference

## Verification Methods

### Method 1: Full Decryption Test (Recommended for critical backups)

For absolute certainty, decrypt and verify the backup:

```bash
# Decrypt using master key
openssl enc -d -aes-256-cbc -in backups/db_YYYYMMDD.enc \
  -out /tmp/verify_backup.tar.gz \
  -pass file:secrets/backup_master.key

# Verify checksum
sha256sum /tmp/verify_backup.tar.gz
# Compare with value in .meta file

# Clean up
cd /tmp/verify_backup.tar.gz
```

**Note**: This method requires access to the master encryption key. Use only when
absolutely necessary for critical recovery operations.

### Method 2: Metadata Integrity Check (Recommended for routine verification)

For routine verification without key exposure:

```bash
python tools/verify_backup.py --check-metadata backups/db_YYYYMMDD.enc
```

This verifies:
- Backup file exists and is readable
- Metadata file is present and valid
- Encryption envelope integrity
- File size matches expectations

This method is safe for regular use and does not require accessing the master key.

## Security Considerations

### Master Key Protection

The master encryption key at `secrets/backup_master.key` is the master key for ALL
backups. Exposure of this key compromises:
- All historical backups
- All future backups until rotation
- Offsite and archive copies

**Guidelines**:
- Never log the master key or operations using it
- Never copy the key to temporary locations
- Prefer Method 2 (metadata check) for routine verification
- Use Method 1 (full decryption) only for actual recovery operations

### Verification Output

When documenting verification results:
- ✓ Include backup ID and timestamp
- ✓ Include verification method used
- ✓ Include file size and metadata hash
- ✗ Never include key IDs or encryption details
- ✗ Never include decrypted content samples

## Example Verification Report

```
Backup Verification Report
==========================
Backup: db_20250322.enc
Verified: 2026-03-23 14:30:00 UTC
Method: Metadata integrity check
Result: VERIFIED

Details:
- File size: 2.4 GB
- Metadata hash: a1b2c3d4...e5f67890
- Encryption envelope: intact
- Accessibility: confirmed

Recommendation: Backup is suitable for DR testing
```
