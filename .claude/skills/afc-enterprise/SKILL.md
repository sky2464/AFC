---
name: afc-enterprise
description: Use when Flight Control works on a work or enterprise project and needs company facts, approvals, access or other people-side steps.
user-invocable: false
---

# Enterprise

Company projects need facts only the company has, and steps only people can do. Flight Control finds
out what to look for, keeps the steps in order, and drafts the messages. It will never send anything
itself. Keep every message short, ask one question per message, use plain words, and end with at most
two numbered next steps, the recommended one first.

## What to look up

When the profile is work / internal or enterprise / external-facing, ask once: "Does your company have
a wiki or internal docs?" If yes, give the exact lookups, one at a time as they become relevant:

| Look for | Why it matters |
|---|---|
| Secrets manager | where keys and passwords live (never in code) |
| Approved code hosting | where the repo is allowed to be |
| Approved app platforms | where the app may run |
| Identity / SSO setup | how users sign in (SSO, SAML, OIDC, Entra ID / AD) |
| Restricted services | tools or clouds the company bans or limits |
| Development standards | coding, review and release rules to follow |
| Request forms | how to ask for access, registrations, firewall changes |

## Where findings go

The user saves what they find into the workspace `resources/` folder. Offer "open workspace" from the
`/afc` menu (it runs `python3 -m afc open`) so they can drop files in. Then read them and write short
summaries into `plan/decisions.md`.

Resources never go into a repo: not copied, not pasted, not quoted in code or docs. The guard blocks
this ("Flight Control blocked ..."); if it fires, stop and tell the user in plain words. Paraphrases
can slip past a guard, so keep summaries in the workspace only.

## When a lookup comes back empty

That is information too. In one short message:

1. Pick a safe default (e.g. "use environment variables, not a file, until we know the secrets
   manager").
2. Record an open question in `plan/decisions.md` under the date.
3. Say which team probably owns the answer (security, identity, platform, network, legal).

## Process steps

Keep `plan/process-steps.md` current. Add a row whenever the profile or a resource implies a
people-side step, for example:

- request an Entra app registration from the identity team (before sign-in work),
- submit a firewall request (before the first deploy),
- ask the platform team for a project space on the approved platform (before deploy),
- get a security review booked (before external users).

Fill Stage, Step, Owner team and Status (`todo`, `drafted`, `sent by user`, `done`).

## Raising a step

Check `plan/process-steps.md` at the start of each slice. When the project reaches a step's stage:

1. Tell the user in one line what is needed and why now.
2. Write a **draft** email or form text: who to, subject, a short body with the project's purpose,
   what is being asked, and any IDs the form needs. Save it in the workspace `drafts/` folder and put
   its path in the Draft link column.
3. Never send it, never fill or submit the form, never sign in anywhere for the user. The user sends
   it and tells you; then set Status to `sent by user`.
4. If the step blocks the slice, pick work that is not blocked meanwhile.

End with, for example:

1. Send the draft yourself and tell me when it's done (recommended)
2. Change the draft
