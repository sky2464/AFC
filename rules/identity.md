# Identity

## Applies when
- The slice touches login, sign-up, sessions, tokens, roles or permissions (touch: auth).
- Always on for work and enterprise profiles.

## Do
- Separate authentication (who are you) from authorization (what may you do).
- Check authorization on the server for every request and every object, not only in the UI.
- Deny by default. Grant the smallest role that works.
- For work and enterprise apps, use the company's SSO. Ask which identity provider it uses.
  - Microsoft shops: Entra ID (formerly Azure AD) via OIDC; on-prem Active Directory via the company's federation (ADFS) or LDAP only when no OIDC option exists.
  - Older enterprise apps: SAML 2.0. Validate signatures, audience and expiry on every assertion.
  - Modern apps: OIDC with the authorization code flow plus PKCE.
- Use a maintained library for OIDC, SAML and JWT. Do not write your own crypto or parser.
- JWT: verify signature, `iss`, `aud`, `exp` and `nbf`. Pin the allowed algorithm. Keep lifetimes short.
- Sessions: secure, HttpOnly, SameSite cookies; rotate the session ID on login; expire idle sessions.
- Protect state-changing requests with a CSRF token or a verified Origin/Referer check (use the framework's built-in).
- Require MFA or step-up auth for admin actions, and MFA for apps that store their own passwords.
- Hash passwords (if you must store them) with Argon2id, scrypt or bcrypt.
- Map identity-provider groups to app roles in one place.
- Per stack:
  - Python: `authlib` or the provider's SDK; `pyjwt` with an explicit `algorithms=[...]`.
  - Node/TS: `openid-client`, `@azure/msal-node` for Entra ID; `jose` for JWT.

## Never
- Never accept a JWT with `alg: none` or an unpinned algorithm.
- Never trust a role, user ID or tenant ID sent by the client.
- Never store tokens in `localStorage` when a cookie works.
- Never build your own login when the company has SSO.
- Never log passwords, tokens, or full SAML assertions.
- Never change state on a GET request.
- Never skip the authorization check on "internal" endpoints.

## Check
- Check: try live that an unauthenticated request gets 401; a user without the role gets 403; user A cannot read user B's object.
- At checkpoint 3: semgrep (when installed) for weak JWT and auth patterns.
- Review question: "Which identity provider, which flow, and where is each permission checked?"
