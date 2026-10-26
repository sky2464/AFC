# Data

## Applies when
- The slice adds or changes stored data: tables, files, caches, queues, exports (touch: data).
- Always on when the project handles personal, customer, financial or health data.

## Do
- Classify each new data field: public, internal, confidential, or restricted (personal, financial, health).
- Use the company's classification labels when it has them.
- Store only what the feature needs. Drop fields you do not use.
- Encrypt in transit (TLS) always. Encrypt at rest for confidential and restricted data.
- Use the platform's managed encryption and keys; let the secrets manager hold keys.
- Set a retention period for each data set and delete or anonymize when it ends.
- Keep test and dev data fake. Use generated data, not copies of production.
- Back up data that matters, and test a restore.
- Record where restricted data lives (store, region, owner).
- Per stack:
  - Python: use migrations (Alembic, Django) for schema changes.
  - Node/TS: use migrations (Prisma, Knex, TypeORM) for schema changes.

## Never
- Never copy production personal data to a laptop or a dev environment.
- Never store card numbers; use the payment provider's tokens.
- Never put restricted data in URLs, logs, analytics or error trackers.
- Never keep data "just in case" without a retention period.
- Never store company resources or customer data in the code repo.

## Check
- While writing: the resources guard blocks company resources being written into a repo.
- Check: run the retention or delete logic live and see what it removes.
- Review question: "What class is each new field, where is it stored, and when is it deleted?"
