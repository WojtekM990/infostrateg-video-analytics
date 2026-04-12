variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "europe-central2" # Warszawa
}

variable "zone" {
  description = "GCP zone"
  type        = string
  default     = "europe-central2-a"
}

variable "cluster_name" {
  description = "Nazwa klastra GKE"
  type        = string
  default     = "infostrateg-cluster"
}

variable "node_machine_type" {
  description = "Typ maszyny dla node'ów GKE"
  type        = string
  default     = "e2-standard-2" # 2 vCPU, 8GB RAM
}

variable "node_count" {
  description = "Liczba node'ów w klastrze"
  type        = number
  default     = 2
}
