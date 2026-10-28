---
name: afc-profile
description: Use when a project is for other people or a company and its profile has to be worked out.
user-invocable: false
---

# Profile

The project is not just for the user, so work out its profile. When done, go back to
`afc-interview`.

Work these in among the intent questions, one per message, skipping any you can already infer:

1. **Purpose** — "What are you building it for: learning, personal use, a quick prototype, an MVP, a work tool, or a product?"
2. **Users** — "Roughly how many people will use it?"
3. **Inside or outside** — "Will they be inside your company, outside it, or both?"
4. **Company** — only if it is for work: "What's your company called?"
5. **Sensitive data** — "Will it handle personal, customer, financial or health data?"
6. **Wiki** — only if there is a company: "Does your company have a wiki or internal docs?"

Decide the profile from the answers, first match wins:

| Answers | Profile |
|---|---|
| There is a company, and users are outside (or both), or more than 50 users, or sensitive data | `enterprise` |
| There is a company, otherwise | `work` |
| No company, purpose is an MVP or a product | `mvp` |
| No company, purpose is a prototype | `prototype` |
| Anything else (learning, personal use) | `personal` |

Record it: `sh bin/afc set profile <profile>`. If the result has a `warning` (for example an
iCloud-synced folder on a work project), say it in one line and offer to move the folder.
Tell the user the profile in plain words ("This is a work tool, so I'll follow work-level safety
rules"), not the label alone.

If there is a company **and** a wiki, hand off to `afc-enterprise`: it tells the user exactly what to
look for in the wiki and keeps the people-side steps. Then come back to `afc-interview`.
