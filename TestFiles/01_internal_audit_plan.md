# Internal Audit Plan - Secure AI Assistant Rollout

Company: ApexFin Services Inc.
Audit Period: Q2 2026
Audit Owner: Internal Audit Team
Scope: AI assistant used by Compliance, Finance, HR, and Engineering teams.

## Objectives
- Verify access control and role-based permissions.
- Evaluate logging and monitoring of AI queries.
- Assess data privacy controls for confidential company documents.
- Confirm incident response readiness.
- Validate vendor/API key management.

## Systems in Scope
- Secure AI Audit Assistant
- PostgreSQL audit database
- Chroma vector store
- Neo4j graph database
- Azure Container Apps deployment
- Azure Key Vault / environment secrets

## Key Risks
- Unauthorized users accessing sensitive audit documents.
- LLM responses exposing confidential or regulated data.
- Missing audit trails for user activity.
- Weak secret management.
- Incomplete retention and deletion policies.

## Audit Criteria
- SOC 2 Security and Confidentiality principles
- ISO 27001 access control and logging practices
- Internal AI Governance Policy v1.2
