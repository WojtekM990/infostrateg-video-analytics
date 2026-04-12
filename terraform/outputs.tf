output "cluster_name" {
  description = "Nazwa klastra GKE"
  value       = google_container_cluster.primary.name
}

output "cluster_endpoint" {
  description = "Endpoint klastra GKE"
  value       = google_container_cluster.primary.endpoint
  sensitive   = true
}

output "region" {
  description = "Region klastra"
  value       = var.region
}

output "github_actions_sa_email" {
  description = "Email service account dla GitHub Actions"
  value       = google_service_account.github_actions.email
}

output "kubectl_config_command" {
  description = "Komenda do podlaczenia kubectl z klastrem"
  value       = "gcloud container clusters get-credentials ${var.cluster_name} --zone ${var.zone} --project ${var.project_id}"
}
