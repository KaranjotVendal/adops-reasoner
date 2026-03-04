# Terraform configuration for Campaign Analyst GCP deployment
# Updated for multi-provider architecture (Kimi + MiniMax)

terraform {
  required_version = ">=1.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  # Optional: Store state in GCS for team collaboration
  # backend "gcs" {
  #   bucket = "your-terraform-state-bucket"
  #   prefix = "campaign-analyst"
  # }
}

# Variables
variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "service_name" {
  description = "Cloud Run service name"
  type        = string
  default     = "campaign-analyst"
}

variable "container_image" {
  description = "Container image URL (defaults to GHCR)"
  type        = string
  default     = ""  # Will use ghcr.io/project_id/campaign-analyst:latest
}

# API Keys (stored in Secret Manager)
variable "kimi_api_key" {
  description = "Kimi API key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "minimax_api_key" {
  description = "MiniMax API key"
  type        = string
  sensitive   = true
  default     = ""
}

# Model Configuration
variable "analyzer_model" {
  description = "Default model for analyzer"
  type        = string
  default     = "k2p5"
}

variable "validator_model" {
  description = "Default model for validator"
  type        = string
  default     = "MiniMax-M2.5"
}

variable "session_storage_path" {
  description = "Session storage path (Cloud Run uses /tmp for ephemeral)"
  type        = string
  default     = "/tmp/sessions"
}

# Provider configuration
provider "google" {
  project = var.project_id
  region  = var.region
}

# Local values
locals {
  service_name = var.service_name
  image        = var.container_image != "" ? var.container_image : "ghcr.io/${var.project_id}/${local.service_name}:latest"
  
  # Secret versions (only create if value provided)
  has_kimi_key    = var.kimi_api_key != ""
  has_minimax_key = var.minimax_api_key != ""
}

# Secret Manager secrets
resource "google_secret_manager_secret" "kimi_api_key" {
  count     = local.has_kimi_key ? 1 : 0
  secret_id = "${local.service_name}-kimi-api-key"

  labels = {
    env = "production"
    app = local.service_name
  }

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "kimi_api_key_version" {
  count       = local.has_kimi_key ? 1 : 0
  secret      = google_secret_manager_secret.kimi_api_key[0].id
  secret_data = var.kimi_api_key
}

resource "google_secret_manager_secret" "minimax_api_key" {
  count     = local.has_minimax_key ? 1 : 0
  secret_id = "${local.service_name}-minimax-api-key"

  labels = {
    env = "production"
    app = local.service_name
  }

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "minimax_api_key_version" {
  count       = local.has_minimax_key ? 1 : 0
  secret      = google_secret_manager_secret.minimax_api_key[0].id
  secret_data = var.minimax_api_key
}

# Service account for Cloud Run
resource "google_service_account" "campaign_analyst_sa" {
  account_id   = "${local.service_name}-sa"
  display_name = "Campaign Analyst Service Account"
  description  = "Service account for Campaign Analyst Cloud Run service"
}

# IAM binding for service account to access Kimi secret
resource "google_secret_manager_secret_iam_member" "kimi_secret_access" {
  count     = local.has_kimi_key ? 1 : 0
  project   = google_secret_manager_secret.kimi_api_key[0].project
  secret_id = google_secret_manager_secret.kimi_api_key[0].secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.campaign_analyst_sa.email}"
}

# IAM binding for service account to access MiniMax secret
resource "google_secret_manager_secret_iam_member" "minimax_secret_access" {
  count     = local.has_minimax_key ? 1 : 0
  project   = google_secret_manager_secret.minimax_api_key[0].project
  secret_id = google_secret_manager_secret.minimax_api_key[0].secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.campaign_analyst_sa.email}"
}

# Cloud Run service
resource "google_cloud_run_v2_service" "campaign_analyst" {
  name     = local.service_name
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.campaign_analyst_sa.email

    scaling {
      min_instances = 0
      max_instances = 10
    }

    containers {
      image = local.image

      # Environment variables
      env {
        name  = "ANALYZER_MODEL"
        value = var.analyzer_model
      }
      env {
        name  = "VALIDATOR_MODEL"
        value = var.validator_model
      }
      env {
        name  = "SESSION_STORAGE_PATH"
        value = var.session_storage_path
      }
      env {
        name  = "LOG_LEVEL"
        value = "INFO"
      }

      # Secret references
      dynamic "env" {
        for_each = local.has_kimi_key ? [1] : []
        content {
          name = "KIMI_API_KEY"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.kimi_api_key[0].secret_id
              version = "latest"
            }
          }
        }
      }

      dynamic "env" {
        for_each = local.has_minimax_key ? [1] : []
        content {
          name = "MINIMAX_API_KEY"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.minimax_api_key[0].secret_id
              version = "latest"
            }
          }
        }
      }

      resources {
        limits = {
          cpu    = "1000m"
          memory = "512Mi"
        }
        cpu_idle = true
      }

      ports {
        container_port = 8000
      }

      startup_probe {
        initial_delay_seconds = 0
        timeout_seconds       = 3
        period_seconds        = 3
        failure_threshold     = 3
        http_get {
          path = "/health"
          port = 8000
        }
      }

      liveness_probe {
        timeout_seconds   = 3
        period_seconds    = 10
        failure_threshold = 3
        http_get {
          path = "/health"
          port = 8000
        }
      }
    }
  }

  depends_on = [
    google_secret_manager_secret_iam_member.kimi_secret_access,
    google_secret_manager_secret_iam_member.minimax_secret_access,
  ]
}

# Allow unauthenticated access (for demo purposes)
# In production, restrict this to specific users or service accounts
resource "google_cloud_run_v2_service_iam_member" "all_users" {
  name     = google_cloud_run_v2_service.campaign_analyst.name
  location = google_cloud_run_v2_service.campaign_analyst.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Outputs
output "service_url" {
  description = "URL of the Cloud Run service"
  value       = google_cloud_run_v2_service.campaign_analyst.uri
}

output "service_account_email" {
  description = "Service account email"
  value       = google_service_account.campaign_analyst_sa.email
}

output "deployment_command" {
  description = "Command to deploy new revision"
  value       = "gcloud run deploy ${local.service_name} --image ${local.image} --region ${var.region}"
}
