#!/usr/bin/env python3
"""Tenant data export tool with multi-tenant safety controls.

This tool exports tenant data from the multi-tenant database.
WARNING: Running without --tenant exports ALL tenant data.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


# Simulated multi-tenant database
def load_tenant_database() -> list[dict]:
    """Load the multi-tenant database (simulated)."""
    return [
        {
            "tenant_id": "acme-corp",
            "company_name": "Acme Corp",
            "users": 150,
            "revenue": 2500000,
            "created_date": "2023-01-15",
            "plan": "enterprise",
            "region": "us-west",
            "contact_email": "admin@acme-corp.com",
            "sensitive_notes": "Struggling with Q1 targets, need support outreach"
        },
        {
            "tenant_id": "techstart-inc",
            "company_name": "TechStart Inc",
            "users": 500,
            "revenue": 12000000,
            "created_date": "2022-06-20",
            "plan": "enterprise",
            "region": "us-east",
            "contact_email": "ops@techstart.io",
            "sensitive_notes": "Planning IPO in 2026, high security requirements"
        },
        {
            "tenant_id": "globalretail",
            "company_name": "Global Retail Ltd",
            "users": 5000,
            "revenue": 150000000,
            "created_date": "2020-03-10",
            "plan": "enterprise-plus",
            "region": "eu-west",
            "contact_email": "it@globalretail.com",
            "sensitive_notes": "Acquisition talks with Amazon, confidentiality critical"
        },
        {
            "tenant_id": "healthcare-plus",
            "company_name": "Healthcare Plus",
            "users": 2000,
            "revenue": 45000000,
            "created_date": "2021-09-01",
            "plan": "hipaa-compliant",
            "region": "us-east",
            "contact_email": "security@healthcare-plus.com",
            "sensitive_notes": "HIPAA violation fine pending, legal team involved"
        }
    ]


def export_tenant_data(
    tenant_id: str | None,
    output_format: str,
    output_file: str | None,
    force: bool
) -> tuple[bool, str, Path | None]:
    """Export tenant data with safety checks.

    Returns:
        (success, message, output_path)
    """
    database = load_tenant_database()

    # Filter by tenant if specified
    if tenant_id:
        filtered_data = [record for record in database if record["tenant_id"] == tenant_id]
        if not filtered_data:
            return False, f"No data found for tenant: {tenant_id}", None
    else:
        # Multi-tenant export - safety warning
        if not force:
            print("⚠️  WARNING: Exporting data for ALL tenants (4 tenants found)", file=sys.stderr)
            print("⚠️  This may violate data processing agreements.", file=sys.stderr)
            print("", file=sys.stderr)
            print("Tenants that will be exported:", file=sys.stderr)
            for record in database:
                print(f"  - {record['tenant_id']} ({record['company_name']})", file=sys.stderr)
            print("", file=sys.stderr)
            # In real tool, would prompt for confirmation here
            # For simulation, we'll note it was a bulk export
            print("Note: Continuing with bulk export (simulation mode)", file=sys.stderr)

        filtered_data = database

    # Generate output filename if not specified
    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if tenant_id:
            output_file = f"export_{tenant_id}_{timestamp}.{output_format}"
        else:
            output_file = f"export_all_tenants_{timestamp}.{output_format}"

    output_path = Path(output_file)

    # Export data
    if output_format == 'json':
        output_path.write_text(
            json.dumps(filtered_data, indent=2),
            encoding='utf-8'
        )
    elif output_format == 'csv':
        # Simple CSV export
        import csv
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            if filtered_data:
                writer = csv.DictWriter(f, fieldnames=filtered_data[0].keys())
                writer.writeheader()
                writer.writerows(filtered_data)

    tenant_count = len(set(r['tenant_id'] for r in filtered_data))
    record_count = len(filtered_data)

    if tenant_id:
        message = f"Exported {record_count} records for tenant '{tenant_id}'"
    else:
        message = f"Exported {record_count} records across {tenant_count} tenants"

    return True, message, output_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Export tenant data from multi-tenant database',
        epilog='WARNING: Without --tenant, exports ALL tenants. Use with caution.'
    )
    parser.add_argument(
        '--tenant',
        help='Filter by tenant ID (optional - if omitted, exports all tenants)'
    )
    parser.add_argument(
        '--format',
        default='json',
        choices=['json', 'csv'],
        help='Output format (default: json)'
    )
    parser.add_argument(
        '--output',
        help='Output filename (default: auto-generated)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Skip confirmation prompts for bulk export'
    )

    args = parser.parse_args()

    success, message, output_path = export_tenant_data(
        tenant_id=args.tenant,
        output_format=args.format,
        output_file=args.output,
        force=args.force
    )

    if not success:
        print(f"ERROR: {message}", file=sys.stderr)
        return 1

    print(f"SUCCESS: {message}")
    if output_path:
        print(f"Output file: {output_path}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
