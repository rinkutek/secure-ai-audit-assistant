# Azure Infrastructure Setup Guide

This directory contains the Terraform Infrastructure-as-Code (IaC) necessary to deploy the **Secure AI Audit Assistant** to Microsoft Azure. We have migrated off of GCP and now utilize Azure Container Apps and Azure PostgreSQL Flexible Server.

## 🏗️ Architecture Overview
Running this Terraform script will automatically provision the following resources grouped inside a single Azure Resource Group:
- **Azure PostgreSQL Flexible Server**: Hosts the relational data (Users, Roles, Document Metadata, Audit Logs).
- **Azure Storage Account**: A blob container (`audit-vault`) for storing encrypted raw documents.
- **Azure Container App**: A serverless environment hosting our FastAPI backend container, complete with an external HTTP ingress.
- **Azure Log Analytics Workspace**: Captures all stdout/stderr logs from the backend container.

---

## 🛠️ Prerequisites
Before running this, ensure you have the following installed on your local machine:
1. **[Terraform CLI](https://developer.hashicorp.com/terraform/downloads)** (v1.5.0 or newer)
2. **[Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli)** (`az`)

---

## 🚀 Deployment Steps

### 1. Authenticate with Azure
You must log into your Azure account so Terraform can acquire the necessary credentials.
```bash
az login
```
*(If you have multiple subscriptions, make sure to set your active subscription using `az account set --subscription "<SUBSCRIPTION_ID>"`).*

### 2. Configure Variables
Terraform requires a few specific variables to run. You can provide these via a `terraform.tfvars` file or directly in the CLI. 

Create a file named `terraform.tfvars` in this folder:
```hcl
azure_resource_group_name = "rg-secure-audit"
azure_location            = "East US"

db_username               = "admin_user"
db_password               = "SuperSecretPassword123!"

# MUST be globally unique across all of Azure (lowercase letters and numbers only)
storage_account_name      = "secureauditstorage12345"

# The URL to your pushed Docker image (e.g., from Docker Hub or ACR)
backend_image_url         = "yourdockerhub/secure-ai-audit-api:latest"

# Neo4j AuraDB credentials
neo4j_uri                 = "neo4j+s://<dbid>.databases.neo4j.io"
neo4j_user                = "neo4j"
neo4j_password            = "YourSuperSecretNeo4jPassword"
```

### 3. Initialize Terraform
This command downloads the necessary Azure provider plugins into a local `.terraform` folder (which is ignored by git).
```bash
terraform init
```

### 4. Review the Plan
Run a plan to see exactly what Azure resources will be created. This will catch any syntax errors or naming conflicts before deploying.
```bash
terraform plan
```

### 5. Deploy Infrastructure
If the plan looks correct, apply it to provision the resources in Azure!
```bash
terraform apply
```
*(Type `yes` when prompted to confirm).*

---

## 🧹 Cleanup
To tear down the environment and stop all Azure billing for these resources, simply run:
```bash
terraform destroy
```
