# Dependencies

## Applies when
- The slice adds, removes or upgrades a package, image or tool (touch: deps).

## Do
- Look up the current version from the registry before adding a package. Never pick a version from memory.
  - Python: `pip index versions <pkg>` or the PyPI page.
  - Node/TS: `npm view <pkg> version`.
  - Containers: the image's official tags page.
- Pin versions with a lock file (`package-lock.json`, `poetry.lock`, `uv.lock`, pinned `requirements.txt`).
- Commit the lock file.
- Prefer few, well-maintained packages. Check last release date, maintainers and license.
- Check the license fits the project (company rules may ban some).
- Run the audit for the stack and fix high findings before the slice is done.
- Produce an SBOM (CycloneDX or SPDX) for work and enterprise releases.
- Use the company's package mirror or registry when it has one.

## Never
- Never add a package to save a few lines of code.
- Never install from a random URL, a fork or a typo-like name.
- Never use `latest` or unpinned ranges in production. Production installs come only from the lock file (`npm ci`, `pip install -r` with hashes, `uv sync --frozen`).
- Never ignore a high or critical finding without a written reason and a date.
- Never run install scripts from packages you have not checked. Default to `npm ci --ignore-scripts` or `ignore-scripts=true` in `.npmrc`.

## Check
- At checkpoint 3: npm audit (Node/TS) and pip-audit (Python) report vulnerable dependencies.
- Review question: "Where did each new version number come from, and is it pinned?"
