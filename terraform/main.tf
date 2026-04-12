terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

# GCS Bucket — tanie przechowywanie przetworzonych wideo
# Worker uploaduje tu wyniki, Dashboard pobiera i odtwarza
resource "google_storage_bucket" "video_output" {
  name          = "infostrateg-video-output-${var.project_id}"
  location      = var.region
  force_destroy               = true
  uniform_bucket_level_access = true

  lifecycle_rule {
    condition {
      age = 30 # Kasuj pliki starsze niż 30 dni
    }
    action {
      type = "Delete"
    }
  }
}

# Uprawnienia dla node'ów GKE do odczytu i zapisu bucketu
resource "google_storage_bucket_iam_member" "gke_nodes_bucket_access" {
  bucket = google_storage_bucket.video_output.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${data.google_compute_default_service_account.default.email}"
}

data "google_compute_default_service_account" "default" {
  project = var.project_id
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# -------------------------------------------------
# VPC — dedykowana sieć dla klastra
# -------------------------------------------------
resource "google_compute_network" "vpc" {
  name                    = "infostrateg-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "subnet" {
  name          = "infostrateg-subnet"
  ip_cidr_range = "10.0.0.0/18"
  region        = var.region
  network       = google_compute_network.vpc.id

  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = "10.48.0.0/14"
  }

  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = "10.52.0.0/20"
  }
}

# -------------------------------------------------
# GKE Cluster
# -------------------------------------------------
resource "google_container_cluster" "primary" {
  name     = var.cluster_name
  location = var.zone

  network    = google_compute_network.vpc.name
  subnetwork = google_compute_subnetwork.subnet.name

  # Usuwamy domyślny node pool — tworzymy własny poniżej
  remove_default_node_pool = true
  initial_node_count       = 1

  ip_allocation_policy {
    cluster_secondary_range_name  = "pods"
    services_secondary_range_name = "services"
  }

  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }
}

resource "google_container_node_pool" "primary_nodes" {
  name       = "infostrateg-node-pool"
  location   = var.zone
  cluster    = google_container_cluster.primary.name
  node_count = var.node_count

  node_config {
    machine_type = var.node_machine_type
    disk_size_gb = 50
    disk_type    = "pd-standard"

    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]

    labels = {
      project = "infostrateg"
    }
  }

  autoscaling {
    min_node_count = 1
    max_node_count = 4
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }
}

# -------------------------------------------------
# Service Account dla GitHub Actions (push do GKE)
# -------------------------------------------------
resource "google_service_account" "github_actions" {
  account_id   = "github-actions-sa"
  display_name = "GitHub Actions Service Account"
}

resource "google_project_iam_member" "github_actions_gke" {
  project = var.project_id
  role    = "roles/container.developer"
  member  = "serviceAccount:${google_service_account.github_actions.email}"
}
