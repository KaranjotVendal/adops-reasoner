# Terraform Infrastructure

Multi-provider GCP infrastructure for Campaign Analyst (Kimi + MiniMax).

## Quick Start

```bash
cd infra

# Initialize
terraform init

# Copy and edit variables
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values

# Plan
terraform plan

# Apply
terraform apply
```

## Resources Created

- **Cloud Run v2 Service** - Containerized campaign analyst API
- **Service Account** - Dedicated SA with minimal permissions
- **Secret Manager** - Secure storage for API keys
  - `campaign-analyst-kimi-api-key` (optional)
  - `campaign-analyst-minimax-api-key` (optional)
- **IAM Bindings** - Secret access permissions

## Configuration

### Required Variables

| Variable | Description |
|----------|-------------|
| `project_id` | GCP project ID |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `region` | us-central1 | GCP region |
| `analyzer_model` | k2p5 | Default analyzer LLM |
| `validator_model` | MiniMax-M2.5 | Default validator LLM |

### API Keys

At least one API key is required:
- `kimi_api_key` - For Kimi K2.5 provider
- `minimax_api_key` - For MiniMax M2.5 provider

## Outputs

```bash
terraform output service_url          # Cloud Run endpoint
terraform output service_account_email # Service account
```

## Testing

```bash
# Validate configuration
terraform validate

# Check formatting
terraform fmt -check

# Run tests
pytest tests/unit/test_terraform.py -v
```
