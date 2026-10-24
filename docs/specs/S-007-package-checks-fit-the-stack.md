# S-007 — Package checks fit the stack

Size: S · Status: next · Started: - · Done: -

Finding: 8.

## Goal

The slice scan checks dependencies with the tool that matches the project. In the live run a Bun
project got `npm audit`, which needs an npm lock file, so the scan said "output unreadable" and the
dependencies went unchecked.

## You'll know it works when

- When the app has `bun.lock` (or `bun.lockb`), then the scan runs `bun audit --json` and reports its
  findings like `npm audit` does.
- When it has `package-lock.json`, then `npm audit` runs as today.
- When it has `package.json` but no lock file, then the scan says "no lock file to audit" instead of
  "output unreadable".
- When the audit tool is missing, then it shows as not installed, with the install offer.

## Out of scope

pnpm and yarn (add later the same way); fixing vulnerable packages automatically.

## Design notes

- `afc/scan.py`: choose the Node audit by lock file; add `parse_bun_audit(text) -> Check`. Check the
  current `bun audit --json` output shape against Bun's docs before writing the parser, never from
  memory; keep a recorded sample as a test fixture.
- The scan report names the tool used.

## Slices

- [ ] 1. Lock-file detection and the "no lock file" message — you'll check it by scanning a folder
      with only `package.json` (tests in `tests/test_scan.py`)
- [ ] 2. Bun audit — you'll check it by scanning php-vuln-checker and seeing a real dependency result
      (tests with a recorded `bun audit --json` sample)

## Decisions

## Shipped
