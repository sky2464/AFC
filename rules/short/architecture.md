# Architecture

## Do
- Keep clear module boundaries. Each module has one job and a small public interface.
- Layer the code: interface (UI, API) -> application logic -> domain -> infrastructure (DB, network, files).
- Dependencies point inward. Domain code does not import the web framework or the database driver.
- Keep every file at or under 500 lines. Split by responsibility before it grows past that.
- Keep functions short and named for what they do.
- Put config in one place, read from the environment.
- Write an ADR (architecture decision record) for big decisions: a new service, a new datastore, a framework, an auth approach, a public API shape.
  - ADR format: context, decision, options considered, consequences. One page.
  - Store ADRs in the project's docs folder.
- Before coding each slice, fill a mini threat check with STRIDE categories: at most 5 rows, sized to the slice.

## Never
- Never let a file grow past 500 lines.
- Never import across layers the wrong way (domain importing UI or DB code).
- Never create circular imports between modules.
- Never make a big decision without an ADR.
- Never write a full STRIDE document for a small slice; keep it to the mini table.
