#!/bin/bash
set -e

echo "=========================================="
echo "🚀 Starting Full Test Suite Execution 🚀"
echo "=========================================="

echo -e "\n[1/4] Ensuring Databases are Running Cleanly..."
docker-compose down -v
export POSTGRES_PORT=5433
docker-compose up -d postgres neo4j chromadb
sleep 10

echo -e "\n[2/4] Running Backend Unit & Integration Tests (Pytest)..."
cd backend
# Make sure DB schema is up to date and seeded before testing integration
export DATABASE_URL=postgresql+asyncpg://secure:secure@localhost:5433/secure_audit
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=neo4jpassword
export CHROMA_HTTP_URL=http://localhost:8000
export DOC_STORAGE_DIR=./data/documents

alembic upgrade head
PYTHONPATH=. python3 app/scripts/seed.py

# Run pytest
PYTHONPATH=. python3 -m pytest tests/ -v
cd ..

echo -e "\n[3/4] Running Frontend Unit & Integration Tests (Vitest)..."
cd frontend
npm run test:unit
cd ..

echo -e "\n[4/4] Running Frontend End-to-End Tests (Playwright)..."
# Start the backend server in the background for live E2E tests
cd backend
export DATABASE_URL=postgresql+asyncpg://secure:secure@localhost:5433/secure_audit
export DOC_STORAGE_DIR=./data/documents
export OPENAI_BASE_URL=http://localhost:11434/v1
export MOCK_MODE=true
PYTHONPATH=. python3 -m uvicorn app.main:app --port 8080 &
BACKEND_PID=$!
sleep 3 # Give it a moment to boot up
cd ..

cd frontend
npm run test:e2e
cd ..

# Clean up the background backend server
kill $BACKEND_PID

echo -e "\n✅ All tests passed successfully!"
