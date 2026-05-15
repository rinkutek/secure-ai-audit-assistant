# Incident Response Runbook - AI Audit Assistant

## Incident Types
1. Unauthorized access to restricted audit files
2. LLM response exposes sensitive data
3. Vector database outage
4. API key leakage
5. Suspicious query behavior

## Severity Levels
Critical:
- Confirmed exposure of secrets, PII, or regulated data.

High:
- Unauthorized access attempt or broken access control.

Medium:
- Service degradation, failed indexing, missing logs.

Low:
- Documentation issue or minor configuration gap.

## Response Steps
1. Triage alert and confirm impact.
2. Disable affected account or integration.
3. Preserve logs and evidence.
4. Rotate exposed secrets if needed.
5. Notify Security and Compliance.
6. Document root cause and corrective actions.

## Contacts
Security On-call: security-oncall@example.com
Compliance Lead: compliance@example.com
Platform Lead: platform@example.com
