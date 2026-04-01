#!/usr/bin/env bash
set -euo pipefail

# provision_remaining.sh
# Complete Phase 1 provisioning after ACR is created
# Creates: Storage Account, Key Vault, PostgreSQL, and App Service Plan

RG=${1:-secure-ai-rg}
LOCATION=${2:-eastus}
STORAGE_NAME=${3:-secureaistorage1775009813}
KV_NAME=${4:-secureai-vault}
PG_NAME=${5:-secureai-pg}

echo "Provisioning remaining resources:"
echo "  RG: $RG"
echo "  LOCATION: $LOCATION"
echo "  STORAGE_NAME: $STORAGE_NAME"
echo "  KV_NAME: $KV_NAME"
echo "  PG_NAME: $PG_NAME"
echo ""

read -p "Proceed? (y/N): " confirm
lower_confirm=$(echo "$confirm" | tr '[:upper:]' '[:lower:]')
if [[ "$lower_confirm" != "y" ]]; then
  echo "Aborting."
  exit 0
fi

# Verify RG exists
echo "Verifying resource group exists..."
if ! az group show -n "$RG" >/dev/null 2>&1; then
  echo "Resource group $RG not found. Aborting."
  exit 1
fi

# Create Storage Account
echo ""
echo "Creating Storage Account: $STORAGE_NAME"
if az storage account show -g "$RG" -n "$STORAGE_NAME" >/dev/null 2>&1; then
  echo "Storage account already exists."
else
  az storage account create \
    -n "$STORAGE_NAME" \
    -g "$RG" \
    -l "$LOCATION" \
    --sku Standard_LRS \
    --kind StorageV2 \
    --https-only true
  echo "Storage account created."
fi

# Get storage key and create container
echo ""
echo "Creating blob container 'documents'..."
STORAGE_KEY=$(az storage account keys list -g "$RG" -n "$STORAGE_NAME" --query "[0].value" -o tsv)
az storage container create \
  --account-name "$STORAGE_NAME" \
  --name documents \
  --account-key "$STORAGE_KEY" \
  --public-access off || echo "Container may already exist"

# Upload documents if they exist
if [ -d "./data/documents" ]; then
  echo "Uploading documents to blob container..."
  az storage blob upload-batch \
    -s ./data/documents \
    -d documents \
    --account-name "$STORAGE_NAME" \
    --account-key "$STORAGE_KEY" \
    --overwrite || echo "Upload completed with possible overwrites"
  echo "Documents uploaded."
else
  echo "No ./data/documents directory found; skipping upload."
fi

# Create Key Vault
echo ""
echo "Creating Key Vault: $KV_NAME"
if az keyvault show -g "$RG" -n "$KV_NAME" >/dev/null 2>&1; then
  echo "Key Vault already exists."
else
  az keyvault create \
    -g "$RG" \
    -n "$KV_NAME" \
    -l "$LOCATION" \
    --sku standard
  echo "Key Vault created."
fi

# Prompt for and add secrets
echo ""
echo "Adding secrets to Key Vault..."

# JWT_SIGNING_KEY
if az keyvault secret show --vault-name "$KV_NAME" --name JWT_SIGNING_KEY >/dev/null 2>&1; then
  echo "JWT_SIGNING_KEY already exists in Key Vault."
else
  read -s -p "Enter JWT_SIGNING_KEY (or press Enter to auto-generate): " JWT_KEY
  echo ""
  if [ -z "$JWT_KEY" ]; then
    JWT_KEY=$(openssl rand -hex 32)
    echo "Generated JWT_SIGNING_KEY."
  fi
  az keyvault secret set --vault-name "$KV_NAME" --name JWT_SIGNING_KEY --value "$JWT_KEY" >/dev/null
  echo "JWT_SIGNING_KEY added to Key Vault."
fi

# POSTGRES_PASSWORD
if az keyvault secret show --vault-name "$KV_NAME" --name POSTGRES_PASSWORD >/dev/null 2>&1; then
  echo "POSTGRES_PASSWORD already exists in Key Vault."
else
  read -s -p "Enter POSTGRES_PASSWORD (or press Enter to auto-generate): " PG_PASS
  echo ""
  if [ -z "$PG_PASS" ]; then
    PG_PASS=$(openssl rand -base64 24)
    echo "Generated POSTGRES_PASSWORD."
  fi
  az keyvault secret set --vault-name "$KV_NAME" --name POSTGRES_PASSWORD --value "$PG_PASS" >/dev/null
  echo "POSTGRES_PASSWORD added to Key Vault."
fi

# Create PostgreSQL Flexible Server
echo ""
echo "Creating PostgreSQL Flexible Server: $PG_NAME (this can take 5-10 minutes)..."
if az postgres flexible-server show -g "$RG" -n "$PG_NAME" >/dev/null 2>&1; then
  echo "PostgreSQL server already exists."
else
  # Retrieve password from Key Vault for server creation
  PG_PASSWORD=$(az keyvault secret show --vault-name "$KV_NAME" --name POSTGRES_PASSWORD --query value -o tsv)
  
  az postgres flexible-server create \
    --resource-group "$RG" \
    --name "$PG_NAME" \
    --admin-user pgadmin \
    --admin-password "$PG_PASSWORD" \
    --sku-name Standard_B1ms \
    --location "$LOCATION" \
    --version 15 \
    --public-access 0.0.0.0/0 \
    --tier Burstable
  
  echo "PostgreSQL Flexible Server created."
fi

# Create App Service Plan
echo ""
echo "Creating App Service Plan: secureai-plan..."
if az appservice plan show -g "$RG" -n secureai-plan >/dev/null 2>&1; then
  echo "App Service Plan already exists."
else
  az appservice plan create \
    -g "$RG" \
    -n secureai-plan \
    --is-linux \
    --sku B1
  echo "App Service Plan created."
fi

echo ""
echo "========================================="
echo "Phase 1 Provisioning Complete!"
echo "========================================="
echo ""
echo "Resources created/verified:"
echo "  Resource Group: $RG"
echo "  Storage Account: $STORAGE_NAME"
echo "  Key Vault: $KV_NAME"
echo "  PostgreSQL Server: $PG_NAME"
echo "  App Service Plan: secureai-plan"
echo ""
echo "Next steps:"
echo "  1. Create service principal for GitHub Actions (Phase 2)"
echo "  2. Add GitHub secrets (Phase 3)"
echo "  3. Build and push Docker images to ACR (Phase 4)"
echo "  4. Deploy backend to App Service (Phase 5)"
echo "  5. Deploy frontend to Static Web Apps (Phase 6)"
echo ""
echo "Save these values for later:"
echo "  ACR_NAME: secureaiacrd45yib4p"
echo "  ACR_LOGIN_SERVER: secureaiacrd45yib4p.azurecr.io"
echo "  STORAGE_NAME: $STORAGE_NAME"
echo "  KV_NAME: $KV_NAME"
echo "  PG_NAME: $PG_NAME"
echo "  RESOURCE_GROUP: $RG"
echo ""
