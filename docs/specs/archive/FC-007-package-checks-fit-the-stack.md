# FC-007 — Package checks fit the stack

Size: S · Status: done · Started: 2026-10-24 · Done: 2026-10-24

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

- [x] 1. Lock-file detection and the "no lock file" message — you'll check it by scanning a folder
      with only `package.json` (tests in `tests/test_scan.py`)
- [x] 2. Bun audit — you'll check it by scanning php-vuln-checker and seeing a real dependency result
      (tests with a recorded `bun audit --json` sample)

## Decisions

- 2026-10-24: Built on the toolkit branch (`77eda62`), brought onto `dev` as `647a474` during FC-010
  slice 7. Two choices differ from the design notes: a Bun project is recognised by `bun.lock` or
  `bun.lockb`, and a missing npm lock file is recognised from npm's own `ENOLOCK` error, not by
  looking for `package-lock.json`. Checked against real output on 2026-10-24: `bun audit --json`
  (Bun 1.3.14) prints its banner on stderr and `{package: [advisories]}` on stdout, and exits 1 when
  it finds problems (the scan judges stdout, so that is fine); `npm audit --json` on a folder with
  only `package.json` reports `ENOLOCK`. Scanning a scratch copy of php-vuln-checker's lock file gave
  "0 vulnerable deps"; a project with lodash 4.17.15 gave "1 vulnerable deps (3 high)", now recorded
  as `tests/fixtures/bun-audit-real-lodash.json`. Both slices are done; close this spec with
  `plan start` then `plan done` once FC-010 is finished.

## Shipped

Shipped 2026-10-24. Slices: 2.
