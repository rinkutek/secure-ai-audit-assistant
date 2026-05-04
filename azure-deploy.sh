#!/bin/bash
# Secure AI Audit Assistant - Azure Cloud-Native Deployment Script

set -e

# ==========================================
# 1. Variables (Update these if necessary)
# ==========================================
# Adding RANDOM to the resource group ensures a 100% clean slate on every run
RESOURCE_GROUP="rg-secure-audit-$RANDOM"
LOCATION="eastus" # Compute location
DB_LOCATION="centralus" # DB location
POSTGRES_SERVER_NAME="psql-secure-audit-$RANDOM"
POSTGRES_USER="dbadmin"
POSTGRES_PASSWORD="SecureDBpassword123!" 
ACR_NAME="acrsecureaudit$RANDOM"
ACA_ENV_NAME="env-secure-audit-$RANDOM"
STORAGE_ACCOUNT_NAME="stsecureaudit$RANDOM"
SHARE_NAME_CHROMA="chromadb"
SHARE_NAME_NEO4J="neo4jdata"

# LLM Configuration
MOCK_MODE="false"
OPENAI_API_KEY="your-openai-api-key-here" # REPLACE THIS WITH YOUR REAL KEY
OPENAI_CHAT_MODEL="gpt-4o-mini"

# Azure OpenAI Configuration (Alternative to OpenRouter)
AZURE_OPENAI_ENDPOINT=""
AZURE_OPENAI_KEY=""
AZURE_OPENAI_DEPLOYMENT="audit-llm"
AZURE_OPENAI_API_VERSION="2024-02-15-preview"



echo "Deploying to Resource Group: $RESOURCE_GROUP in $LOCATION"

# ==========================================
# 2. Base Infrastructure
# ==========================================
echo "Creating Resource Group..."
az group create --name $RESOURCE_GROUP --location $LOCATION

# ==========================================
# 3. PostgreSQL Flexible Server (Free Tier)
# ==========================================
echo "Provisioning Azure Database for PostgreSQL Flexible Server in $DB_LOCATION..."
# B_Standard_B1ms is part of the Azure Free Services for 12 months for students
az postgres flexible-server create \
  --location $DB_LOCATION \
  --resource-group $RESOURCE_GROUP \
  --name $POSTGRES_SERVER_NAME \
  --admin-user $POSTGRES_USER \
  --admin-password $POSTGRES_PASSWORD \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --public-access 0.0.0.0 \
  --version 16

# ==========================================
# 4. Container Registry & Environment
# ==========================================
echo "Creating Azure Container Registry..."
az acr create --resource-group $RESOURCE_GROUP --name $ACR_NAME --sku Basic --admin-enabled true
ACR_LOGIN_SERVER=$(az acr show --name $ACR_NAME --resource-group $RESOURCE_GROUP --query loginServer --output tsv)
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --resource-group $RESOURCE_GROUP --query "passwords[0].value" -o tsv)

echo "Creating Azure Container Apps Environment..."
az containerapp env create \
  --name $ACA_ENV_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION

# ==========================================
# 5. Persistent Storage (Azure Files) for ChromaDB & Neo4j
# ==========================================
echo "Setting up Storage Account and File Shares..."
az storage account create --resource-group $RESOURCE_GROUP --name $STORAGE_ACCOUNT_NAME --location $LOCATION --sku Standard_LRS --min-tls-version TLS1_2
STORAGE_KEY=$(az storage account keys list --resource-group $RESOURCE_GROUP --account-name $STORAGE_ACCOUNT_NAME --query "[0].value" -o tsv)

az storage share create --name $SHARE_NAME_CHROMA --account-name $STORAGE_ACCOUNT_NAME --account-key $STORAGE_KEY
az storage share create --name $SHARE_NAME_NEO4J --account-name $STORAGE_ACCOUNT_NAME --account-key $STORAGE_KEY

echo "Linking Azure Files to Container Apps Environment..."
az containerapp env storage set --name $ACA_ENV_NAME --resource-group $RESOURCE_GROUP --storage-name chromastorage \
  --azure-file-account-name $STORAGE_ACCOUNT_NAME --azure-file-account-key $STORAGE_KEY --azure-file-share-name $SHARE_NAME_CHROMA --access-mode ReadWrite

az containerapp env storage set --name $ACA_ENV_NAME --resource-group $RESOURCE_GROUP --storage-name neo4jstorage \
  --azure-file-account-name $STORAGE_ACCOUNT_NAME --azure-file-account-key $STORAGE_KEY --azure-file-share-name $SHARE_NAME_NEO4J --access-mode ReadWrite

# ==========================================
# 6. Deploy Databases (ChromaDB & Neo4j) to ACA
# ==========================================
echo "Deploying ChromaDB to Container Apps..."
az containerapp create \
  --name chromadb \
  --resource-group $RESOURCE_GROUP \
  --environment $ACA_ENV_NAME \
  --image chromadb/chroma:0.5.5 \
  --target-port 8000 \
  --min-replicas 1 \
  --ingress internal \
  --env-vars IS_PERSISTENT=TRUE PERSIST_DIRECTORY=/chroma/chroma ALLOW_RESET=FALSE ANONYMIZED_TELEMETRY=FALSE

echo "Deploying Neo4j to Container Apps..."
az containerapp create \
  --name neo4j \
  --resource-group $RESOURCE_GROUP \
  --environment $ACA_ENV_NAME \
  --image neo4j:5.22 \
  --target-port 7687 \
  --exposed-port 7687 \
  --transport tcp \
  --min-replicas 1 \
  --ingress internal \
  --env-vars NEO4J_AUTH=neo4j/SecureNeo4jPassword123

# ==========================================
# 7. Build and Deploy FastAPI Backend
# ==========================================
echo "Building and Pushing FastAPI Backend Image using local Docker..."
# Student subscriptions block 'az acr build', so we use local docker build -> push
az acr login --name $ACR_NAME
docker build --platform linux/amd64 -t ${ACR_LOGIN_SERVER}/secure-audit-api:latest ./backend
docker push ${ACR_LOGIN_SERVER}/secure-audit-api:latest

echo "Deploying FastAPI Backend to Container Apps..."
JWT_SECRET=$(openssl rand -hex 32)
# Append ?ssl=require for Azure PostgreSQL Flexible Server connectivity
DB_URL="postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_SERVER_NAME}.postgres.database.azure.com:5432/postgres?ssl=require"

# Fetch the dynamically generated internal FQDNs for Databases
NEO4J_FQDN=$(az containerapp show -n neo4j -g $RESOURCE_GROUP --query properties.configuration.ingress.fqdn -o tsv)
CHROMA_FQDN=$(az containerapp show -n chromadb -g $RESOURCE_GROUP --query properties.configuration.ingress.fqdn -o tsv)

az containerapp create \
  --name audit-backend-api \
  --resource-group $RESOURCE_GROUP \
  --environment $ACA_ENV_NAME \
  --image ${ACR_LOGIN_SERVER}/secure-audit-api:latest \
  --registry-server $ACR_LOGIN_SERVER \
  --registry-username $ACR_NAME \
  --registry-password $ACR_PASSWORD \
  --target-port 8080 \
  --min-replicas 1 \
  --ingress external \
  --env-vars \
      DATABASE_URL="$DB_URL" \
      JWT_SECRET_KEY="$JWT_SECRET" \
      CHROMA_HTTP_URL="http://chromadb:80" \
      NEO4J_URI="bolt://neo4j:7687" \
      NEO4J_USER="neo4j" \
      NEO4J_PASSWORD="SecureNeo4jPassword123" \
      MOCK_MODE="$MOCK_MODE" \
      MOCK_EMBEDDINGS="$MOCK_EMBEDDINGS" \
      OPENAI_API_KEY="$OPENAI_API_KEY" \
      OPENAI_CHAT_MODEL="$OPENAI_CHAT_MODEL" \
      CORS_ORIGINS="*" \
      AZURE_OPENAI_ENDPOINT="$AZURE_OPENAI_ENDPOINT" \
      AZURE_OPENAI_KEY="$AZURE_OPENAI_KEY" \
      AZURE_OPENAI_DEPLOYMENT="$AZURE_OPENAI_DEPLOYMENT" \
      AZURE_OPENAI_API_VERSION="$AZURE_OPENAI_API_VERSION"

API_FQDN=$(az containerapp show -n audit-backend-api -g $RESOURCE_GROUP --query properties.configuration.ingress.fqdn -o tsv)

echo "=========================================="
echo "✅ Backend Deployment Complete!"
echo "Your FastAPI cloud URL is: https://$API_FQDN"
echo "Before deploying to Azure Static Web Apps, remember:"
echo "1. When Azure creates the GitHub Actions .yml file for your Frontend, edit it!"
echo "2. Add this step right before the 'Build And Deploy' action:"
echo "   - name: Inject Vite Environment Variables"
echo "     run: |"
echo "       echo \"VITE_API_BASE_URL=https://\$API_FQDN\" > frontend/.env.production"
echo "3. Under the build configurations in that same .yml, change 'output_location: \"build\"' to 'output_location: \"dist\"'."
echo "=========================================="
