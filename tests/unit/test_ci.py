"""Unit tests for CI/CD configuration."""

import pytest
from pathlib import Path


class TestCIConfig:
    """Tests for CI/CD configuration."""

    def test_github_workflow_exists(self):
        """Test that GitHub workflow file exists."""
        workflow_dir = Path(__file__).parent.parent.parent / ".github" / "workflows"
        workflow_file = workflow_dir / "ci.yml"
        assert workflow_file.exists()

    def test_github_workflow_valid_yaml(self):
        """Test that workflow is valid YAML."""
        import yaml

        workflow_dir = Path(__file__).parent.parent.parent / ".github" / "workflows"
        workflow_file = workflow_dir / "ci.yml"
        content = workflow_file.read_text()

        # Should not raise
        data = yaml.safe_load(content)
        # YAML converts 'on' key to True
        assert True in data or "on" in data
        assert "jobs" in data

    def test_workflow_has_required_jobs(self):
        """Test that workflow has required jobs."""
        import yaml

        workflow_dir = Path(__file__).parent.parent.parent / ".github" / "workflows"
        workflow_file = workflow_dir / "ci.yml"
        content = workflow_file.read_text()
        data = yaml.safe_load(content)

        jobs = data.get("jobs", {})
        assert "lint-and-test" in jobs
        assert "build-and-push" in jobs
        assert "test-deployment" in jobs
        assert "deploy-production" in jobs

    def test_dockerfile_exists(self):
        """Test that Dockerfile exists."""
        repo_root = Path(__file__).parent.parent.parent
        dockerfile = repo_root / "Dockerfile"
        assert dockerfile.exists()

    def test_dockerfile_has_required_instructions(self):
        """Test that Dockerfile has required instructions."""
        repo_root = Path(__file__).parent.parent.parent
        dockerfile = repo_root / "Dockerfile"
        content = dockerfile.read_text()

        assert "FROM python:3.13" in content
        assert "WORKDIR" in content
        assert "EXPOSE" in content
        assert "CMD" in content


class TestDockerfile:
    """Tests for Dockerfile configuration."""

    def test_dockerfile_uses_slim_variant(self):
        """Test that Dockerfile uses slim Python variant."""
        repo_root = Path(__file__).parent.parent.parent
        dockerfile = repo_root / "Dockerfile"
        content = dockerfile.read_text()

        assert "slim" in content

    def test_dockerfile_exposes_correct_port(self):
        """Test that Dockerfile exposes port 8080."""
        repo_root = Path(__file__).parent.parent.parent
        dockerfile = repo_root / "Dockerfile"
        content = dockerfile.read_text()

        assert "8080" in content
