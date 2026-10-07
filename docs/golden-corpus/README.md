# Golden Corpus: R1.4 Implementation

This directory documents the golden corpus snapshots used for R3 migration testing and R5 UI parity validation.

## Overview

The golden corpus consists of read-only snapshots of working catalyst deployments captured at stable points in the framework's development. These snapshots serve three purposes:

1. **R3 Migration Testing**: Validate that `catalyst migrate` correctly transforms legacy deployment formats to new locator-based storage.
2. **R5 UI Parity Testing**: Ensure new UIs (REST API, desktop app, VS Code extension) can read and render all artifact types from the corpus.
3. **Regression Detection**: Provide a baseline for detecting unintended changes in system behavior across refactoring phases.

## Captured Deployments

### 1. Catalyst Framework (Kernel + SE Module)
- **Location**: `tests/fixtures/catalyst-framework-golden-corpus.tar.gz`
- **Metadata**: `tests/fixtures/catalyst-framework-golden-corpus-metadata.json`
- **Snapshot date**: 2026-10-07 (R0 end)
- **Contents**: 
  - Kernel version: 0.45.0
  - Module: software-engineering v2.1.0
  - Rules: 16 (framework rules, domain rules, templates)
  - Requirements: 11
  - Workflows: 6
  - Journal entries: 173
  - Users: 1
  - Roles: 8

**Use case**: Validates core catalyst framework functionality, rule parsing, and deployment self-hosting.

### 2. UI Repository (Planned)
- **Location**: `tests/fixtures/ui-repo-golden-corpus.tar.gz` (not yet captured)
- **Metadata**: `tests/fixtures/ui-repo-golden-corpus-metadata.json` (not yet captured)
- **Status**: Pending — requires dedicated test UI deployment
- **Expected contents**: UI repo rules, widget definitions, integration with framework rule set

**Use case**: Tests multi-repo deployments and shared rule references.

### 3. Example Application (Planned)
- **Location**: `tests/fixtures/example-app-golden-corpus.tar.gz` (not yet captured)
- **Metadata**: `tests/fixtures/example-app-golden-corpus-metadata.json` (not yet captured)
- **Status**: Pending — target example project TBD
- **Expected contents**: Minimal rule set (5–10 rules), IAM users, simplified installation scenario

**Use case**: Validates simplified installation and typical user deployment.

## Metadata Format

Each golden corpus is accompanied by a metadata JSON file documenting:

```json
{
  "capture_epoch": "2026-10-07T15:55:26.433850+00:00",
  "deployment_name": "catalyst",
  "kernel_version": "0.45.0",
  "module": "software-engineering v2.1.0",
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

**Fields:**
- `capture_epoch`: ISO8601 timestamp when corpus was captured
- `deployment_name`: Human-readable deployment identifier
- `kernel_version`: Catalyst framework version at capture time
- `module`: Active module and version
- `git_sha`: Git commit SHA of the captured deployment's state
- `rules_total`: Total number of rule files in the deployment
- `users`, `roles`, `requirements`, `workflows`: Artifact counts
- `journal_entries`: Number of entries in the deployment journal (audit trail)
- `artifacts`: Breakdown of artifact types

## Capturing a Corpus

### Automated Capture

Run the capture script from the repository root:

```bash
./scripts/capture-golden-corpus.sh [deployment-name]
```

Parameters:
- `deployment-name`: Optional identifier (default: `catalyst-framework`). Determines output file names.

Output:
- `tests/fixtures/{deployment-name}-golden-corpus.tar.gz`
- `tests/fixtures/{deployment-name}-golden-corpus-metadata.json`

### What Gets Captured

The script captures:
1. **All of `.criterion/`**: The deployment's working copy, including:
   - `.criterion/.git/`: Full git history
   - `.criterion/rules/`: All rule definitions
   - `.criterion/development/`: Journal, analysis outputs
   - `.criterion/IAM/`: Users and roles
   - `.criterion/definitions/`: Artifact type definitions
   - `.criterion/requirements/`, `.criterion/workflows/`, etc.

2. **Metadata**: Extracted from deployment files:
   - `version.txt`: Kernel version
   - `DEPLOYMENT.md`: Module information
   - `IAM/users/users.json`, `IAM/roles/roles.json`: User/role counts
   - Rule file enumeration and git history

### Exclusions

The capture script excludes:
- macOS metadata files (`._*`, `.DS_Store`)
- Temporary/derived files

## Using Corpus in Tests

### Example: R3 Migration Validation

```python
# tests/test_migrate_legacy_to_locator.py
import tarfile
import json
from pathlib import Path
from catalyst.store import Store

def test_migrate_catalyst_golden_corpus():
    """Catalyst deployment: legacy pointer → new locator."""
    
    # Extract corpus
    corpus_path = Path("tests/fixtures/catalyst-framework-golden-corpus.tar.gz")
    with tarfile.open(corpus_path) as tar:
        tar.extractall("tmp_golden")
    
    # Load metadata
    with open("tests/fixtures/catalyst-framework-golden-corpus-metadata.json") as f:
        metadata = json.load(f)
    
    # Simulate migration from old format to new
    old_store = Store.legacy_symlink("tmp_golden/.criterion")
    new_store = Store.locator_based(".criterion")
    
    # Validate: rule and journal preservation
    assert len(old_store.rules()) == metadata["rules_total"]
    assert len(new_store.rules()) == metadata["rules_total"]
    assert len(old_store.journal.entries) == metadata["journal_entries"]
```

### Example: R5 UI Parity Testing

```python
# tests/test_ui_parity_golden_corpus.py
def test_api_serves_all_corpus_rules():
    """API can load and serve all rules from golden corpus."""
    
    corpus_path = Path("tests/fixtures/catalyst-framework-golden-corpus.tar.gz")
    with tarfile.open(corpus_path) as tar:
        tar.extractall("tmp_corpus")
    
    # Load via REST API (e.g., catalyst serve)
    api = APIClient("http://localhost:8000")
    rules = api.rules.list()
    
    # Verify
    with open("tests/fixtures/catalyst-framework-golden-corpus-metadata.json") as f:
        metadata = json.load(f)
    
    assert len(rules) == metadata["rules_total"]
    
    # Spot-check rendering
    for rule in rules[:5]:
        rendered = api.rules.render(rule["id"])
        assert rendered["markdown"] is not None
```

## Maintenance

### Update Frequency

- **Phase boundaries** (e.g., R0→R1, R1→R2): Capture new corpus to document stable state
- **Between phases**: Use existing corpus; no updates needed
- **Release branches**: Optional; corpus may be omitted from release artifacts if not needed for deployment testing

### Refresh Process

To update the catalyst-framework corpus (e.g., after R2 stabilizes):

```bash
# On development branch at stable point
git checkout development
./scripts/capture-golden-corpus.sh catalyst-framework

# Verify test suite
pytest tests/test_golden_corpus.py -v

# Commit
git add tests/fixtures/catalyst-framework-golden-corpus*
git commit -m "R1.4: Update catalyst-framework golden corpus"
```

### Size Management

Golden corpus tarballs are stored in `tests/fixtures/` and excluded from gitignore *only during active development phases*. Typical sizes:

- **Catalyst framework**: ~9 MB (includes full .git history)
- **UI repository**: ~5 MB (estimate)
- **Example app**: ~2 MB (estimate)
- **Total**: ~16 MB

To keep repository size manageable:
- Archive old corpus versions to external storage if corpus is refreshed frequently
- Use `.gitattributes` (LFS) if corpus exceeds single-repository budgets
- Document in CHANGELOG when corpus is updated

## Files

```
docs/golden-corpus/
├── README.md                                    (this file)
├── SCHEMA.md                                    (metadata schema documentation)
├── CAPTURE.md                                   (detailed capture process)
└── MIGRATION-TESTS.md                           (R3 migration test examples)
```

Related:
- `scripts/capture-golden-corpus.sh`: Automated capture script
- `tests/test_golden_corpus.py`: Test suite for corpus validation
- `tests/fixtures/`: Actual corpus tarballs and metadata (not in docs/)

## References

- **R1.4 Design**: `framework/kernel/migrations/0.46.0/r1-4-golden-corpus.md`
- **R3 Migration**: `framework/kernel/migrations/0.46.0/r3-*.md` (pending)
- **R5 UI Parity**: `framework/kernel/migrations/0.46.0/r5-*.md` (pending)
