# Containers and deploy

## Applies when
- The slice adds or changes a Dockerfile, compose file, CI pipeline, infrastructure code or deploy step (touch: deploy).

## Do
- Use a small, official base image with a pinned tag (or digest).
- Use a multi-stage build: build tools stay in the build stage.
- Run as a non-root user (`USER app`). Drop capabilities you do not need.
- Use a read-only root filesystem where the app allows it.
- Configure by environment variables. One image runs in every environment.
- Add a `.dockerignore` that excludes `.env`, `.git`, keys and test data.
- Add a health check.
- Store CI secrets in the CI system's secret store, scoped to the job that needs them.
- Prefer short-lived cloud credentials (OIDC federation from CI) over long-lived keys.
- Scan infrastructure code (Terraform, Bicep, Kubernetes YAML) before applying it.
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

## Check
- While writing: the secrets guard blocks secrets in Dockerfiles and CI files.
- At checkpoint 3: the built-in secret scan, gitleaks and semgrep (when installed) cover the deploy files.
- Review question: "Does the container run as non-root, and where do its secrets come from?"
