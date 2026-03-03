# Terraform configuration for Campaign Analyst GCP deployment
terraform {
  required_version = ">=1.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

# Variables - fill in your values
variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "service_account_email" {
  description = "Service account email for Cloud Run"
  type        = string
}

# Environment variables for Cloud Run
variable "minimax_api_key" {
  description = "MiniMax API key (stored in Secret Manager)"
  type        = string
  sensitive   = true
}

# Provider configuration
provider "google" {
  project = var.project_id
  region  = var.region
}

# Local values
locals {
  service_name = "campaign-analyst"
  image        = "ghcr.io/${var.project_id}/${local.service_name}:latest"
}

# Secret Manager secret for API key
resource "google_secret_manager_secret" "minimax_api_key" {
  secret_id = "${local.service_name}-minimax-api-key"

  labels = {
    env = "production"
  }

  replication {
    auto_create_location = true
  }
}

resource "google_secret_manager_secret_version" "minimax_api_key_version" {
  secret = google_secret_manager_secret.minimax_api_key.id
  secret_data = var.minimax_api_key
}

# Service account for Cloud Run
resource "google_service_account" "campaign_analyst_sa" {
  account_id   = "${local.service_name}-sa"
  display_name = "Campaign Analyst Service Account"
  description  = "Service account for Campaign Analyst Cloud Run service"
}

# IAM binding for service account to access secrets
resource "google_secret_manager_secret_iam_member" "secret_access" {
  project  = google_secret_manager_secret.minimax_api_key.project
  secret_id = google_secret_manager_secret.minimax_api_key.secret_id
  role     = "roles/secretmanager.secretAccessor"
  member   = "serviceAccount:${google_service_account.campaign_analyst_sa.email}"
}

# Cloud Run service
resource "google_cloud_run_service" "campaign_analyst" {
  name     = local.service_name
  location = var.region

  template {
    spec {
      containers {
        image = local.image

        env {
          name  = "MINIMAX_API_KEY"
          value = "secrets://${google_secret_manager_secret.minimax_api_key.secret_id}"
        }

        resources {
          limits = {
            cpu    = "1000m"
            memory = "512Mi"
          }
        }
      }

      service_account_name = google_service_account.campaign_analyst_sa.email
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
}

# Allow unauthenticated access for demo purposes
resource "google_cloud_run_service_iam_member" "all_users" {
  service  = google_cloud_run_service.campaign_analyst.name
  location = google_cloud_run_service.campaign_analyst.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Outputs
output "service_url" {
  description = "URL of the Cloud Run service"
  value       = google_cloud_run_service.campaign_analyst.status[0].url
}

output "service_account_email" {
  description = "Service account email"
  value       = google_service_account.campaign_analyst_sa.email
}
