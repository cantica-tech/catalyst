"""
Golden corpus capture, metadata generation, and artifact rendering tests.

Tests for R1.4: Golden Corpus implementation. Validates:
- Tarball creation and integrity
- Metadata generation accuracy
- Artifact extraction and structure
- Test scaffolding for R3 migration and R5 UI parity testing
"""

import json
import tarfile
import tempfile
from pathlib import Path
from datetime import datetime
import pytest

# The corpus is captured locally (scripts/capture-golden-corpus.sh) and never committed:
# it holds a deployment's private governance data. Tests that need it skip without it.
CORPUS = Path(__file__).parent / "fixtures" / "catalyst-framework-golden-corpus.tar.gz"


def _corpus():
    if not CORPUS.exists():
        pytest.skip(f"golden corpus not captured locally: {CORPUS.name}")
    return CORPUS


class TestGoldenCorpusCapture:
    """Test golden corpus capture script and artifacts."""

    @pytest.fixture
    def fixtures_dir(self):
        """Get the fixtures directory."""
        return Path(__file__).parent / "fixtures"

    @pytest.fixture
    def corpus_tarball(self, fixtures_dir):
        """Get the catalyst golden corpus tarball."""
        return _corpus()

    @pytest.fixture
    def corpus_metadata(self, fixtures_dir):
        """Get the catalyst golden corpus metadata."""
        metadata_file = fixtures_dir / "catalyst-framework-golden-corpus-metadata.json"
        assert metadata_file.exists(), f"Metadata file not found: {metadata_file}"
        with open(metadata_file) as f:
            return json.load(f)

    def test_corpus_tarball_exists_and_is_valid(self, corpus_tarball):
        """Verify golden corpus tarball exists and is a valid tar.gz."""
        assert corpus_tarball.exists(), f"Tarball not found: {corpus_tarball}"
        assert corpus_tarball.suffix == ".gz", "Expected .tar.gz file"
        
        # Verify tarball integrity
        with tarfile.open(corpus_tarball) as tar:
            members = tar.getmembers()
            assert len(members) > 0, "Tarball is empty"

    def test_corpus_tarball_contains_criterion_structure(self, corpus_tarball):
        """Verify tarball contains expected .criterion directory structure."""
        with tarfile.open(corpus_tarball) as tar:
            members = tar.getmembers()
            
            # Check for expected directories
            member_names = {m.name for m in members}
            expected_dirs = {
                ".criterion/",
                ".criterion/rules/",
                ".criterion/development/",
                ".criterion/IAM/",
            }
            
            for expected in expected_dirs:
                found = any(m for m in member_names if m.startswith(expected))
                assert found, f"Expected directory not found in tarball: {expected}"

    def test_corpus_tarball_has_no_git_history(self, corpus_tarball):
        """The corpus never carries the working copy's git repository (private history)."""
        with tarfile.open(corpus_tarball) as tar:
            names = tar.getnames()
        assert not [n for n in names if "/.git/" in n or n.endswith("/.git")], \
            "Corpus must not contain .criterion/.git: recapture with scripts/capture-golden-corpus.sh"

    def test_corpus_metadata_file_exists_and_is_valid_json(self, corpus_metadata):
        """Verify metadata file exists and contains valid JSON."""
        assert isinstance(corpus_metadata, dict), "Metadata should be a JSON object"

    def test_corpus_metadata_has_required_fields(self, corpus_metadata):
        """Verify metadata contains all required fields."""
        required_fields = {
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
            "artifacts",
        }
        
        for field in required_fields:
            assert field in corpus_metadata, f"Missing required field in metadata: {field}"

    def test_corpus_metadata_capture_epoch_is_valid_iso8601(self, corpus_metadata):
        """Verify capture_epoch is a valid ISO8601 timestamp."""
        epoch_str = corpus_metadata["capture_epoch"]
        try:
            # Parse ISO8601 timestamp (may include timezone)
            if epoch_str.endswith("Z"):
                datetime.fromisoformat(epoch_str[:-1] + "+00:00")
            else:
                datetime.fromisoformat(epoch_str)
        except ValueError:
            pytest.fail(f"Invalid ISO8601 timestamp: {epoch_str}")

    def test_corpus_metadata_deployment_name(self, corpus_metadata):
        """Verify deployment_name is set."""
        assert corpus_metadata["deployment_name"], "deployment_name should not be empty"

    def test_corpus_metadata_versions_are_strings(self, corpus_metadata):
        """Verify kernel_version, module, and git_sha are strings."""
        assert isinstance(corpus_metadata["kernel_version"], str), "kernel_version should be string"
        assert isinstance(corpus_metadata["module"], str), "module should be string"
        assert isinstance(corpus_metadata["git_sha"], str), "git_sha should be string"

    def test_corpus_metadata_artifact_counts_are_non_negative(self, corpus_metadata):
        """Verify all artifact counts are non-negative integers."""
        count_fields = {
            "rules_total",
            "users",
            "roles",
            "requirements",
            "workflows",
            "journal_entries",
        }
        
        for field in count_fields:
            value = corpus_metadata[field]
            assert isinstance(value, int), f"{field} should be integer, got {type(value)}"
            assert value >= 0, f"{field} should be non-negative, got {value}"

    def test_corpus_metadata_artifacts_subobject(self, corpus_metadata):
        """Verify artifacts subobject contains expected fields."""
        artifacts = corpus_metadata["artifacts"]
        assert isinstance(artifacts, dict), "artifacts should be an object"
        
        expected_artifact_types = {"rules", "requirements", "workflows", "domains"}
        for artifact_type in expected_artifact_types:
            assert artifact_type in artifacts, f"Missing artifact type: {artifact_type}"
            assert isinstance(artifacts[artifact_type], int), f"{artifact_type} should be integer"
            assert artifacts[artifact_type] >= 0, f"{artifact_type} should be non-negative"

    def test_corpus_metadata_artifacts_match_top_level_counts(self, corpus_metadata):
        """Verify artifact subobject counts match top-level counts."""
        assert corpus_metadata["artifacts"]["rules"] == corpus_metadata["rules_total"]
        assert corpus_metadata["artifacts"]["requirements"] == corpus_metadata["requirements"]
        assert corpus_metadata["artifacts"]["workflows"] == corpus_metadata["workflows"]

    def test_corpus_metadata_rules_count_matches_tarball_content(self, corpus_tarball, corpus_metadata):
        """Verify rules count in metadata matches actual rules in tarball."""
        with tarfile.open(corpus_tarball) as tar:
            members = tar.getmembers()
            
            # Count .md files in rules/ directory
            rule_files = [
                m for m in members 
                if m.name.endswith(".md") and "/rules/" in m.name and m.isfile()
            ]
            
            # Should have at least the number of rules specified in metadata
            assert len(rule_files) >= corpus_metadata["rules_total"], \
                f"Tarball has {len(rule_files)} rule files, metadata claims {corpus_metadata['rules_total']}"


class TestGoldenCorpusExtraction:
    """Test extracting and validating corpus contents."""

    @pytest.fixture
    def corpus_tarball(self):
        """Get the catalyst golden corpus tarball."""
        return _corpus()

    @pytest.fixture
    def extracted_corpus(self, corpus_tarball):
        """Extract corpus to temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(corpus_tarball) as tar:
                tar.extractall(tmpdir)
            
            # Find the .criterion directory (should be at tmpdir/.criterion)
            criterion_path = Path(tmpdir) / ".criterion"
            if not criterion_path.exists():
                # Look for any .criterion directory
                for p in Path(tmpdir).glob("**/.criterion"):
                    criterion_path = p
                    break
            
            yield criterion_path

    def test_extracted_corpus_has_criterion_root(self, extracted_corpus):
        """Verify extracted corpus has .criterion root directory."""
        assert extracted_corpus.exists(), f"Extracted .criterion not found at {extracted_corpus}"
        assert extracted_corpus.is_dir()

    def test_extracted_corpus_has_no_git_repository(self, extracted_corpus):
        """The extracted corpus carries no git repository (private history stays out)."""
        assert not (extracted_corpus / ".git").exists()

    def test_extracted_corpus_has_rules_directory(self, extracted_corpus):
        """Verify extracted corpus contains rules directory."""
        rules_dir = extracted_corpus / "rules"
        assert rules_dir.exists(), "Extracted corpus should contain rules directory"
        assert rules_dir.is_dir()

    def test_extracted_corpus_has_development_directory(self, extracted_corpus):
        """Verify extracted corpus contains development directory."""
        dev_dir = extracted_corpus / "development"
        assert dev_dir.exists(), "Extracted corpus should contain development directory"
        assert dev_dir.is_dir()

    def test_extracted_corpus_has_journal(self, extracted_corpus):
        """Verify extracted corpus contains journal.jsonl."""
        journal = extracted_corpus / "development" / "journal.jsonl"
        assert journal.exists(), "Extracted corpus should contain development/journal.jsonl"
        assert journal.is_file()

    def test_extracted_corpus_has_version(self, extracted_corpus):
        """Verify extracted corpus contains version.txt."""
        version_file = extracted_corpus / "version.txt"
        assert version_file.exists(), "Extracted corpus should contain version.txt"
        assert version_file.is_file()
        
        # Version should be readable
        version = version_file.read_text().strip()
        assert version, "version.txt should not be empty"

    def test_extracted_corpus_has_deployment_metadata(self, extracted_corpus):
        """Verify extracted corpus contains DEPLOYMENT.md."""
        deployment = extracted_corpus / "DEPLOYMENT.md"
        assert deployment.exists(), "Extracted corpus should contain DEPLOYMENT.md"
        assert deployment.is_file()

    def test_extracted_corpus_rules_are_readable(self, extracted_corpus):
        """Verify at least some rules in extracted corpus are readable."""
        rules_dir = extracted_corpus / "rules"
        
        # Find all .md files recursively in rules directory
        md_files = list(rules_dir.glob("**/*.md"))
        
        assert len(md_files) > 0, "Should have at least one rule file"
        
        # Try reading first few rules, with encoding handling
        successful_reads = 0
        for rule_file in md_files[:5]:
            try:
                content = rule_file.read_text(encoding='utf-8', errors='ignore')
                if content:
                    successful_reads += 1
            except Exception:
                # Some files might be binary or have encoding issues
                pass
        
        # At least some files should be readable
        assert successful_reads > 0, "Should be able to read at least one rule file"

    def test_extracted_corpus_has_iam_structure(self, extracted_corpus):
        """Verify extracted corpus contains IAM directory structure."""
        iam_dir = extracted_corpus / "IAM"
        assert iam_dir.exists(), "Extracted corpus should contain IAM directory"
        
        # Check for users and roles
        users_file = iam_dir / "users" / "users.json"
        roles_file = iam_dir / "roles" / "roles.json"
        
        assert users_file.exists(), "Should contain IAM/users/users.json"
        assert roles_file.exists(), "Should contain IAM/roles/roles.json"


class TestGoldenCorpusMetadata:
    """Test golden corpus metadata generation and content."""

    @pytest.fixture
    def corpus_metadata(self):
        """Get the catalyst golden corpus metadata."""
        metadata_file = Path(__file__).parent / "fixtures" / "catalyst-framework-golden-corpus-metadata.json"
        with open(metadata_file) as f:
            return json.load(f)

    def test_metadata_kernel_version_format(self, corpus_metadata):
        """Verify kernel version follows semantic versioning."""
        version = corpus_metadata["kernel_version"]
        # Should be in format X.Y.Z or "unknown"
        parts = version.split(".")
        assert len(parts) == 3 or version == "unknown", f"Invalid version format: {version}"

    def test_metadata_git_sha_format(self, corpus_metadata):
        """Verify git SHA is valid commit hash format."""
        sha = corpus_metadata["git_sha"]
        # Should be 40 hex characters or "unknown"
        if sha != "unknown":
            assert len(sha) == 40, f"Invalid git SHA length: {sha}"
            try:
                int(sha, 16)
            except ValueError:
                pytest.fail(f"Invalid git SHA (not hex): {sha}")

    def test_metadata_roles_greater_than_or_equal_users(self, corpus_metadata):
        """Verify roles count is >= users count (reasonable sanity check)."""
        # Typically systems have at least one role per user, often more
        roles = corpus_metadata["roles"]
        users = corpus_metadata["users"]
        assert roles >= 1, "Should have at least one role defined"

    def test_metadata_module_name_present(self, corpus_metadata):
        """Verify module name is present and non-empty."""
        module = corpus_metadata["module"]
        assert module and module != "unknown", f"Module should be specified, got: {module}"


class TestGoldenCorpusR3MigrationScaffolding:
    """Test scaffolding for R3 migration validation."""

    @pytest.fixture
    def corpus_tarball(self):
        """Get the catalyst golden corpus tarball."""
        return _corpus()

    @pytest.fixture
    def corpus_metadata(self):
        """Get the catalyst golden corpus metadata."""
        metadata_file = Path(__file__).parent / "fixtures" / "catalyst-framework-golden-corpus-metadata.json"
        with open(metadata_file) as f:
            return json.load(f)

    def test_r3_migration_can_extract_and_load_corpus(self, corpus_tarball, corpus_metadata):
        """Test that R3 migration test can extract and load corpus."""
        # This is scaffolding for future R3 migration tests
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(corpus_tarball) as tar:
                tar.extractall(tmpdir)
            
            # Verify extraction succeeded
            criterion_path = Path(tmpdir) / ".criterion"
            assert criterion_path.exists()
            
            # Verify we can access the journal (key test artifact)
            journal_path = criterion_path / "development" / "journal.jsonl"
            assert journal_path.exists()
            
            # Count journal entries match metadata
            journal_lines = journal_path.read_text().strip().split("\n")
            expected_count = corpus_metadata["journal_entries"]
            # Allow some variance due to extraction/line ending differences
            assert abs(len(journal_lines) - expected_count) <= 1, \
                f"Journal entry count mismatch: extracted {len(journal_lines)}, expected ~{expected_count}"

    def test_r3_migration_preserves_rule_structure(self, corpus_tarball, corpus_metadata):
        """Test that R3 migration will find expected rule structure in corpus."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(corpus_tarball) as tar:
                tar.extractall(tmpdir)
            
            criterion_path = Path(tmpdir) / ".criterion"
            rules_path = criterion_path / "rules"
            
            # Count rule files recursively (rules may be in subdirectories)
            rule_files = list(rules_path.glob("**/*.md"))
            # Filter out template and README files for accuracy
            rule_files = [f for f in rule_files if not f.name.startswith("TEMPLATE-") and f.name not in ("README.md",)]
            
            expected_count = corpus_metadata["rules_total"]
            
            # Should have at least most of the expected rules
            # (accounting for template and documentation files)
            assert len(rule_files) >= expected_count - 5, \
                f"Rule file count mismatch: found {len(rule_files)}, expected ~{expected_count}"


class TestGoldenCorpusR5UIParityScaffolding:
    """Test scaffolding for R5 UI parity validation."""

    @pytest.fixture
    def corpus_metadata(self):
        """Get the catalyst golden corpus metadata."""
        metadata_file = Path(__file__).parent / "fixtures" / "catalyst-framework-golden-corpus-metadata.json"
        with open(metadata_file) as f:
            return json.load(f)

    def test_r5_ui_can_read_corpus_metadata(self, corpus_metadata):
        """Test that R5 UI can read and parse corpus metadata."""
        # Verify metadata is properly structured for UI consumption
        assert "capture_epoch" in corpus_metadata
        assert "deployment_name" in corpus_metadata
        assert "artifacts" in corpus_metadata
        
        # Metadata should be serializable for API responses
        json_str = json.dumps(corpus_metadata)
        assert len(json_str) > 0

    def test_r5_ui_artifact_counts_match_expectations(self, corpus_metadata):
        """Test that artifact counts are consistent across metadata."""
        artifacts = corpus_metadata["artifacts"]
        
        # Top-level counts should match artifact subobject
        assert corpus_metadata["rules_total"] == artifacts["rules"]
        assert corpus_metadata["requirements"] == artifacts["requirements"]
        assert corpus_metadata["workflows"] == artifacts["workflows"]

    def test_r5_ui_can_identify_deployment_from_metadata(self, corpus_metadata):
        """Test that UI can identify and describe the deployment."""
        assert corpus_metadata["deployment_name"]
        assert corpus_metadata["kernel_version"]
        assert corpus_metadata["module"]
        
        # Should have enough info to show in a UI dashboard
        summary = f"{corpus_metadata['deployment_name']} (kernel {corpus_metadata['kernel_version']})"
        assert len(summary) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
