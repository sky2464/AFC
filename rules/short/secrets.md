# Secrets

## Do
- Read every secret from an environment variable or a secrets manager at runtime.
- Use the company's secrets manager when it has one (for example Azure Key Vault, AWS Secrets Manager, HashiCorp Vault, 1Password). Ask which one if unknown.
- Keep local values in a `.env` file. Add `.env` to `.gitignore` before the first commit.
- Commit a `.env.example` with names and placeholders only, e.g. `API_KEY=<your-key>`.
- Fail fast at startup with a clear message when a required secret is missing.
- Give each environment (dev, test, prod) its own secrets.
- Write rotation notes: who owns each secret, where it lives, how to rotate it, when it expires.
- If a secret leaks, rotate it first, then clean history. Deleting the commit is not enough.
- Per stack:
  - Python: `os.environ["API_KEY"]`; load `.env` only in local dev.
  - Node/TS: `process.env.API_KEY`; load `.env` only in local dev.
  - Containers: inject at run time (`--env-file`, orchestrator secrets), never bake into the image.

## Never
- Never put a secret in code, tests, docs, comments, commit messages, issues or chat.
- Never log a secret, or a request/response that contains one.
- Never commit `.env`, key files, certificates or credential JSON.
- Never send a secret in a URL query string.
- Never ship a real secret as a default value in code.
- Never share one secret across environments or people.
