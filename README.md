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

# 🚀 Local Deployment

## 1) Prerequisites

Install:

- Docker Desktop, including Docker Compose v2
- Git
- Optional: Ollama, only if you want real local LLM responses instead of mock mode

Verify Docker:

```bash
docker --version
docker compose version
docker info
```

If `docker info` cannot connect to the Docker daemon, start Docker Desktop first.

## 2) Create the Environment File

```bash
cp .env.example .env
```

Generate a local JWT signing key:

```bash
openssl rand -hex 32
```

Paste the generated value into `.env`:

```env
JWT_SIGNING_KEY=<your-generated-key>
```

## 3) Choose LLM Mode

### Option A: Offline mock mode

This is the easiest local setup and does not require Ollama or internet access.

In `.env`:

```env
MOCK_MODE=true
```

### Option B: Ollama local model mode

Install and start Ollama, then pull the chat and embedding models:

```bash
ollama pull llama3.2
ollama pull nomic-embed-text
```

In `.env` for Docker Compose:

```env
MOCK_MODE=false
OPENAI_BASE_URL=http://host.docker.internal:11434/v1
OPENAI_API_KEY=local-dev
OPENAI_CHAT_MODEL=llama3.2
OPENAI_EMBEDDING_MODEL=nomic-embed-text
```

If you run the backend directly on your host machine instead of inside Docker, use:

```env
OPENAI_BASE_URL=http://localhost:11434/v1
```

## 4) Start the Full Local Stack

```bash
docker compose up --build -d
docker compose ps
```

Expected local services:

| Service | URL / Port |
| --- | --- |
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8080 |
| API Docs | http://localhost:8080/docs |
| Neo4j Browser | http://localhost:7474 |
| ChromaDB | http://localhost:8000 |
| PostgreSQL | localhost:5432 |

Neo4j login:

```text
Username: neo4j
Password: neo4jpassword
```

## 5) Run Migrations

```bash
docker compose exec api bash -lc "alembic upgrade head"
```

## 6) Seed Sample Users, Documents, and RBAC Policies

```bash
docker compose exec api bash -lc "python app/scripts/seed.py"
```

Seeded users:

```text
admin@example.com / AdminPass123!
auditor@example.com / AuditorPass123!
viewer@example.com / ViewerPass123!
```

## 7) Open and Verify the App

Open:

```text
http://localhost:5173
```

Login as:

```text
admin@example.com / AdminPass123!
```

Try this query:

```text
What is the SOC 2 evidence retention policy?
```

Expected result:

- An answer grounded in the seeded SOC 2 document
- Document citations
- Retrieval debug counts
- No `503 Service Unavailable`

## 🛡 RBAC Demonstration

Login as:

```text
viewer@example.com / ViewerPass123!
```

Ask a question about a document that the viewer role is not allowed to access.

Expected result:

```text
No results (insufficient access)
```

RBAC is enforced before LLM execution, so unauthorized snippets should not be sent to the model or shown in citations.

## 🧾 Audit Log Verification

Open:

```text
http://localhost:5173/audit-logs
```

Click **Verify Chain**.

Expected result:

```text
Verification: OK
```

This confirms the SHA-256 audit hash chain has not been tampered with.

## 📂 Where Data Is Stored

Raw uploaded documents:

```text
./data/documents
```

Inside the backend container:

```text
/data/documents
```

Structured data is stored in PostgreSQL, RBAC graph data is stored in Neo4j, and document embeddings are stored in ChromaDB.

## 🧪 Running Tests Locally

Run the full test suite:

```bash
./run_all_tests.sh
```

Backend unit tests only:

```bash
cd backend
PYTHONPATH=. python3 -m pytest tests/ --ignore=tests/integration -v
cd ..
```

Frontend unit tests only:

```bash
cd frontend
npm run test:unit
cd ..
```

Playwright end-to-end tests:

```bash
cd frontend
VITE_API_BASE_URL=http://localhost:8080 npm run test:e2e
cd ..
```

## 🧯 Troubleshooting

### Docker daemon is not running

If Docker commands fail with:

```text
Cannot connect to the Docker daemon
```

Start Docker Desktop, wait until it is ready, then run:

```bash
docker info
```

### ChromaDB embedding dimension mismatch

If `/query` returns `503 Service Unavailable` after switching between mock mode and Ollama mode, ChromaDB may still contain embeddings from the old mode. Mock embeddings use `384` dimensions, while `nomic-embed-text` uses `768`.

Reset local Docker volumes and seed again:

```bash
docker compose down -v
docker compose up --build -d
docker compose exec api bash -lc "alembic upgrade head"
docker compose exec api bash -lc "python app/scripts/seed.py"
```

This removes local dev database/vector data and recreates it using the current `.env` settings.

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
