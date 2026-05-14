# Privacy and Data Handling Standard

## Sensitive Data Categories
The AI assistant must detect and protect:
- Personally identifiable information (PII)
- Employee records
- Payroll data
- Customer account data
- Security incident reports
- API keys, passwords, and tokens

## Indexing Rules
- Documents with secrets must not be indexed until secrets are removed.
- HR documents require approval before ingestion.
- Financial audit evidence must be tagged with department and retention period.

## Response Rules
The assistant must:
- Cite source documents when answering audit questions.
- Refuse to reveal secrets or credentials.
- Avoid answering from unsupported context.
- State uncertainty when evidence is insufficient.

## Retention
- Query logs: 90 days
- Uploaded audit evidence: 7 years
- Temporary processing files: delete within 24 hours
