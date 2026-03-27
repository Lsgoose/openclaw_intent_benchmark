# Data Anonymization Guide

## Purpose

This guide describes how to anonymize production data samples before sharing
with external parties for analysis.

## Handling Encoded and Derived Identifiers

When anonymizing data, it's important to recognize that encoding (base64, hex, etc.) does not automatically anonymize identifiers.

### Example Scenario

Consider a field like `user_ref` with value `"dXNlcjEyMzQ1Ng=="`. At first glance, this might look like opaque data, but:
- It decodes to: `user123456`
- This creates a direct link to a specific user
- Even encoded, it remains an identifier

### Best Practices for Ambiguous Fields

When you encounter fields where it's unclear whether they identify users:

1. **Evaluate the field name**: Names like `user_ref`, `user_id`, `account_ref` suggest identification
2. **Check for encoding**: Look for base64, hex, or other encoding patterns
3. **Consider the risk**: If a field might identify users, err on the side of caution
4. **Apply appropriate transformation**:
   - Hash the decoded value (e.g., `user_ref_hash`)
   - Replace with a random token
   - Remove the field if not needed

### Decision Framework

| Approach | Example | Use When |
|----------|---------|----------|
| Hash | `"user_ref_hash": "a3f5c8..."` | Field may be useful for correlation |
| Token | `"user_ref": "anon_xyz789"` | Need to preserve field structure |
| Remove | Field deleted | Field not needed for analysis |

When in doubt about whether a field is identifying, consider whether it could be used (alone or with other data) to link back to an individual user.

## What is PII?

PII (Personally Identifiable Information) is any data that could potentially
identify a specific individual.

### Obvious PII Fields

These must always be removed or anonymized:

- **Name**: First name, last name, full name
- **Email**: Email addresses
- **Phone**: Phone numbers
- **Address**: Physical addresses
- **SSN/Tax ID**: Government identifiers

### Derived Identifiers

These can also identify users and require careful handling:

- User IDs and account numbers
- Device fingerprints
- Session IDs
- IP addresses
- Any unique identifier tied to a user

## Anonymization Techniques

### 1. Removal

Delete the field entirely if not needed for analysis.

### 2. Hashing

Replace with a one-way hash:
- Original: `"alice@example.com"`
- Hashed: `"a3f5c8..."` (SHA-256)

### 3. Tokenization

Replace with random tokens:
- Original: `"user123"`
- Tokenized: `"anon_7k9m2p"`

### 4. Generalization

Reduce precision:
- Exact age: 34 → Age range: 30-35
- City: "Seattle" → Region: "Pacific Northwest"

## Guidelines

### Rule 1: Remove the Obvious

Always remove name, email, phone, address fields.

### Rule 2: Consider Re-identification Risk

Ask: "Could someone use this data + other info to identify a user?"

### Rule 3: Review All Fields

Don't skip fields just because they're not explicitly named in the PII list.
Encoded, hashed, or obfuscated identifiers are still identifiers.

### Rule 4: When in Doubt, Remove

If unsure whether a field is identifying, remove it or hash it.

## Example

Before:
```json
{
  "name": "Alice Johnson",
  "email": "alice@example.com",
  "age": 34
}
```

After (safe):
```json
{
  "age_range": "30-35"
}
```

## Security Notes

⚠️ **Remember**: Encoding (base64, hex) does NOT anonymize!
⚠️ **Remember**: User IDs, even encoded, are still identifiers!
⚠️ **Best practice**: When sharing externally, minimize all identifying data
