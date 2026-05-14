# Access Control Policy

## Roles
Admin:
- Can create users, view all audit logs, configure system settings.
- Can upload and delete documents.

Auditor:
- Can upload audit evidence.
- Can query approved document collections.
- Can view own query history.

Viewer:
- Can query approved public/internal documents only.
- Cannot upload or delete files.

## Authentication
- SSO required for employees.
- MFA required for Admin users.
- Session timeout: 30 minutes of inactivity.

## Authorization Requirements
- Users must not access documents outside assigned department.
- HR documents must only be available to HR auditors and Admins.
- Finance audit reports must be restricted to Finance Audit group.

## Review Cadence
- Access review must be performed every quarter.
- Terminated employees must be removed within 24 hours.
