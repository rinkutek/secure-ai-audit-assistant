# Secure AI Audit Assistant  
**Secure RAG + Graph-Based RBAC + Tamper-Evident Audit Log (Local Dev)**

---

## 📌 Overview

Secure AI Audit Assistant is a fully local, Dockerized application that allows auditors and compliance users to securely query internal documents using:

- ✅ Hybrid RAG (Semantic + BM25 Retrieval)
- ✅ Graph-Based RBAC (Neo4j)
- ✅ JWT Authentication
- ✅ Tamper-Evident Audit Logs (SHA-256 Hash Chain)
- ✅ Fail-Closed Security Model
- ✅ Fully Offline Mock Mode (No external LLM required)

Everything runs locally using Docker Compose.

---

## 🏗 Architecture

**Backend**
- FastAPI (Async)
- SQLAlchemy (Async)
- PostgreSQL
- Neo4j (RBAC graph)
- ChromaDB (Vector Store)

**Frontend**
- React (Vite)

**Security**
- JWT authentication
- RBAC enforced BEFORE LLM
- No unauthorized snippet leakage
- Append-only audit log with integrity verification

---

# 🚀 Quick Start (Local Setup)

## 1) Prerequisites

> **☁️ Migrating to the Cloud?** 
> If you want to deploy this stack to Microsoft Azure using a cloud-native serverless architecture, see the [Azure Migration Guide](./AZURE_MIGRATION.md) and the `azure-deploy.sh` script.

Install:

- Docker Desktop (includes Docker Compose v2)
- Git

Verify installation:

```bash
docker --version
docker compose version
```

```bash
docker --version
docker compose version
```

## 2) Create Environment File
cp .env.example .env

## 3) Generate Secure JWT Signing Key (Required)
openssl rand -hex 32
Paste output into .env: JWT_SIGNING_KEY=<your-generated-key>

## 4) Start the Full Stack
```bash
docker compose up --build -d
docker compose ps
```

Expected:

Service	Port
Frontend	http://localhost:5173

API	http://localhost:8081

Neo4j	http://localhost:7474

ChromaDB	http://localhost:8000

PostgreSQL	5432

## 5) Database Setup
```bash
docker compose exec api bash -lc "alembic upgrade head"
```

## 6) Seed Sample Data
docker compose exec api bash -lc "python -m app.scripts.seed"

Seeded users and their credentials will be printed


## 🧠 Using the Application
🔐 Login
Open: http://localhost:5173


## 🔎 Run a Query (Hybrid RAG)

Example: What are the requirements for SOC 2 evidence retention?

You should see:

Grounded answer
Citations
Retrieval debug counts

## 🛡 RBAC Demonstration

Login as viewer@example.com

Ask a restricted question (e.g., incident response policy).

Expected result:

No results (insufficient access)
No snippet leakage.
No citations.

RBAC is enforced BEFORE LLM execution.

## 🧾 Audit Log Verification

Navigate to: http://localhost:5173/audit-logs

Click Verify Chain

Expected: Verification: OK
This confirms SHA-256 hash chain integrity.

## 📂 Where Documents Are Stored

Raw documents: ./data/documents

Inside containers:/data/documents

Chunked content stored in PostgreSQL.
Embeddings stored in ChromaDB.

---

## ☁️ Cloud Deployment (Microsoft Azure)

If you are looking to deploy this application to production in the cloud, we provide full Infrastructure-as-Code (IaC) via Terraform targeted at Microsoft Azure. 

The cloud deployment provisions:
- Azure PostgreSQL Flexible Server
- Azure Container Apps (Serverless Backend)
- Azure Storage Accounts
- Azure Log Analytics

To deploy the application to Azure, please see the complete setup guide inside the `terraform/` folder:
👉 **[Azure Deployment Guide](./terraform/README.md)**
