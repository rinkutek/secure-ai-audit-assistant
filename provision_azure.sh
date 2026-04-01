#!/usr/bin/env bash
set -euo pipefail

# Ensure Azure CLI is installed
if ! command -v az >/dev/null 2>&1; then
  cat <<MSG
Azure CLI ('az') not found in PATH.
Install it on macOS using Homebrew:

  brew update
  brew install azure-cli

Then run 'az login' to authenticate and re-run this script.
MSG
  exit 1
fi

# provision_azure.sh
# Idempotent helper to provision Azure resources for the Secure AI Audit Assistant
# - Creates Resource Group, ACR, Storage Account + container, Key Vault, PostgreSQL Flexible Server
# - Uploads ./data/documents to blob storage
# - Adds secrets to Key Vault
#
# Usage:
#   chmod +x provision_azure.sh
#   ./provision_azure.sh --rg secure-ai-rg --location eastus
#
# The script prompts for sensitive values (JWT key, Postgres password) if not provided via env vars.

print_help() {
  cat <<EOF
Usage: $0 [--rg <resource-group>] [--location <location>] [--acr-name <acr>] [--storage-name <storage>] [--kv-name <keyvault>] [--pg-name <postgres>] [--frontend-static]

Options:
  --rg            Resource group name (default: secure-ai-rg)
  --location      Azure region (default: eastus)
  --acr-name      ACR name (default: secureaiacr)
  --storage-name  Storage account name (must be globally unique)
  --kv-name       Key Vault name (default: secureai-vault)
  --pg-name       Postgres server name (default: secureai-pg)
  --frontend-static  Create Azure Static Web App placeholder guidance instead of App Service
  --help          Show this help

Example:
  ./provision_azure.sh --rg secure-ai-rg --location eastus --storage-name secureaistorage$RANDOM

EOF
}

# defaults
RG=${RG:-secure-ai-rg}
LOCATION=${LOCATION:-eastus}
ACR_NAME=${ACR_NAME:-secureaiacr}
KV_NAME=${KV_NAME:-secureai-vault}
PG_NAME=${PG_NAME:-secureai-pg}
# default to Static Web Apps for frontend (you said yes)
FRONTEND_STATIC=${FRONTEND_STATIC:-true}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --rg) RG="$2"; shift 2 ;;
    --location) LOCATION="$2"; shift 2 ;;
    --acr-name) ACR_NAME="$2"; shift 2 ;;
    --storage-name) STORAGE_NAME="$2"; shift 2 ;;
    --kv-name) KV_NAME="$2"; shift 2 ;;
    --pg-name) PG_NAME="$2"; shift 2 ;;
    --frontend-static) FRONTEND_STATIC=true; shift 1 ;;
    --help) print_help; exit 0 ;;
    *) echo "Unknown arg: $1"; print_help; exit 1 ;;
  esac
done

if [[ -z "${STORAGE_NAME:-}" ]]; then
  echo "ERROR: --storage-name is required (storage account name must be globally unique, lowercase, 3-24 chars)."
  print_help
  exit 1
fi

echo "Using settings: RG=$RG, LOCATION=$LOCATION, ACR_NAME=$ACR_NAME, STORAGE_NAME=$STORAGE_NAME, KV_NAME=$KV_NAME, PG_NAME=$PG_NAME, FRONTEND_STATIC=$FRONTEND_STATIC"

# Check Azure login
AZ_ACCOUNT_ID=$(az account show --query id -o tsv 2>/dev/null || true)
if [[ -z "$AZ_ACCOUNT_ID" ]]; then
  echo "You are not logged in to Azure CLI. Run 'az login' and re-run this script."
  exit 1
fi

read -p "Proceed to create resources in subscription $AZ_ACCOUNT_ID? (y/N): " confirm
lower_confirm=$(echo "$confirm" | tr '[:upper:]' '[:lower:]')
if [[ "$lower_confirm" != "y" ]]; then
  echo "Aborting. No changes made."
  exit 0
fi

# create resource group
echo "Creating resource group $RG in $LOCATION..."
az group create -n "$RG" -l "$LOCATION"

# create ACR
echo "Creating ACR: $ACR_NAME (Standard)..."
az acr create -n "$ACR_NAME" -g "$RG" --sku Standard --output none || true

ACR_LOGIN=$(az acr show -n "$ACR_NAME" -g "$RG" --query loginServer -o tsv)
echo "ACR login server: $ACR_LOGIN"

# create Storage account
echo "Creating Storage account: $STORAGE_NAME..."
az storage account create -n "$STORAGE_NAME" -g "$RG" -l "$LOCATION" --sku Standard_LRS --kind StorageV2 --output none || true

STORAGE_KEY=$(az storage account keys list -g "$RG" -n "$STORAGE_NAME" --query [0].value -o tsv)
echo "Creating blob container 'documents' (private)..."
az storage container create --account-name "$STORAGE_NAME" --name documents --account-key "$STORAGE_KEY" --public-access off --output none || true

if [[ -d "./data/documents" ]]; then
  echo "Uploading ./data/documents -> blob container 'documents'..."
  az storage blob upload-batch -s ./data/documents -d documents --account-name "$STORAGE_NAME" --account-key "$STORAGE_KEY" --output none || true
  echo "Uploaded documents."
else
  echo "No ./data/documents directory found; skipping upload."
fi

# create Key Vault
echo "Creating Key Vault: $KV_NAME..."
az keyvault create -g "$RG" -n "$KV_NAME" -l "$LOCATION" --sku standard --output none || true

# prompt for secrets
if [[ -z "${JWT_SIGNING_KEY:-}" ]]; then
  read -s -p "Enter JWT_SIGNING_KEY (hex string) or press Enter to auto-generate: " JWT_SIGNING_KEY
  echo
fi
if [[ -z "$JWT_SIGNING_KEY" ]]; then
  JWT_SIGNING_KEY=$(openssl rand -hex 32)
  echo "Generated JWT_SIGNING_KEY: (kept in Key Vault)"
fi

if [[ -z "${POSTGRES_PASSWORD:-}" ]]; then
  read -s -p "Enter POSTGRES_PASSWORD to create for PostgreSQL server (or press Enter to auto-generate): " POSTGRES_PASSWORD
  echo
fi
if [[ -z "$POSTGRES_PASSWORD" ]]; then
  POSTGRES_PASSWORD=$(openssl rand -base64 24)
  echo "Generated a random Postgres password."
fi

echo "Adding secrets to Key Vault..."
az keyvault secret set --vault-name "$KV_NAME" --name JWT_SIGNING_KEY --value "$JWT_SIGNING_KEY" --output none
az keyvault secret set --vault-name "$KV_NAME" --name POSTGRES_PASSWORD --value "$POSTGRES_PASSWORD" --output none

echo "Creating PostgreSQL Flexible Server (small SKU). This can take several minutes..."
az postgres flexible-server create \
  --resource-group "$RG" \
  --name "$PG_NAME" \
  --admin-user pgadmin \
  --admin-password "$POSTGRES_PASSWORD" \
  --sku-name Standard_B1ms \
  --location "$LOCATION" \
  --version 15 \
  --public-access 0.0.0.0/0 \
  --output none || true

echo "Note: The server was created with a permissive public access entry (0.0.0.0/0) for convenience in dev."
echo "You should lock this down to your app's outbound IPs or VNet in production."

# create App Service plan and placeholder (optional guidance)
if [[ "$FRONTEND_STATIC" == "false" ]]; then
  echo "Creating App Service plan (B1) for container apps..."
  az appservice plan create -g "$RG" -n secureai-plan --is-linux --sku B1 --output none || true
  echo "(You can create a Web App and configure it to pull container images from ACR; see README for details.)"
else
  echo "You requested Static Web Apps for the frontend. Create an Azure Static Web App via portal or 'az staticwebapp' commands and point it to the built frontend output (dist) from your CI pipeline."
fi

echo "Provisioning complete. Summary and next steps:\n"
cat <<EOF
Resources created/used:
  Resource Group: $RG
  ACR: $ACR_NAME (login: $ACR_LOGIN)
  Storage Account: $STORAGE_NAME, container: documents
  Key Vault: $KV_NAME (JWT_SIGNING_KEY, POSTGRES_PASSWORD)
  Postgres Flexible Server: $PG_NAME (admin user: pgadmin)

Next actions (recommended):
  1) Build & push container images to ACR (local or CI). Example:
     az acr login -n $ACR_NAME
     docker build -t $ACR_LOGIN/backend:latest -f backend/Dockerfile backend
     docker push $ACR_LOGIN/backend:latest

  2) Configure your App Service or AKS to pull images from ACR. For AKS, attach ACR to the cluster.

  3) Configure your app to read secrets from Key Vault (use managed identity for production). For App Service you can link Key Vault references via app settings.

  4) Run DB migrations and seed as a one-off job in the target environment:
     alembic upgrade head
     python -m app.scripts.seed

  5) Lock down Postgres firewall rules and Key Vault access policies.

Cleanup (delete the resource group and all contained resources):
  az group delete -n $RG --yes --no-wait

EOF

echo "Done."
