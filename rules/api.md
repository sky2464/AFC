# API

## Applies when
- The slice adds or changes an HTTP, GraphQL or RPC endpoint (touch: api).

## Do
- CORS: allow only the exact origins that need it. List them in config.
- Add a rate limit to every public endpoint, stricter on login, sign-up and expensive calls. Return 429 with `Retry-After`.
- Use one error envelope everywhere, e.g. `{"error": {"code": "not_found", "message": "Order not found", "request_id": "..."}}`.
- Log the full error on the server; send only the safe envelope to the client.
- Put a version in the path or a header (`/v1/...`). Keep old versions until clients move.
- Set request size limits and timeouts.
- Paginate list endpoints with a maximum page size.
- Use HTTPS only. Send security headers (HSTS, `X-Content-Type-Options`, a content security policy for HTML).
- For enterprise: put public APIs behind the company's API gateway (for example Azure API Management, AWS API Gateway, Kong) and let it do auth, quotas and logging.
- Per stack:
  - Python: FastAPI/Flask CORS middleware with explicit origins; `slowapi` or gateway limits.
  - Node/TS: `cors` with an origin list; `express-rate-limit` or gateway limits.

## Never
- Never reflect the request `Origin` back as the allowed origin.
- Never allow the `null` origin.
- Never match origins by prefix, suffix or regex; compare against the exact configured list.
- Never return stack traces, SQL, file paths or internal hostnames to the client.
- Never break a published version without a new version.
- Never expose admin or debug endpoints on the public interface.
- Never return more fields than the client needs.

## Check
- Tests: an `evil-example.com` origin gets no CORS header; a disallowed origin gets no CORS header; the rate limit returns 429; an error returns the envelope with no stack trace.
- At checkpoint 3: semgrep (when installed) for permissive CORS and leaky error handlers.
- Review question: "Who may call this endpoint, how often, and what does it return on error?"
