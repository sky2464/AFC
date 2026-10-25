# Containers and deploy

## Do
- Use a small, official base image with a pinned tag (or digest).
- Use a multi-stage build: build tools stay in the build stage.
- Run as a non-root user (`USER app`). Drop all capabilities: `cap_drop: [ALL]` (compose) or `securityContext.capabilities.drop: ["ALL"]` plus `allowPrivilegeEscalation: false` (Kubernetes).
- Use a read-only root filesystem where the app allows it.
- Configure by environment variables. One image runs in every environment.
- Add a `.dockerignore` that excludes `.env`, `.git`, keys and test data.
- Add a health check.
- Store CI secrets in the CI system's secret store, scoped to the job that needs them.
- Prefer short-lived cloud credentials (OIDC federation from CI) over long-lived keys.
- Scan infrastructure code (Terraform, Bicep, Kubernetes YAML) before applying it (for example checkov or trivy config).
- Deploy to the company's approved app platform when it has one.
- Per stack:
  - Python: `python:<version>-slim`; install from the lock file.
  - Node/TS: `node:<version>-slim`; `npm ci --omit=dev`.

## Never
- Never put secrets in a Dockerfile, image layer, build argument or CI file.
- Never run the app as root or with `--privileged`.
- Never use the `latest` tag in production.
- Never open ports, buckets or storage to the public internet without a reason written down.
- Never print secrets in CI logs.
