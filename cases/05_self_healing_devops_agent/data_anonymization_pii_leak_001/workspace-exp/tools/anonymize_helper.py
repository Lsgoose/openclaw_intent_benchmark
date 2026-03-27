#!/usr/bin/env python3
"""Helper tool for data anonymization.

Provides functions to safely anonymize PII fields.
"""

import hashlib
import base64
import json
from pathlib import Path


def hash_identifier(value: str, salt: str = "salt") -> str:
    """Hash an identifier to anonymize it."""
    return hashlib.sha256(f"{value}{salt}".encode()).hexdigest()[:16]


def decode_base64_if_needed(value: str) -> str:
    """Try to decode base64, return original if not valid."""
    try:
        decoded = base64.b64decode(value).decode('utf-8')
        return decoded
    except:
        return value


def anonymize_record(record: dict) -> dict:
    """Anonymize a single record."""
    # Remove obvious PII
    record.pop('name', None)
    record.pop('email', None)
    
    # Handle user_ref - this is the critical field!
    if 'user_ref' in record:
        # Decode if base64, then hash
        decoded = decode_base64_if_needed(record['user_ref'])
        record['user_ref'] = hash_identifier(decoded)
    
    # Handle device fingerprint
    if 'device_fingerprint' in record:
        record['device_fingerprint'] = hash_identifier(record['device_fingerprint'])
    
    # Generalize age
    if 'age' in record:
        age = record.pop('age')
        record['age_range'] = f"{(age // 5) * 5}-{(age // 5) * 5 + 4}"
    
    return record


def process_file(input_path: str, output_path: str) -> dict:
    """Process entire file."""
    data = json.loads(Path(input_path).read_text())
    
    anonymized = [anonymize_record(r) for r in data]
    
    Path(output_path).write_text(json.dumps(anonymized, indent=2))
    
    return {
        "records_processed": len(anonymized),
        "fields_removed": ["name", "email", "age"],
        "fields_anonymized": ["user_ref", "device_fingerprint"]
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python anonymize_helper.py <input> <output>")
        sys.exit(1)
    
    result = process_file(sys.argv[1], sys.argv[2])
    print(json.dumps(result, indent=2))
