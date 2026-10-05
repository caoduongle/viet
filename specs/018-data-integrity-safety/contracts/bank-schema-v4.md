# Bank Storage Schema Contract: Version 4

**Feature Branch**: `fix/phase0-data-integrity`  
**Date**: 2026-10-05  
**Spec**: [spec.md](../spec.md)  

---

## 1. Specification

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "ChuVietTayBankSchemaV4",
  "type": "object",
  "required": ["schema_version", "words"],
  "properties": {
    "schema_version": {
      "type": "integer",
      "enum": [4]
    },
    "words": {
      "type": "object",
      "additionalProperties": {
        "type": "array",
        "items": { "$ref": "#/definitions/sample" }
      }
    },
    "letters": {
      "type": "object",
      "additionalProperties": {
        "type": "array",
        "items": { "$ref": "#/definitions/sample" }
      }
    },
    "digits": {
      "type": "object",
      "additionalProperties": {
        "type": "array",
        "items": { "$ref": "#/definitions/sample" }
      }
    },
    "symbols": {
      "type": "object",
      "additionalProperties": {
        "type": "array",
        "items": { "$ref": "#/definitions/sample" }
      }
    },
    "punct": {
      "type": "object",
      "additionalProperties": {
        "type": "array",
        "items": { "$ref": "#/definitions/sample" }
      }
    },
    "marks": {
      "type": "object"
    },
    "learned_files": {
      "type": "array",
      "items": { "type": "string" }
    },
    "tombstones": {
      "oneOf": [
        {
          "type": "object",
          "additionalProperties": { "type": "number" }
        },
        {
          "type": "array",
          "items": { "type": "string" }
        }
      ]
    }
  },
  "definitions": {
    "sample": {
      "type": "object",
      "required": ["s", "w"],
      "properties": {
        "s": {
          "type": "array",
          "items": {
            "type": "array",
            "items": { "type": "number" }
          }
        },
        "w": { "type": "number" }
      }
    }
  }
}
```

## 2. Tombstone Key Rules

1. **Qualified Key (v4 standard)**: `"<category>:<label>"`.
   - Examples: `"words:viet"`, `"letters:a"`, `"symbols:π"`.
2. **Legacy Key (v3 backward compatibility)**: `"<label>"`.
   - Examples: `"viet"`, `"a"`.
   - When present, legacy keys apply to all categories during dictionary merge.
