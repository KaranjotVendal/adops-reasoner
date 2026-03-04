# PR5: Terraform Infrastructure

**Branch:** `pr/05-terraform-minimal`  
**Base:** `pr/04-evals-demo`  
**Status:** Ready for Review

---

## Summary

This PR provides complete Terraform configuration for deploying the Campaign Analyst to GCP Cloud Run with support for multiple LLM providers.

---

## What's Included

### Infrastructure Components

| Resource | Purpose |
|----------|---------|
| Cloud Run v2 Service | Containerized API with auto-scaling |
| Service Account | Minimal permissions (Secret Manager + Cloud Run) |
| Secret Manager | Secure storage for Kimi and MiniMax API keys |
| IAM Bindings | Service account access to secrets |

### Features

- **Multi-provider support**: Secrets for both Kimi and MiniMax
- **Environment configuration**: Model selection, storage paths
- **Health checks**: Startup and liveness probes
- **Auto-scaling**: 0-10 instances based on load
- **CPU idle**: Cost optimization during low traffic

---

## Quick Start

```bash
cd infra

# Initialize Terraform
terraform init

# Configure variables
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values

# Plan and apply
terraform plan
terraform apply
```

---

## Configuration

### Required Variables

```hcl
project_id = "your-gcp-project-id"
```

### Optional Variables

```hcl
region           = "us-central1"
analyzer_model   = "k2p5"
validator_model  = "MiniMax-M2.5"
```

### API Keys (at least one required)

```hcl
kimi_api_key      = "sk-..."  # Optional
minimax_api_key   = "sk-..."  # Optional
```

---

## Outputs

```bash
terraform output service_url           # Cloud Run endpoint
terraform output service_account_email # Service account
```

---

## Files Changed

- `infra/main.tf` - Complete Cloud Run v2 configuration
- `infra/terraform.tfvars.example` - Updated with multi-provider vars
- `infra/README.md` - Deployment documentation
- `tests/unit/test_terraform.py` - Updated for Cloud Run v2

---

## Test Coverage

- 4 Terraform tests passing
- Syntax validation
- Resource validation

---

## Security

- Service account with minimal permissions
- API keys stored in Secret Manager
- No secrets in Terraform state (marked sensitive)

---

## Checklist

- [x] Cloud Run v2 service
- [x] Multi-provider Secret Manager
- [x] Service account + IAM
- [x] Health check probes
- [x] Auto-scaling configuration
- [x] Documentation
- [x] Tests passing
