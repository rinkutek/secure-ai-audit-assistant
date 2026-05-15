# Vendor Risk Assessment - LLM Provider

Vendor: Cloud LLM Provider
Assessment Date: 2026-04-28
Risk Rating: Medium

## Data Shared
- User prompts
- Retrieved document snippets
- System instructions
- Metadata such as user role and request timestamp

## Required Controls
- Contractual data retention limits
- No training on customer data
- Encryption in transit
- Regional data processing where applicable
- API key rotation every 90 days

## Open Questions
- Does the provider retain prompts for abuse monitoring?
- Can enterprise logging be disabled?
- Are audit logs available for model requests?

## Decision
Approved for internal audit testing only. Production approval requires Security and Legal review.
