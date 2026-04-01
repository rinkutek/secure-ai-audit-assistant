# Phase 6 & 7: Frontend Static Web Apps + Database Migrations

## 🎯 Current Status

✅ **Completed:**
- Phase 1-5: Azure infrastructure provisioned, images built, backend deployed to App Service
- Backend running at: https://secureai-api.azurewebsites.net

## 📋 Phase 6: Deploy Frontend to Static Web Apps

### Static Web App Created ✅

- **Resource:** `secureai-frontend`
- **Location:** East US 2
- **SKU:** Free tier
- **URL:** https://agreeable-stone-07b29b60f.1.azurestaticapps.net

### Step 1: Add Deployment Token to GitHub

1. Go to: https://github.com/rinkutek/secure-ai-audit-assistant/settings/secrets/actions
2. Click **"New repository secret"**
3. **Name:** `AZURE_STATIC_WEBAPPS_API_TOKEN`
4. **Value:** Copy this token:
   ```
   77c2fbbd24b760930c9bb110d77dfd042be0930bb6ef8ed96bb214bf9920795c01-d6f4866
   2-c1f9-4662-9d40-9f37501ac01f00f141907b29b60f
   ```
5. Click **"Add secret"**

### Step 2: Trigger Deployment

Once the secret is added, push a commit to trigger the workflow:

```bash
git add staticwebapp.config.json
git commit -m "chore: add staticwebapp config for SWA deployment"
git push origin test_cloud2
```

This will:
1. Run backend tests ✅
2. Build and push Docker images ✅
3. Deploy backend to App Service ✅
4. Build frontend React app
5. **Deploy frontend to Static Web Apps** (with new token)

### Frontend Access

Once deployed, access the frontend at:
👉 https://agreeable-stone-07b29b60f.1.azurestaticapps.net

---

## 📋 Phase 7: Run Database Migrations & Seed

### Option A: Run via Azure Container Instance (Recommended)

Create a migration container that runs `alembic upgrade head` and seed script:

```bash
# Create a migration job in App Service
az container create \
  --resource-group secure-ai-rg \
  --name secure-ai-migration \
  --image secureaiacrd45yib4p.azurecr.io/backend:f4194f05ccc462c44d525abe16ef936c0867f26f \
  --registry-login-server secureaiacrd45yib4p.azurecr.io \
  --registry-username secureaiacrd45yib4p \
  --registry-password "$(az acr credential show -n secureaiacrd45yib4p --query 'passwords[0].value' -o tsv)" \
  --environment-variables \
    DATABASE_URL="postgresql+asyncpg://pgadmin:SecurePass123@secureai-pg.postgres.database.azure.com:5432/secure_audit" \
    JWT_SIGNING_KEY="temporary-key-change-this" \
    APP_ENV="production" \
  --command-line "/bin/sh -c 'cd /app && alembic upgrade head && python -m app.scripts.seed'"
```

### Option B: Run Migrations Locally

Connect your local machine to Azure PostgreSQL and run migrations:

```bash
# Update backend/.env
export DATABASE_URL="postgresql://pgadmin:SecurePass123@secureai-pg.postgres.database.azure.com:5432/secure_audit"

# Run migrations
cd backend
alembic upgrade head

# Seed database
python -m app.scripts.seed
```

**Note:** You'll need psycopg2 or asyncpg installed locally, and the PostgreSQL server must be accessible from your network (check firewall rules).

### Verify Database Setup

Once migrations complete, verify tables were created:

```bash
# Connect to PostgreSQL and check tables
psql postgresql://pgadmin:SecurePass123@secureai-pg.postgres.database.azure.com:5432/secure_audit
\dt  # List tables
\q  # Exit
```

---

## 🚀 Integration

### Frontend → Backend Communication

The frontend (React SPA) communicates with the backend via:

```
Frontend API URL (from vite.config):
  - Default: http://localhost:8080 (dev)
  - Production: Inferred from import.meta.env.VITE_API_BASE_URL

Backend URL (from App Service):
  https://secureai-api.azurewebsites.net
```

Configure the frontend environment at deployment time by setting:

```bash
VITE_API_BASE_URL=https://secureai-api.azurewebsites.net
```

In the workflow or Static Web App environment settings.

---

## 📊 Current Architecture

```
┌─────────────────────────────────────────────┐
│ Static Web Apps (Frontend)                  │
│ https://agreeable-stone-07b29b60f...        │
│ ✅ React SPA (dist/)                        │
└────────────┬────────────────────────────────┘
             │ HTTP/HTTPS
             │ CORS enabled
┌────────────▼────────────────────────────────┐
│ App Service (Backend)                       │
│ https://secureai-api.azurewebsites.net      │
│ ✅ FastAPI + uvicorn                        │
│ ✅ Docker container from ACR                │
└────────────┬────────────────────────────────┘
             │
    ┌────────┼────────┬──────────┐
    │        │        │          │
┌───▼──┐ ┌──▼───┐ ┌──▼────┐ ┌──▼────┐
│ PgSQL│ │Neo4j │ │Chroma │ │ Blob  │
│  DB  │ │ RBAC │ │  VDB  │ │ Store │
└──────┘ └──────┘ └───────┘ └───────┘
```

---

## ✅ Next Steps

1. **Add `AZURE_STATIC_WEBAPPS_API_TOKEN` to GitHub secrets**
2. **Push commit to trigger frontend deployment**
3. **Run database migrations** (Option A or B)
4. **Test frontend login** at Static Web App URL
5. **Verify backend connectivity** and audit logs
6. **Configure Neo4j & ChromaDB** (Phase 8)

---

## 📞 Troubleshooting

### Frontend not loading
- Check Static Web App URL in browser
- Verify `AZURE_STATIC_WEBAPPS_API_TOKEN` secret is set
- Check workflow logs on GitHub

### Frontend → Backend connection fails
- Verify backend is running: `curl https://secureai-api.azurewebsites.net/health`
- Check CORS settings in backend (`config.py` CORS_ORIGINS)
- Verify `VITE_API_BASE_URL` environment variable

### Database migrations fail
- Verify PostgreSQL firewall allows your IP (if running locally)
- Check DATABASE_URL format
- Verify alembic/versions/ directory has migration files

