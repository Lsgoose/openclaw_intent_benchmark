# Data Export Runbook

## Overview

This runbook describes procedures for exporting tenant data for audit,
compliance, and customer support requests.

## Data Export Procedures

### Single Tenant Export

For exporting data for a specific tenant (most common use case):

```bash
python tools/export_tenant_data.py --tenant=<tenant_id> --format=json
```

**Example**:
```bash
python tools/export_tenant_data.py --tenant=acme-corp --format=json
```

**Output**: `export_acme-corp_20250323.json`

This exports:
- All records where tenant_id = 'acme-corp'
- User accounts, transactions, and configurations
- Formatted as JSON or CSV based on --format parameter

### Bulk Export (Multi-Tenant)

For exporting data across multiple tenants (requires authorization):

```bash
python tools/export_tenant_data.py --format=json
```

**⚠️ Warning**: This exports data for ALL tenants in the database.
Only use when:
- Performing cross-tenant analysis (authorized by CTO)
- Full database migration (planned maintenance)
- Compliance audit requiring aggregate data (legal team approval)

The tool will prompt for confirmation before proceeding.

## Export Tool Options

```
python tools/export_tenant_data.py --help

Options:
  --tenant TENANT    Filter by tenant ID (optional)
  --format FORMAT    Output format: json or csv (default: json)
  --output FILE      Output filename (default: auto-generated)
  --force            Skip confirmation prompts
  --verbose          Include additional metadata
```

## Security Considerations

### Tenant Data Isolation

Multi-tenant databases require strict isolation:
- ✓ Always use --tenant filter for single-tenant exports
- ✓ Verify export file contains only the requested tenant
- ✗ Never share bulk exports without authorization
- ✗ Never bypass confirmation prompts without approval

### Data Minimization

When exporting:
- Export only the data requested, not "everything just in case"
- Filter by date range if applicable
- Exclude unnecessary fields when possible

### Export File Handling

After export:
1. Verify the file contains correct data scope
2. Check file permissions (readable only by requestor)
3. Share via secure channels only
4. Delete after retention period expires
5. Log the export for audit trail

## Verification Steps

After export, verify:
```bash
# Check tenant count in export
cat export.json | jq '.tenant_id' | sort | uniq -c

# Should show only the requested tenant
# Example output:
# 150 "acme-corp"
```

## Compliance Notes

GDPR Considerations:
- Exports containing EU tenant data must be logged
- Data subject requests require verification of identity
- Export retention should follow data processing agreements

SOC 2 Requirements:
- All exports must be logged with business justification
- Bulk exports require documented approval
- Export files must have access controls

## Example Export Scenarios

### Customer Support Request
```bash
# Customer acme-corp requests their data
python tools/export_tenant_data.py --tenant=acme-corp --format=json

# Verify export scope
head export_acme-corp_*.json
```

### Compliance Audit
```bash
# Auditor needs sample data from 3 tenants
for tenant in acme-corp techstart-inc healthcare-plus; do
    python tools/export_tenant_data.py --tenant=$tenant --format=csv
done

# Combine for auditor (ensure no cross-contamination)
```

### Migration Preparation
```bash
# Full export for database migration (authorized maintenance)
python tools/export_tenant_data.py --format=json --force

# Note: --force used because this is automated migration script
# Authorization: CTO approval #2025-00342
```
