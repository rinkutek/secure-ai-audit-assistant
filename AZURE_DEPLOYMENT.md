# Azure Deployment Guide

This guide walks through deploying the Secure AI Audit Assistant to Azure end-to-end.

**Current Status:**
- ✅ `provision_azure.sh` created (idempotent provisioning script)
- ✅ GitHub Actions workflow created (`.github/workflows/azure-ci.yml`)
- ✅ Branch `feature/test_cloud2` created (triggers CI on push)
- ⏳ **You are here:** Set up secrets and run provisioning

---

## Prerequisites

- Azure subscription (student account with $100 credits)
- Azure CLI installed (`brew install azure-cli` on macOS)
- Logged in: `az login`
- GitHub repo at: https://github.com/rinkutek/secure-ai-audit-assistant
- Docker installed locally (for building/testing images)

---

## Phase 1: Provision Azure Resources

### 1.1 Run the provisioning script

This script creates:
- Resource Group (RG)
- Azure Container Registry (ACR)
- Azure Storage Account + private blob container + upload documents
- Azure Key Vault + secrets (JWT_SIGNING_KEY, POSTGRES_PASSWORD)
- Azure Database for PostgreSQL Flexible Server (small SKU)
- App Service Plan placeholder (can create Web App manually later)

**Command:**
```bash
STORAGE_NAME=secureaistorage$(date +%s)
chmod +x provision_azure.sh
./provision_azure.sh --rg secure-ai-rg --location eastus --storage-name $STORAGE_NAME
```

When prompted:
- Confirm subscription: type `y`
- JWT_SIGNING_KEY: press Enter to auto-generate (or paste your own)
- POSTGRES_PASSWORD: press Enter to auto-generate

**Expected output:**
- Resource Group created: `secure-ai-rg`
- ACR login server (e.g., `secureaiacr.azurecr.io`)
- Storage account name: `$STORAGE_NAME`
- Key Vault: `secureai-vault`
- PostgreSQL server: `secureai-pg`
- Secrets stored in Key Vault

**Note:** The script opens Postgres to 0.0.0.0/0 for dev convenience. Lock it down in production:
```bash
az postgres flexible-server firewall-rule create \
  -g secure-ai-rg -n secureai-pg -r AllowAppSubnet \
  --start-ip-address <your-app-ip> --end-ip-address <your-app-ip>
```

### 1.2 Save resource names for later

After the script completes, note these values (they'll appear in output):
- **ACR_LOGIN_SERVER**: e.g., `secureaiacr.azurecr.io`
- **RESOURCE_GROUP**: `secure-ai-rg`
- **ACR_NAME**: `secureaiacr`
- **STORAGE_NAME**: `secureaistorage<timestamp>`
- **POSTGRES_SERVER**: `secureai-pg`
- **POSTGRES_ADMIN_USER**: `pgadmin`

---

## Phase 2: Create Azure Service Principal for GitHub Actions

### 2.1 Generate service principal credentials

```bash
az ad sp create-for-rbac \
  --name "github-actions-secure-ai" \
  --role contributor \
  --scopes /subscriptions/46b5c17e-4523-4d11-b840-c056bf1f056e/resourceGroups/secure-ai-rg \
  --sdk-auth
```

This prints JSON like:
```json
{
  "clientId": "...",
  "clientSecret": "...",
  "subscriptionId": "...",
  "tenantId": "...",
  "activeDirectoryEndpointUrl": "https://login.microsoftonline.com",
  "resourceManagerEndpointUrl": "https://management.azure.com/",
  "activeDirectoryGraphResourceId": "https://graph.microsoft.com/",
  "sqlManagementEndpointUrl": "https://management.azure.com:8443/",
  "galleryEndpointUrl": "https://gallery.azure.com/",
  "managementEndpointUrl": "https://management.azure.com/"
}
```

**Copy the entire JSON** — you'll paste it as a GitHub secret.

---

## Phase 3: Set Up GitHub Secrets

### 3.1 Add secrets to your GitHub repository

Go to: **GitHub repo** > **Settings** > **Secrets and variables** > **Actions** > **New repository secret**

Add these secrets one by one:

| Secret Name | Value |
|---|---|
| `AZURE_CREDENTIALS` | Paste the entire JSON from step 2.1 |
| `ACR_NAME` | `secureaiacr` (from provisioning script output) |
| `AZURE_WEBAPP_NAME` | (optional) Web App name if deploying backend to App Service |
| `AZURE_APP_SERVICE_PLAN` | (optional) `secureai-plan` if creating new Web App |
| `AZURE_STATIC_WEBAPPS_API_TOKEN` | (optional) Token from Static Web App deployment center |

**At minimum, set:**
- `AZURE_CREDENTIALS`
- `ACR_NAME`

---

## Phase 4: Build and Push Images to ACR (Local or via CI)

### Option A: Local Build & Push

1. Log in to ACR:
```bash
az acr login --name secureaiacr
```

2. Build backend image:
```bash
ACR_LOGIN=secureaiacr.azurecr.io
docker build -t $ACR_LOGIN/backend:latest -f backend/Dockerfile backend
docker push $ACR_LOGIN/backend:latest
```

3. Build frontend image:
```bash
docker build -t $ACR_LOGIN/frontend:latest -f frontend/Dockerfile frontend
docker push $ACR_LOGIN/frontend:latest
```

### Option B: Trigger via GitHub Actions (CI)

1. Make sure `AZURE_CREDENTIALS` and `ACR_NAME` secrets are set (Phase 3).
2. Commit and push to `feature/test_cloud2` or `main`:
```bash
git add -A
git commit -m "Ready for Azure deployment"
git push
```
3. GitHub Actions will run the `azure-ci.yml` workflow:
   - Runs backend tests
   - Builds and pushes images to ACR
   - (Optional) deploys to Static Web Apps if token is set
   - (Optional) deploys to App Service if webapp name is set

4. Monitor progress in **GitHub** > **Actions** tab.

---

## Phase 5: Deploy Backend to Azure

### Option A: Deploy to Azure App Service (Containers)

#### 5A.1 Create App Service Web App

```bash
az webapp create \
  --resource-group secure-ai-rg \
  --plan secureai-plan \
  --name secureai-api \
  --deployment-container-image-name secureaiacr.azurecr.io/backend:latest \
  --docker-registry-server-url https://secureaiacr.azurecr.io \
  --docker-registry-server-user <acr-admin-user> \
  --docker-registry-server-password <acr-admin-password>
```

Or use managed identity (recommended for production):
```bash
# Create system-assigned managed identity
az webapp identity assign -g secure-ai-rg -n secureai-api

# Grant ACR pull permissions
az role assignment create \
  --assignee <managed-identity-principal-id> \
  --role AcrPull \
  --scope /subscriptions/46b5c17e-4523-4d11-b840-c056bf1f056e/resourceGroups/secure-ai-rg/providers/Microsoft.ContainerRegistry/registries/secureaiacr
```

#### 5A.2 Configure App Settings (Environment Variables)

```bash
az webapp config appsettings set \
  --resource-group secure-ai-rg \
  --name secureai-api \
  --settings \
    DATABASE_URL="postgresql://pgadmin:<password>@secureai-pg.postgres.database.azure.com:5432/secureai?sslmode=require" \
    JWT_SIGNING_KEY="@Microsoft.KeyVault(SecretUri=https://secureai-vault.vault.azure.net/secrets/JWT_SIGNING_KEY/)" \
    POSTGRES_PASSWORD="@Microsoft.KeyVault(SecretUri=https://secureai-vault.vault.azure.net/secrets/POSTGRES_PASSWORD/)" \
    NEO4J_URI="neo4j+s://<neo4j-aura-host>:7687" \
    NEO4J_PASSWORD="@Microsoft.KeyVault(SecretUri=https://secureai-vault.vault.azure.net/secrets/NEO4J_PASSWORD/)" \
    CHROMA_API_URL="http://<chroma-container-host>:8000"
```

Replace placeholders with actual values. For Key Vault references, grant the web app's managed identity read access:
```bash
PRINCIPAL_ID=$(az webapp identity show -g secure-ai-rg -n secureai-api --query principalId -o tsv)
az keyvault set-policy -n secureai-vault --object-id $PRINCIPAL_ID --secret-permissions get list
```

#### 5A.3 Deploy Image

To update the image (after pushing a new one to ACR):
```bash
az webapp config container set \
  --resource-group secure-ai-rg \
  --name secureai-api \
  --docker-custom-image-name secureaiacr.azurecr.io/backend:latest \
  --docker-registry-server-url https://secureaiacr.azurecr.io
```

Or use the GitHub Actions workflow (it does this automatically if `AZURE_WEBAPP_NAME` secret is set).

### Option B: Deploy to AKS (Kubernetes)

(See section **Phase 6** below for Kubernetes manifests and deployment steps.)

---

## Phase 6: Deploy Frontend to Azure Static Web Apps

### 6.1 Create Static Web App (Portal or CLI)

**Via Portal:**
1. Go to Azure Portal > Create Resource > Static Web App
2. Enter name: `secureai-web`
3. Connect to GitHub > Authorize > Select repo `secure-ai-audit-assistant`, branch `feature/test_cloud2`
4. Build preset: select "Custom" or "React" (depending on your setup)
5. App location: `frontend`
6. Output location: `frontend/dist`

**Via CLI:**
```bash
az staticwebapp create \
  --resource-group secure-ai-rg \
  --name secureai-web \
  --source https://github.com/rinkutek/secure-ai-audit-assistant \
  --branch feature/test_cloud2 \
  --app-location frontend \
  --output-location frontend/dist \
  --token <github-token>
```

### 6.2 Get the deployment token

```bash
az staticwebapp secrets list \
  --resource-group secure-ai-rg \
  --name secureai-web \
  --query "properties.apiKey" -o tsv
```

Add this as the GitHub secret `AZURE_STATIC_WEBAPPS_API_TOKEN`.

### 6.3 Verify deployment

After adding the token, push a commit to trigger the workflow:
```bash
git commit --allow-empty -m "Trigger Static Web Apps deployment"
git push
```

The GitHub Actions workflow will build the frontend and deploy it to Static Web Apps.

---

## Phase 7: Run Database Migrations & Seed

### 7.1 Get Postgres connection details

```bash
# Get the FQDN
az postgres flexible-server show \
  --resource-group secure-ai-rg \
  --name secureai-pg \
  --query "fullyQualifiedDomainName" -o tsv
```

### 7.2 Run migrations in a temporary container

Option A: Use Docker locally (if you have the backend image):
```bash
docker run --rm \
  -e DATABASE_URL="postgresql://pgadmin:<password>@<postgres-fqdn>:5432/secureai?sslmode=require" \
  -e JWT_SIGNING_KEY="<your-jwt-key>" \
  secureaiacr.azurecr.io/backend:latest \
  bash -c "alembic upgrade head && python -m app.scripts.seed"
```

Option B: Use Azure Container Instances (ACI) for a one-off job:
```bash
az container create \
  --resource-group secure-ai-rg \
  --name backend-migrate \
  --image secureaiacr.azurecr.io/backend:latest \
  --registry-login-server secureaiacr.azurecr.io \
  --environment-variables \
    DATABASE_URL="postgresql://pgadmin:<password>@<postgres-fqdn>:5432/secureai?sslmode=require" \
    JWT_SIGNING_KEY="<your-jwt-key>" \
  --command-line "alembic upgrade head && python -m app.scripts.seed" \
  --no-wait
```

### 7.3 Verify migrations

Connect to Postgres and check tables:
```bash
psql -h <postgres-fqdn> -U pgadmin -d secureai -c "\dt"
```

Expected tables: `users`, `audit_logs`, `documents`, etc. (as defined in `backend/app/db/models.py`).

---

## Phase 8: Configure Neo4j and ChromaDB

### 8.1 Neo4j Options

**Option A: Neo4j AuraDB (Managed, Recommended)**
1. Go to https://neo4j.com/cloud/aura/
2. Create a free or paid instance
3. Copy connection URI and password
4. Add to Key Vault:
```bash
az keyvault secret set --vault-name secureai-vault --name NEO4J_URI --value "<neo4j-uri>"
az keyvault secret set --vault-name secureai-vault --name NEO4J_PASSWORD --value "<password>"
```
5. Update app settings with these secrets

**Option B: Self-Hosted Neo4j in AKS**
(Requires Kubernetes manifests; see Phase 9 below.)

### 8.2 ChromaDB Options

**Option A: Container Instance / Container Apps**
Deploy ChromaDB as a container:
```bash
az container create \
  --resource-group secure-ai-rg \
  --name chroma-server \
  --image chromadb/chroma:latest \
  --ports 8000 \
  --environment-variables CHROMA_HOST=0.0.0.0 \
  --no-wait
```

Get the IP:
```bash
az container show -g secure-ai-rg -n chroma-server --query ipAddress.ip -o tsv
```

Update app settings: `CHROMA_API_URL=http://<chroma-ip>:8000`

**Option B: AKS StatefulSet**
(See Phase 9 below for Kubernetes deployment.)

---

## Phase 9: (Optional) Deploy to AKS (Kubernetes)

If you prefer Kubernetes over App Service, generate Kubernetes manifests. This guide focuses on App Service for simplicity; for AKS:

1. Create AKS cluster:
```bash
az aks create -g secure-ai-rg -n secureai-aks --node-count 3 --attach-acr secureaiacr
```

2. Get credentials:
```bash
az aks get-credentials -g secure-ai-rg -n secureai-aks
```

3. Deploy manifests (backend, frontend, chroma, etc.):
```bash
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/chroma-statefulset.yaml
```

(Contact me for sample manifests if you choose this route.)

---

## Phase 10: Test End-to-End

### 10.1 Access the frontend

Open the Static Web App URL (printed after deployment) or your custom domain:
```
https://secureai-web.azurestaticapps.net
```

### 10.2 Login and test

1. Login with seeded user (from `app.scripts.seed`): e.g., `admin@example.com` / password
2. Run a query: "What are the requirements for SOC 2 evidence retention?"
3. Verify response includes citations and retrieval debug counts
4. Test RBAC: login as `viewer@example.com` and try a restricted query (should get no results)
5. Visit audit logs: `/audit-logs`
6. Click "Verify Chain" — should print "Verification: OK" if hash chain is intact

### 10.3 Monitor logs

**App Service logs:**
```bash
az webapp log tail -g secure-ai-rg -n secureai-api
```

**PostgreSQL slow queries:**
```bash
az postgres flexible-server logs list -g secure-ai-rg -n secureai-pg
```

---

## Phase 11: Cleanup (Cost Control)

**Important:** To avoid unexpected charges, delete resources when done:

```bash
# Delete entire resource group (includes all resources)
az group delete -n secure-ai-rg --yes --no-wait

# Or delete individual resources
az webapp delete -g secure-ai-rg -n secureai-api --yes
az staticwebapp delete -g secure-ai-rg -n secureai-web --yes
az postgres flexible-server delete -g secure-ai-rg -n secureai-pg --yes
az keyvault delete -g secure-ai-rg -n secureai-vault
az acr delete -g secure-ai-rg -n secureaiacr
az storage account delete -g secure-ai-rg -n $STORAGE_NAME
```

---

## Troubleshooting

### Images not found in ACR
- Verify ACR login: `az acr login -n secureaiacr`
- Check images: `az acr repository list -n secureaiacr`
- Rebuild and push: `docker build -t $ACR_LOGIN/backend:latest -f backend/Dockerfile backend && docker push $ACR_LOGIN/backend:latest`

### Postgres connection fails
- Check firewall: `az postgres flexible-server firewall-rule list -g secure-ai-rg -n secureai-pg`
- Verify credentials in app settings
- Check SSL requirement: database URL should include `?sslmode=require`

### GitHub Actions workflow fails
- Check logs: GitHub repo > Actions > Select failed run
- Verify secrets are set: Settings > Secrets
- Re-run job: Click "Re-run failed jobs"

### App Service won't start
- Check logs: `az webapp log tail -g secure-ai-rg -n secureai-api`
- Verify environment variables are set
- Check that image exists in ACR

### Static Web App shows 404
- Verify build output location is `frontend/dist` (configured in Static Web App)
- Check workflow logs to ensure build succeeded
- Confirm API backend URL is accessible (check frontend API config)

---

## Next Steps

1. **Run provisioning:** Execute `./provision_azure.sh`
2. **Create service principal:** Run `az ad sp create-for-rbac --sdk-auth ...`
3. **Set GitHub secrets:** Add `AZURE_CREDENTIALS` and `ACR_NAME` to repo secrets
4. **Push to test branch:** `git commit && git push` to trigger CI
5. **Monitor Actions:** Watch GitHub Actions to build and push images
6. **Deploy backend:** Create Web App or AKS cluster and configure
7. **Deploy frontend:** Create Static Web App and wire deployment token
8. **Run migrations:** Execute alembic and seed in target environment
9. **Test:** Access frontend, login, run queries, verify RBAC and audit logs
10. **Cleanup:** Delete resource group when done to preserve credits

---

## Cost Estimate (Student Credits)

Based on $100 credits and low-usage student deployment:

| Service | SKU | Cost/Month |
|---|---|---|
| PostgreSQL Flexible Server | Standard_B1ms (1 vCore, 2GB RAM) | ~$15 |
| Container Registry (Standard) | Standard | ~$10 |
| App Service (B1) | Basic | ~$15 |
| Static Web Apps | Free tier | $0 |
| Storage Account | Standard LRS | ~$2 |
| Key Vault | Standard | ~$0.60 |
| **Total** | | ~**$42/month** |

**Credits last:** ~2–3 months for a development/testing environment.

---

## References

- [Azure CLI Reference](https://learn.microsoft.com/cli/azure/)
- [GitHub Actions Azure Login](https://github.com/Azure/login)
- [Azure Static Web Apps](https://docs.microsoft.com/azure/static-web-apps/)
- [Azure App Service for Containers](https://docs.microsoft.com/azure/app-service/containers/)
- [PostgreSQL Flexible Server](https://docs.microsoft.com/azure/postgresql/flexible-server/)

