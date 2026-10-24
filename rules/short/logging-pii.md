# Logging and PII

## Do
- Write structured logs (JSON or key=value) with timestamp, level, event name and request ID.
- Use log levels on purpose: debug for dev, info for business events, warn and error for problems.
- Redact PII before it reaches the log: names, emails, phone numbers, addresses, IDs, card numbers, health data.
- Log a stable user ID or a hash, not the email.
- Write audit events for security-relevant actions: login, logout, failed login, role change, data export, delete, admin action.
- An audit event says who, what, which object, when, from where, and the result.
- Keep audit logs append-only and separate from debug logs.
- Set a log retention period that matches the data rules.
- Per stack:
  - Python: `logging` with a JSON formatter and a redaction filter.
  - Node/TS: `pino` with `redact` paths.
  - Containers: log to stdout; let the platform collect logs.

## Never
- Never log secrets, tokens, passwords, session IDs or full request bodies.
- Never log full card numbers or government IDs.
- Never use logs as the only copy of business data.
- Never leave debug logging on in production.
