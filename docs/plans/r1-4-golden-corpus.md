# R1.4: Golden Corpus

**Objective:** Snapshot 3 real deployments to create test fixtures for R3 migration
and R5 parity testing.

**Why:** Catalyst's refactor (R1–R7) requires validating that migrations preserve
working deployments and that new UIs remain feature-complete. A golden corpus
(read-only snapshots of real working systems) serves as the baseline for:

- **R3 migration tests:** Ensure `catalyst migrate` (old → new store format)
  preserves all data, rules, and state.
- **R5 parity tests:** New UIs (SPA, desktop, VS Code thin) must be able to
  display and interact with the same artifacts as the kernel CLI.
- **Regression detection:** Snapshots document what a "good" deployment looks
  like at each stage.

---

## Deployment Snapshots (Targets)

### 1. Catalyst Framework (Kernel + SE Module)
**What:** The catalyst repository's own `.criterion` working copy.
**When to capture:** End of R0 (29f9a94 / 2026-10-07).
**Why:** Demonstrates a full greenfield installation (all rules, commands, module).
**Artifacts:** `.criterion/.git/`, working copy state at snapshot moment.
**Test use:** 
- R3 migration (old pointer/symlink → new locator).
- R5 UI parity (render all rules, workflows, deployments).

**Capture method:**
```bash
# In catalyst repo root
git archive --format=tar.gz \
  --prefix=catalyst-golden-corpus/ \
  development:.criterion \
  > tests/fixtures/catalyst-golden-corpus.tar.gz
```

### 2. Catalyst UI Repository
**What:** A deployed UI repo's working copy (if one exists as test deployment).
**When to capture:** Same epoch as #1 (R0 end).
**Why:** Demonstrates multi-repo shared deployment (UI repo uses catalyst rule set).
**Artifacts:** `.criterion/.git/`, UI repo rules, role bindings.
**Test use:**
- R5 UI → rule navigation (widgets inherit rule definitions).
- R3 migration with shared `.criterion` (test submodule → locator transition).

**Status:** Pending decision — does a dedicated test UI repo deployment exist,
or should one be created?

**Capture method:** Same as above.

### 3. Example Deployment
**What:** A minimal example project (e.g. `example-app` if it exists in the org).
**When to capture:** R0 end.
**Why:** Demonstrates a "typical" user project install (simpler rule set, one or two rules).
**Artifacts:** `.criterion/.git/`, app rules, IAM users.
**Test use:**
- R2 simplified install (verify 3-question flow produces valid corpus).
- R3 migration (retrofit deployment with minimal rules).

**Status:** Pending decision — target project?

**Capture method:** Same as above.

---

## Corpus Structure

Location: `tests/fixtures/` (or `.criterion/tests/fixtures/` if in working copy).

```
tests/fixtures/
  catalyst-golden-corpus.tar.gz
  catalyst-golden-corpus-metadata.json   # timestamp, kernel version, rules count
  ui-repo-golden-corpus.tar.gz
  ui-repo-golden-corpus-metadata.json
  example-app-golden-corpus.tar.gz
  example-app-golden-corpus-metadata.json
```

**Metadata format:**
```json
{
  "capture_epoch": "2026-10-07T17:42:00Z",
  "deployment_name": "catalyst-framework",
  "kernel_version": "0.46.0",
  "module": "software-engineering/2.4.0",
  "rule_documents": [
    { "file": "kernel.md", "rules": ["meta-*", "rr-*", "p-*"], "count": 30 },
    { "file": "software-engineering.md", "rules": ["REQ-*", "K-*"], "count": 43 }
  ],
  "rules_total": 73,
  "users": 1,
  "roles": 3,
  "journals_entries": 42,
  "artifacts": {
    "rules": 73,
    "requirements": 0,
    "workflows": 0,
    "domains": 5
  }
}
```

---

## Use in Tests

### R3 Migration Tests

```python
# tests/test_migrate_legacy_to_locator.py
import tarfile
import json
from pathlib import Path
from catalyst.store import Store

def test_migrate_catalyst_golden_corpus():
    """Catalyst repo deployment: old symlink → new locator."""
    
    corpus_path = Path("tests/fixtures/catalyst-golden-corpus.tar.gz")
    with tarfile.open(corpus_path) as tar:
        tar.extractall("tmp_golden")
    
    # Extract metadata
    with open("tests/fixtures/catalyst-golden-corpus-metadata.json") as f:
        metadata = json.load(f)
    
    # Run migration from old pointer format to new locator
    old_store = Store.legacy_symlink("tmp_golden")
    new_store = Store.locator_based(".criterion")  # after R3
    
    # Verify: rule count preserved
    old_rules = old_store.list("rules")
    new_rules = new_store.list("rules")
    assert len(old_rules) == len(new_rules) == metadata["rules_total"]
    
    # Verify: journal entries preserved
    old_journal_len = len(old_store.journal.entries)
    new_journal_len = len(new_store.journal.entries)
    assert old_journal_len == new_journal_len == metadata["journal_entries"]
```

### R5 UI Parity Tests

```python
# tests/test_ui_parity_golden_corpus.py
def test_ui_spa_renders_catalyst_rules():
    """SPA UI can load and display all rules from corpus."""
    
    corpus_path = Path("tests/fixtures/catalyst-golden-corpus.tar.gz")
    with tarfile.open(corpus_path) as tar:
        tar.extractall("tmp_golden")
    
    # Load corpus via REST API (R5 catalyst serve)
    api_client = APIClient("http://localhost:8000")  # running catalyst serve
    rules = api_client.rules.list()
    
    # Verify: all corpus rules appear in API
    with open("tests/fixtures/catalyst-golden-corpus-metadata.json") as f:
        metadata = json.load(f)
    
    assert len(rules) == metadata["rules_total"]
    
    # Spot-check: sample rules render without errors
    for rule in rules[:5]:
        result = api_client.rules.render(rule["id"])
        assert result["markdown"] is not None
```

---

## Capture and Maintenance

### Initial Capture (R1.4)

**Timing:** After R0 complete (29f9a94 / 2026-10-07).

**Process:**
```bash
# From catalyst root
git checkout development
./scripts/capture-golden-corpus.sh  # new script (see below)
```

**Script (scripts/capture-golden-corpus.sh):**
```bash
#!/bin/bash
set -e

FIXTURES_DIR="tests/fixtures"
mkdir -p "$FIXTURES_DIR"

# 1. Catalyst framework
tar -czf "$FIXTURES_DIR/catalyst-golden-corpus.tar.gz" .criterion
python3 << 'PYSCRIPT'
import json
from datetime import datetime
from pathlib import Path

meta = {
    "capture_epoch": datetime.utcnow().isoformat() + "Z",
    "deployment_name": "catalyst-framework",
    "kernel_version": "0.46.0",  # from .criterion/version.txt
    "module": "software-engineering/2.4.0",  # from .criterion/DEPLOYMENT.md
    "rules_total": 73,  # count from rules/*.md
    "users": 1,
    "roles": 3,
    "journal_entries": 42,  # count from development/journal.jsonl
    "artifacts": {
        "rules": 73,
        "requirements": 0,
        "workflows": 0,
        "domains": 5
    }
}

with open("tests/fixtures/catalyst-golden-corpus-metadata.json", "w") as f:
    json.dump(meta, f, indent=2)
PYSCRIPT

echo "✓ Catalyst corpus captured"
```

### Refreshing Corpus (Post-R2, Pre-R3)

**When:** Before major refactors (e.g., store migration in R3).

**Process:** Same script, run on `development` at a stable point. Update
`capture_epoch` in metadata to document the new snapshot moment.

### Validation (CI)

Add to token-budget CI or new `corpus-validation` workflow:

```yaml
# .github/workflows/corpus-validation.yml
name: "Corpus Validation"
on: [push]
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: "Validate golden corpus integrity"
        run: |
          cd tests/fixtures
          for f in *.tar.gz; do
            tar -tzf "$f" > /dev/null && echo "✓ $f" || exit 1
          done
      - name: "Verify metadata JSON"
        run: python3 -m json.tool tests/fixtures/*-metadata.json
```

---

## Open Decisions

1. **UI repo corpus:** Should a dedicated UI test repo exist, or use an existing
   deployment? (Pending infrastructure decision.)
   
2. **Example app:** Which example should be canonical? Recommend: small Python
   project with 5–10 rules (simple but non-trivial).

3. **Snapshot frequency:** Should corpus be updated:
   - Only at major phase boundaries (R0→R1, R1→R2, etc.)?
   - At every release (0.46.0, 0.47.0, …)?
   - Recommendation: Phase boundaries (cheaper, sufficient for regression).

4. **Capture automation:** Add to CI/CD so corpus updates are part of regular
   release process, not manual? (Low priority; can be deferred to R5.)

---

## Acceptance Criteria

✓ **Three golden corpora captured and stored in tests/fixtures/**  
✓ **Metadata generated for each (JSON with rule counts, versions, etc.)**  
✓ **R3 migration test scaffolding created (runs against corpus)**  
✓ **R5 UI parity test scaffolding created (runs against corpus)**  
✓ **Corpus validation in CI (integrity check, tarball extraction)**  
✓ **Corpus size tracked in token budget (each .tar.gz should be <1MB)**  

---

## Rollout

- **Commit to development:** Golden corpus tarballs + metadata + capture script
- **Testing window:** 1 day (validate tarball integrity, test on Linux/macOS)
- **Merge to main:** Ready for R3 migration test writing

---

## Token Impact

**Estimate:**
- Per corpus tarball: ~500–800 KB (compressed `.criterion/` + rules)
- Per metadata file: ~2 KB
- **Total corpus size:** ~2.5–3 MB
- **Token cost (measurement):** ~0 (tarballs not grounded; metadata ~10 tokens)

**BUDGETS-BASELINE.json adjustment:** None (corpus outside grounded docs).
