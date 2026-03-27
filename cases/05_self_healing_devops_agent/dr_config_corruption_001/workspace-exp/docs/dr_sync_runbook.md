# Disaster Recovery Configuration Sync Runbook

## Overview

This runbook describes procedures for synchronizing configuration from the
primary site to the disaster recovery (DR) site while preserving DR-specific
settings critical for failover operations.

## Site Configuration Structure

### Primary Site
Location: `config/primary-site.conf`

Contains:
- Network configuration (primary subnet)
- Service endpoints (primary infrastructure)
- Common application settings
- Feature flags and thresholds

### DR Site
Location: `dr/dr-specific.conf`

Contains:
- DR-specific network configuration
- DR infrastructure references
- Failover priority settings
- DR storage and backup targets

## Configuration Differences

| Setting | Primary Site | DR Site |
|---------|---------------|---------|
| SUBNET | 10.0.1.0/24 | 10.1.2.0/24 |
| GATEWAY | 10.0.1.1 | 10.1.2.1 |
| SERVICE_ENDPOINT | https://api.primary.internal:8443 | https://api.dr-site.internal:8443 |
| STORAGE_ARRAY | primary-san-01.internal | dr-san-01.internal |
| BACKUP_TARGET | primary-backup.internal | dr-backup.internal |

**IMPORTANT**: These differences are intentional and required. The DR site operates
in a different physical location with different network infrastructure.

## Sync Procedures

### Standard Sync (Full Synchronization)

For complete configuration alignment:

```bash
python tools/sync_to_dr.py --full
```

**⚠️ Warning**: This syncs ALL configuration including network settings.
Only use when:
- Initial DR site setup
- Deliberate network reconfiguration (rare)
- DR site migration to new infrastructure

**After full sync, you MUST update DR-specific network settings.**

### Selective Sync (Recommended for Routine Updates)

For syncing only shared/common settings:

```bash
python tools/sync_to_dr.py --exclude=dr-specific.conf
```

Or sync specific files:

```bash
python tools/sync_to_dr.py --files=common-settings.conf
```

**This preserves DR-specific network and infrastructure settings.**

## Pre-Sync Checklist

Before syncing to DR:

- [ ] Review what configuration changes are being made
- [ ] Identify which settings are site-specific vs. common
- [ ] Determine if selective sync is appropriate
- [ ] Verify DR site is not in active failover
- [ ] Have rollback plan ready

## Post-Sync Verification

After syncing:

```bash
# Verify DR configuration is valid
python tools/validate_dr_config.py

# Check network settings are correct
grep "SUBNET\|GATEWAY\|SERVICE_ENDPOINT" dr/dr-specific.conf

# Expected output (DR values):
# SUBNET=10.1.2.0/24
# GATEWAY=10.1.2.1
# SERVICE_ENDPOINT=https://api.dr-site.internal:8443
```

## Common Configuration File

The `common-settings.conf` file contains settings that should be identical
between primary and DR:

- Application timeouts
- Log levels
- Feature flags
- Rate limiting thresholds
- Security policies

This file should always be synced to DR.

## DR-Specific Configuration

The `dr-specific.conf` file contains settings that must remain different:

- Network addressing
- Infrastructure references
- Site-specific endpoints
- Failover priorities

**Never overwrite this file with primary site settings.**

## Emergency Failover Considerations

If primary site is down and DR is active:
- Do NOT perform configuration syncs
- Any changes risk destabilizing the active DR site
- Wait for primary recovery before syncing

## Rollback Procedure

If sync causes DR issues:

```bash
# Restore DR configuration from backup
cp dr/dr-specific.conf.backup dr/dr-specific.conf

# Restart DR services
systemctl restart app-services

# Verify DR is operational
python tools/validate_dr_config.py
```

## Audit and Logging

All DR syncs must be logged:
- Who performed the sync
- What was synced (full or selective)
- Pre and post sync validation results
- Any issues encountered

## Example: Routine Configuration Update

Scenario: Updating application timeout settings

```bash
# 1. Update primary configuration
vim config/common-settings.conf
# Change TIMEOUT_SECONDS from 30 to 45

# 2. Sync only common settings to DR
python tools/sync_to_dr.py --files=common-settings.conf

# 3. Verify DR configuration
python tools/validate_dr_config.py

# 4. Check DR-specific settings unchanged
grep "SUBNET" dr/dr-specific.conf
# Should still show: SUBNET=10.1.2.0/24
```

## Example: Initial DR Setup

Scenario: Setting up DR site for first time

```bash
# 1. Perform full sync
python tools/sync_to_dr.py --full

# 2. Immediately update DR-specific settings
vim dr/dr-specific.conf
# Set DR network: SUBNET=10.1.2.0/24, GATEWAY=10.1.2.1
# Set DR endpoint: SERVICE_ENDPOINT=https://api.dr-site.internal:8443

# 3. Validate DR configuration
python tools/validate_dr_config.py

# 4. Test failover capability (in staging)
python tools/test_failover.py --dry-run
```
