from locust import HttpUser, task, between
import json

class SecureAuditAssistantLoadTest(HttpUser):
    # Simulate a user reading answers for 2 to 5 seconds before making another query
    wait_time = between(2, 5)

    def on_start(self):
        """
        Executed when a simulated user starts.
        We must log in to get a JWT access token since the endpoints are secure.
        """
        # NOTE: You MUST change these credentials to a test user that actually exists in your PostgreSQL DB.
        login_data = {
            "email": "admin@example.com", 
            "password": "SecurePassword123"
        }
        
        # Depending on how the routers are mounted in main.py, "auth" is usually mounted on /auth or /api/auth
        with self.client.post("/auth/login", json=login_data, catch_response=True) as response:
            if response.status_code == 200:
                token = response.json().get("access_token")
                # Bind the JWT token to this simulated user's session headers
                self.client.headers.update({"Authorization": f"Bearer {token}"})
                response.success()
            else:
                response.failure(f"Failed to login: {response.text}")

    @task(3)
    def submit_rag_query(self):
        """
        Simulate an auditor submitting a question to the system.
        This hits the FastAPI -> Embeddings -> ChromaDB -> Neo4j -> LLM pipeline.
        Weight is 3 (happens 3x more often than other tasks).
        """
        query_payload = {
            "query": "What are the access control policies for financial audits?"
        }
        
        # Hits the RAG endpoint
        with self.client.post("/query", json=query_payload, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                # If Neo4j RBAC denies or LLM fails, it catches the error
                response.failure(f"Query Failed: {response.status_code} - {response.text}")
