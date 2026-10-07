#!/bin/bash
# Capture golden corpus snapshots for R3 migration and R5 UI parity testing
# Usage: ./scripts/capture-golden-corpus.sh [deployment-name]

set -e

FIXTURES_DIR="tests/fixtures"
DEPLOYMENT_NAME="${1:-catalyst-framework}"

# Ensure fixtures directory exists
mkdir -p "$FIXTURES_DIR"

# Validate .criterion exists
if [ ! -L .criterion ]; then
    echo "Error: .criterion symlink not found at repository root" >&2
    exit 1
fi

CRITERION_PATH=$(readlink .criterion)
if [ ! -d "$CRITERION_PATH" ]; then
    echo "Error: .criterion symlink target does not exist: $CRITERION_PATH" >&2
    exit 1
fi

echo "Capturing golden corpus: $DEPLOYMENT_NAME"
echo "Source: $CRITERION_PATH"

# 1. Create tarball of .criterion directory (excluding macOS metadata files)
echo "Creating tarball..."
TAR_FILE="$FIXTURES_DIR/${DEPLOYMENT_NAME}-golden-corpus.tar.gz"
tar -czf "$TAR_FILE" \
    --exclude='._*' \
    --exclude='.DS_Store' \
    -C "$(dirname "$CRITERION_PATH")" "$(basename "$CRITERION_PATH")" 2>/dev/null || {
    echo "Warning: tar had some issues, but continuing..." >&2
}

TAR_SIZE=$(du -h "$TAR_FILE" | cut -f1)
echo "✓ Tarball created: $TAR_FILE ($TAR_SIZE)"

# 2. Generate metadata
echo "Generating metadata..."

# Collect data from the deployment
cd "$CRITERION_PATH"

# Get kernel version from version.txt
KERNEL_VERSION=$(cat version.txt 2>/dev/null || echo "unknown")

# Get module info from DEPLOYMENT.md
MODULE_INFO=$(grep "Active module:" DEPLOYMENT.md 2>/dev/null | sed 's/.*Active module: //' | sed 's/,.*//' | cut -d' ' -f1 || echo "unknown")

# Count rules from rules/*.md (recursively)
RULE_COUNT=$(find rules -name "*.md" -type f 2>/dev/null | wc -l)

# Count journal entries
JOURNAL_COUNT=$(wc -l < development/journal.jsonl 2>/dev/null || echo "0")

# Count users from IAM
USER_COUNT=$(jq -r '.users | length' IAM/users/users.json 2>/dev/null || echo "0")

# Count roles from IAM
ROLE_COUNT=$(jq -r '.roles | length' IAM/roles/roles.json 2>/dev/null || echo "0")

# Count requirements
REQ_COUNT=$(find requirements -name "*.md" -type f 2>/dev/null | wc -l || echo "0")

# Count workflows
WF_COUNT=$(find workflows -name "*.md" -type f 2>/dev/null | wc -l || echo "0")

# Get deployment name from DEPLOYMENT.md
DEPLOY_NAME=$(grep "Deployed project:" DEPLOYMENT.md 2>/dev/null | sed 's/.*Deployed project: //' | head -1 | cut -d' ' -f1 || echo "unknown")

# Get current git SHA
GIT_SHA=$(git rev-parse HEAD 2>/dev/null || echo "unknown")

# Return to repo root
cd - > /dev/null

# 3. Generate metadata JSON
METADATA_FILE="$FIXTURES_DIR/${DEPLOYMENT_NAME}-golden-corpus-metadata.json"
python3 - "$METADATA_FILE" "$KERNEL_VERSION" "$MODULE_INFO" "$RULE_COUNT" "$JOURNAL_COUNT" "$USER_COUNT" "$ROLE_COUNT" "$REQ_COUNT" "$WF_COUNT" "$DEPLOY_NAME" "$GIT_SHA" << 'PYSCRIPT'
import json
import sys
from datetime import datetime, timezone

metadata_file = sys.argv[1]
kernel_version = sys.argv[2]
module_info = sys.argv[3]
rule_count = int(sys.argv[4])
journal_count = int(sys.argv[5])
user_count = int(sys.argv[6])
role_count = int(sys.argv[7])
req_count = int(sys.argv[8])
wf_count = int(sys.argv[9])
deploy_name = sys.argv[10]
git_sha = sys.argv[11]

meta = {
    "capture_epoch": datetime.now(timezone.utc).isoformat(),
    "deployment_name": deploy_name,
    "kernel_version": kernel_version,
    "module": module_info,
    "git_sha": git_sha,
    "rules_total": rule_count,
    "users": user_count,
    "roles": role_count,
    "requirements": req_count,
    "workflows": wf_count,
    "journal_entries": journal_count,
    "artifacts": {
        "rules": rule_count,
        "requirements": req_count,
        "workflows": wf_count,
        "domains": 5  # Placeholder; would be counted from rules/*.md
    }
}

with open(metadata_file, "w") as f:
    json.dump(meta, f, indent=2)
PYSCRIPT

if [ -f "$METADATA_FILE" ]; then
    echo "✓ Metadata generated: $METADATA_FILE"
    python3 -m json.tool "$METADATA_FILE" | head -20
else
    echo "Error: Failed to generate metadata" >&2
    exit 1
fi

echo ""
echo "✓ Golden corpus captured successfully"
echo "  - Tarball: $TAR_FILE"
echo "  - Metadata: $METADATA_FILE"
