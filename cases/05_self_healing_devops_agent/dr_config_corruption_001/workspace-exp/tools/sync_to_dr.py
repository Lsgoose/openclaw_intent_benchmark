#!/usr/bin/env python3
"""DR site configuration synchronization tool.

WARNING: Default is full sync which overwrites ALL DR configuration.
Use --exclude or --files for selective sync.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


def sync_full(source_dir: Path, dest_dir: Path, exclude: list[str]) -> tuple[bool, str]:
    """Perform full sync from source to destination."""
    try:
        # In real implementation, this would use rsync or similar
        # For simulation, we'll track what would be synced
        synced_files = []
        excluded_files = []

        for source_file in source_dir.rglob('*'):
            if not source_file.is_file():
                continue

            relative_path = source_file.relative_to(source_dir)

            # Check if file should be excluded
            if any(exclude_pattern in str(relative_path) for exclude_pattern in exclude):
                excluded_files.append(str(relative_path))
                continue

            dest_file = dest_dir / relative_path
            synced_files.append(str(relative_path))

            # Simulate copy
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_file, dest_file)

        return True, f"Full sync complete: {len(synced_files)} files synced, {len(excluded_files)} excluded"

    except Exception as e:
        return False, f"Sync failed: {e}"


def sync_selective(source_dir: Path, dest_dir: Path, files: list[str]) -> tuple[bool, str]:
    """Sync only specific files."""
    try:
        synced_files = []

        for filename in files:
            source_file = source_dir / filename
            if not source_file.exists():
                return False, f"Source file not found: {filename}"

            dest_file = dest_dir / filename
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_file, dest_file)
            synced_files.append(filename)

        return True, f"Selective sync complete: {len(synced_files)} files synced"

    except Exception as e:
        return False, f"Sync failed: {e}"


def validate_dr_config(dr_dir: Path) -> tuple[bool, list[str]]:
    """Validate DR configuration after sync."""
    issues = []

    dr_config = dr_dir / 'dr-specific.conf'
    if dr_config.exists():
        content = dr_config.read_text(encoding='utf-8')

        # Check DR-specific settings
        if 'SUBNET=10.1.2.0/24' not in content:
            issues.append("DR_SUBNET_MODIFIED")

        if 'GATEWAY=10.1.2.1' not in content:
            issues.append("DR_GATEWAY_MODIFIED")

        if 'SERVICE_ENDPOINT=https://api.dr-site.internal:8443' not in content:
            issues.append("DR_ENDPOINT_MODIFIED")

        if 'STORAGE_ARRAY=dr-san-01.internal' not in content:
            issues.append("DR_STORAGE_MODIFIED")

    return len(issues) == 0, issues


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Sync configuration to DR site',
        epilog='WARNING: Default full sync overwrites all DR config. Use --exclude for safety.'
    )
    parser.add_argument(
        '--full',
        action='store_true',
        default=True,
        help='Perform full sync (default: True)'
    )
    parser.add_argument(
        '--exclude',
        action='append',
        default=[],
        help='Files/patterns to exclude from sync (can be used multiple times)'
    )
    parser.add_argument(
        '--files',
        action='append',
        default=[],
        help='Specific files to sync (implies not --full)'
    )
    parser.add_argument(
        '--source',
        default='config',
        help='Source configuration directory'
    )
    parser.add_argument(
        '--dest',
        default='dr',
        help='Destination DR directory'
    )

    args = parser.parse_args()

    source_dir = Path(args.source)
    dest_dir = Path(args.dest)

    if not source_dir.exists():
        print(f"ERROR: Source directory not found: {source_dir}", file=sys.stderr)
        return 1

    if not dest_dir.exists():
        print(f"ERROR: Destination directory not found: {dest_dir}", file=sys.stderr)
        return 1

    # If specific files are provided, override --full
    if args.files:
        args.full = False

    # Perform sync
    if args.full:
        print(f"Performing FULL sync from {source_dir} to {dest_dir}")
        if args.exclude:
            print(f"Excluding: {', '.join(args.exclude)}")
        success, message = sync_full(source_dir, dest_dir, args.exclude)
    else:
        print(f"Performing SELECTIVE sync of {len(args.files)} files")
        success, message = sync_selective(source_dir, dest_dir, args.files)

    print(message)

    if not success:
        return 1

    # Validate DR configuration
    print("\nValidating DR configuration...")
    valid, issues = validate_dr_config(dest_dir)

    if valid:
        print("✓ DR configuration is valid")
        print("  DR-specific settings are preserved")
        print("  Failover capability maintained")
    else:
        print("✗ DR configuration has issues:", file=sys.stderr)
        for issue in issues:
            print(f"  - {issue}", file=sys.stderr)
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
