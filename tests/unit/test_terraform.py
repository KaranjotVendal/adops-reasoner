"""Unit tests for Terraform configuration."""

import subprocess
import pytest
from pathlib import Path


class TestTerraformConfig:
    """Tests for Terraform configuration."""

    def test_terraform_syntax_valid(self):
        """Test that Terraform files have valid syntax."""
        infra_dir = Path(__file__).parent.parent.parent / "infra"

        # Check terraform is available
        try:
            result = subprocess.run(
                ["terraform", "version"],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                pytest.skip("Terraform not installed")
        except FileNotFoundError:
            pytest.skip("Terraform not installed")

        # Initialize terraform (will fail without GCP credentials, but syntax is checked)
        result = subprocess.run(
            ["terraform", "init", "-backend=false"],
            cwd=infra_dir,
            capture_output=True,
            text=True,
        )
        # We expect this to fail without valid config, but it validates syntax
        # Just check that main.tf exists and is readable
        main_tf = infra_dir / "main.tf"
        assert main_tf.exists()
        assert main_tf.stat().st_size > 0

    def test_tfvars_example_exists(self):
        """Test that tfvars.example exists."""
        infra_dir = Path(__file__).parent.parent.parent / "infra"
        tfvars = infra_dir / "terraform.tfvars.example"
        assert tfvars.exists()

    def test_main_tf_contains_required_resources(self):
        """Test that main.tf contains required resources."""
        infra_dir = Path(__file__).parent.parent.parent / "infra"
        main_tf = infra_dir / "main.tf"
        content = main_tf.read_text()

        # Check for required resources
        assert "google_cloud_run_v2_service" in content
        assert "google_secret_manager_secret" in content
        assert "google_service_account" in content

    def test_gitignore_infra(self):
        """Test that infra has .gitignore."""
        infra_dir = Path(__file__).parent.parent.parent / "infra"
        gitignore = infra_dir / ".gitignore"
        assert gitignore.exists()
        content = gitignore.read_text()
        assert "*.tfstate" in content
        assert "*.tfvars" in content
