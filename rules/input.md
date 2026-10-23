# Input

## Applies when
- The slice reads anything from outside: forms, query strings, headers, files, uploads, webhooks, messages (touch: input).
- Always on for MVP, work and enterprise profiles.

## Do
- Validate every input at the boundary: type, length, range, format, allowed values.
- Prefer allow-lists over block-lists.
- Use a schema library to validate and parse in one step.
- Encode output for where it goes: HTML, attributes, URLs, JavaScript, CSV, shell.
- Use parameterized queries or an ORM for every database call.
- Pass commands as argument lists, not as one shell string.
- For uploads: limit size, check type by content, store outside the web root, rename the file.
- For URLs the server fetches: allow-list hosts to stop SSRF.
- Resolve file paths and confirm they stay inside the allowed folder (path traversal).
- Per stack:
  - Python: `pydantic` or dataclass checks; `subprocess.run([...])` without `shell=True`.
  - Node/TS: `zod` or similar; frameworks that auto-escape templates; `execFile` over `exec`.

## Never
- Never build SQL, shell, LDAP, XPath or NoSQL queries by string concatenation with input.
- Never call `eval`, `exec`, `pickle.loads` or `yaml.load` (unsafe loader) on input.
- Never render user input as raw HTML (`innerHTML`, `dangerouslySetInnerHTML`, `|safe`).
- Never trust client-side validation alone.
- Never echo input back in error messages without encoding.

## Check
- Tests: each new input has one test with a valid value and one with a malicious or out-of-range value.
- At checkpoint 3: semgrep (when installed) for injection patterns.
- Review question: "Where is each new input validated, and how is each output encoded?"
