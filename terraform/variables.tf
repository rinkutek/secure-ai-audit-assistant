variable "azure_resource_group_name" {
  description = "The name of the Azure Resource Group to create/deploy into"
  type        = string
  default     = "rg-secure-audit"
}

variable "azure_location" {
  description = "The Azure region to deploy into"
  default     = "East US"
}

variable "db_username" {
  description = "Administrator username for the PostgreSQL Flexible Server"
  type        = string
  sensitive   = true
}

variable "db_password" {
  description = "Administrator password for the PostgreSQL Flexible Server"
  type        = string
  sensitive   = true
}

variable "neo4j_uri" {
  description = "Neo4j AuraDB Connection URI (e.g., neo4j+s://<dbid>.databases.neo4j.io)"
  type        = string
}

variable "neo4j_user" {
  description = "Neo4j Username"
  type        = string
  default     = "neo4j"
}

variable "neo4j_password" {
  description = "Neo4j Password"
  type        = string
  sensitive   = true
}

variable "storage_account_name" {
  description = "Name for the Azure Storage Account (must be globally unique and lowercase)"
  type        = string
}

variable "backend_image_url" {
  description = "ACR, Docker Hub, or GHCR URL for the backend Docker image"
  type        = string
}

output "container_app_url" {
  value = azurerm_container_app.backend.latest_revision_fqdn
}

output "postgresql_server_fqdn" {
  value = azurerm_postgresql_flexible_server.postgres.fqdn
}
