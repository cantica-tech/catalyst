# Golden Corpus Metadata Schema

This document defines the structure and field specifications for golden corpus metadata JSON files.

## Schema Definition

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Golden Corpus Metadata",
  "description": "Metadata for a snapshot of a catalyst deployment",
  "type": "object",
  "required": [
    "capture_epoch",
    "deployment_name",
    "kernel_version",
    "module",
    "git_sha",
    "rules_total",
    "users",
    "roles",
    "requirements",
    "workflows",
    "journal_entries",
    "artifacts"
  ],
  "properties": {
    "capture_epoch": {
      "type": "string",
      "format": "date-time",
      "description": "ISO8601 timestamp (UTC) when corpus was captured"
    },
    "deployment_name": {
      "type": "string",
      "minLength": 1,
      "description": "Human-readable identifier for the deployment (e.g., 'catalyst', 'example-app', 'ui-repo')"
    },
    "kernel_version": {
      "type": "string",
      "description": "Semantic version of catalyst kernel at capture time (e.g., '0.45.0')"
    },
    "module": {
      "type": "string",
      "description": "Active module identifier and version (e.g., 'software-engineering v2.1.0')"
    },
    "git_sha": {
      "type": "string",
      "pattern": "^[0-9a-f]{40}$",
      "description": "Full git commit SHA (40 hex characters) of deployment state at capture"
    },
    "rules_total": {
      "type": "integer",
      "minimum": 0,
      "description": "Total number of rule definition files in the deployment"
    },
    "users": {
      "type": "integer",
      "minimum": 0,
      "description": "Number of IAM users defined in the deployment"
    },
    "roles": {
      "type": "integer",
      "minimum": 0,
      "description": "Number of IAM roles defined in the deployment"
    },
    "requirements": {
      "type": "integer",
      "minimum": 0,
      "description": "Number of requirement artifact files"
    },
    "workflows": {
      "type": "integer",
      "minimum": 0,
      "description": "Number of workflow artifact files"
    },
    "journal_entries": {
      "type": "integer",
      "minimum": 0,
      "description": "Number of lines in the deployment journal (development/journal.jsonl)"
    },
    "artifacts": {
      "type": "object",
      "required": ["rules", "requirements", "workflows", "domains"],
      "properties": {
        "rules": {
          "type": "integer",
          "minimum": 0,
          "description": "Artifact count: rules"
        },
        "requirements": {
          "type": "integer",
          "minimum": 0,
          "description": "Artifact count: requirements"
        },
        "workflows": {
          "type": "integer",
          "minimum": 0,
          "description": "Artifact count: workflows"
        },
        "domains": {
          "type": "integer",
          "minimum": 0,
          "description": "Artifact count: domains"
        }
      },
      "description": "Breakdown of artifact types by count"
    }
  }
}
```

## Field Specifications

### capture_epoch
- **Format**: ISO8601 datetime string, including timezone (recommended: UTC)
- **Example**: `"2026-10-07T15:55:26.433850+00:00"` or `"2026-10-07T15:55:26Z"`
- **Source**: Generated at capture time via Python's `datetime.now(timezone.utc).isoformat()`
- **Use**: Determines corpus age; used in test reports to correlate with framework releases

### deployment_name
- **Type**: String, 1–64 characters recommended
- **Examples**: `"catalyst-framework"`, `"example-app"`, `"ui-repo-deployment"`
- **Source**: Extracted from DEPLOYMENT.md or provided as script parameter
- **Use**: Identifies corpus in test output and naming; helps organize multiple corpora

### kernel_version
- **Format**: Semantic version (X.Y.Z)
- **Example**: `"0.45.0"`
- **Source**: Read from `.criterion/version.txt`
- **Use**: Documents kernel baseline; used to validate framework compatibility across migrations

### module
- **Format**: Module name + optional version, semicolon-separated
- **Examples**: 
  - `"software-engineering v2.1.0"`
  - `"custom-module/1.0.0"`
  - `"unknown"` (if module info unavailable)
- **Source**: Extracted from DEPLOYMENT.md
- **Use**: Identifies module baseline; may guide migration path selection in R3

### git_sha
- **Format**: 40-character hexadecimal string (git commit SHA)
- **Example**: `"8fbf7f07af171a6637d5922760929b5bfe0feb7f"`
- **Source**: Generated via `git rev-parse HEAD` in captured deployment
- **Use**: Links corpus to exact git state; enables checkout and reproduction of same deployment

### Artifact Counts (rules_total, requirements, workflows, users, roles, journal_entries)
- **Type**: Non-negative integers
- **Source**: Counted/extracted from deployment files and IAM configuration
- **Use**: 
  - Sanity checks on extraction and migration
  - Test assertions to validate artifact preservation
  - Documentation of deployment scope
- **Consistency**: All counts should match between top-level fields and `artifacts` subobject where applicable

### artifacts (subobject)
- **Type**: Object mapping artifact type names to counts
- **Required keys**: `rules`, `requirements`, `workflows`, `domains`
- **Optional keys**: `bugfix`, `feature`, `test`, `etc.` (if applicable to deployment)
- **Constraint**: `artifacts.rules` must equal top-level `rules_total` (enforced by tests)
- **Use**: Provides a single object for API responses and dashboard rendering in R5 UIs

## Validation Rules

1. **Temporal Consistency**: `capture_epoch` should be close to file modification timestamps in tarball
2. **Count Consistency**: 
   - `artifacts.rules == rules_total`
   - `artifacts.requirements == requirements`
   - `artifacts.workflows == workflows`
3. **SHA Validity**: `git_sha` should be a valid commit in the deployment's `.git` directory
4. **Non-negativity**: All counts must be ≥ 0
5. **Completeness**: All required fields must be present (no null values)

## Example: Minimal Valid Metadata

```json
{
  "capture_epoch": "2026-10-07T15:55:26Z",
  "deployment_name": "minimal-example",
  "kernel_version": "0.45.0",
  "module": "custom-module/1.0.0",
  "git_sha": "0000000000000000000000000000000000000000",
  "rules_total": 5,
  "users": 2,
  "roles": 3,
  "requirements": 0,
  "workflows": 1,
  "journal_entries": 10,
  "artifacts": {
    "rules": 5,
    "requirements": 0,
    "workflows": 1,
    "domains": 2
  }
}
```

## Example: Full Real Corpus (catalyst-framework)

```json
{
  "capture_epoch": "2026-10-07T15:55:26.433850+00:00",
  "deployment_name": "catalyst",
  "kernel_version": "0.45.0",
  "module": "`software-engineering`",
  "git_sha": "8fbf7f07af171a6637d5922760929b5bfe0feb7f",
  "rules_total": 16,
  "users": 1,
  "roles": 8,
  "requirements": 11,
  "workflows": 6,
  "journal_entries": 173,
  "artifacts": {
    "rules": 16,
    "requirements": 11,
    "workflows": 6,
    "domains": 5
  }
}
```

## Programmatic Access

### Python

```python
import json
from pathlib import Path

def load_corpus_metadata(corpus_name: str) -> dict:
    """Load golden corpus metadata."""
    metadata_file = Path("tests/fixtures") / f"{corpus_name}-golden-corpus-metadata.json"
    with open(metadata_file) as f:
        return json.load(f)

# Usage
metadata = load_corpus_metadata("catalyst-framework")
print(f"Captured: {metadata['capture_epoch']}")
print(f"Rules: {metadata['rules_total']}")
```

### JavaScript/Node.js

```javascript
const fs = require('fs');
const path = require('path');

function loadCorpusMetadata(corpusName) {
  const metadataFile = path.join(
    'tests/fixtures',
    `${corpusName}-golden-corpus-metadata.json`
  );
  return JSON.parse(fs.readFileSync(metadataFile, 'utf-8'));
}

// Usage
const metadata = loadCorpusMetadata('catalyst-framework');
console.log(`Captured: ${metadata.capture_epoch}`);
console.log(`Rules: ${metadata.rules_total}`);
```

## Extending the Schema

To add fields for future testing needs:

1. **Add to required fields** if the field is essential for all corpora
2. **Add to optional fields** if only some corpora need it
3. **Update validation tests** in `tests/test_golden_corpus.py`
4. **Document in this file** with rationale and use cases
5. **Regenerate all existing corpora** to include the new field

Example: Adding per-rule metadata

```json
{
  "...": "...",
  "rules_by_type": {
    "framework": 8,
    "domain": 5,
    "template": 3
  }
}
```

Would require:
- New capture logic to categorize rules
- Updated schema in this document
- Additional test assertions
- Regeneration of existing corpora
