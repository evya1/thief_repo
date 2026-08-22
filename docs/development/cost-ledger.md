---
artifact: development-record
id: COST-LEDGER
status: informational
owner: orchestrator
updated: 2026-08-22
---

# Development cost ledger

A running log of Claude Code session cost, one row per session. Process
metadata only: no secrets, credentials, tokens, account identifiers,
generation identifiers, or personal data.

Unlike `docs/development/session-report.md` (which records OpenRouter
billing for non-Claude workers dispatched *by* a supervising session), this
ledger tracks the supervising Claude Code session's own usage. That figure
is not exposed to the agent at run time (no billing/telemetry read access),
so each row is entered manually from the account's usage dashboard after
the session ends, and stays `TBD` until then.

| Date | Session / task | Model | Tokens (in / out) | Cost (USD) | Notes |
|---|---|---|---|---|---|
| 2026-08-22 | Thief `w_trap` trap-risk heuristic repair (`claude/trap-risk-strategy-heuristic-a79745`) | `claude-sonnet-5` | TBD | TBD | Figures pending manual entry from the account's usage dashboard; not visible to the agent during the session. |

## How to fill a `TBD` row

1. Open the account's Claude Code usage dashboard for the session's date.
2. Match the session by branch name / start time.
3. Replace `TBD` in both the token and cost columns with the reported
   figures.
4. Commit the update with a message referencing this ledger, not the
   original task's commit.
