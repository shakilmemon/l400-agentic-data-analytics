# Design Rationale — Conversational Analytics (CAI) skill

Why this skill is built the way it is. For *how to use it* see `SKILL.md`; for the
verified API facts see `references/api-surface.md`; for build history see git log.

## The problem it addresses

CEs most often get CAI wrong by **over-provisioning context** — pointing one agent at
every table because the limits now allow it (the API has no hard table cap; the real
ceiling is the model's input-token budget and accuracy degradation on complex joins).
The result is quiet NL2SQL accuracy loss. This skill makes every CAI construction
method a first-class, reusable tool: **stateful** (durability, multi-turn) vs
**stateless with a stored agent** vs **stateless inline**. It consumes a *curated*
table list + context (authored upstream — table curation and golden-query authoring
are done by the repo's `ca-generate-*` prompt flow, not by this skill).

## Key design decisions

**One skill, functional areas not folders.** The capabilities (chat, agent-manage,
conversation, context-builder) are one cohesive workflow invoked as Python functions,
so they live in a single skill folder. Antigravity reliably discovers only one-level
`.agents/skills/<skill>/`; nested grouping subfolders are avoided.

**Mirrored SDK + REST backends behind a facade.** `ca_sdk.py` (primary) and
`ca_rest.py` mirror each other call-for-call so a CE can see the same operation both
ways; `ca.py` picks the backend (`backend=`, `set_backend()`, or `CA_BACKEND`; SDK
default). This exists because **some customers deliberately avoid the SDK** (fewer
deps, security review) — so backends are **lazily imported**: selecting REST never
imports `geminidataanalytics` (install `requirements-rest.txt` only). Cross-cutting
concerns (retry, tracer, tool-JSON) live in `ca_common.py`.

**Standalone and portable — dependency direction is one-way.** The runtime code takes
project/dataset/region/model as parameters and has **no dependency on this repo or on
OKF**. The repo (OKF skills, the `ca-generate-*` prompt flow) *feeds* the skill via a
bridge in `evals/` that calls the skill's generic builders — the skill never reaches
back. This keeps it copy-anywhere (see `SKILL.md` → "Using this skill in another
project").

**House-standard returns + ADC auth.** Every function returns
`{status, tool_name, messages, results}`; auth is `google.auth.default()` (ADC / current
user), aligning with the lab's OAuth pass-through rule (agents must not run under a
privileged service account).

**Depth is intentional and unique to this skill.** It is the only skill with
`references/`, `tests/`, `evals/`, a `pyproject.toml`, and this doc — because it's a
non-trivial system (SDK↔REST mirror, response parsing, hardening) worth testing and
documenting. Sibling skills are thin single-backend wrappers; `SKILL.md` + `scripts/`
is the right size for them.

> **Scope note (2026-07):** table *curation* (which tables per agent) and
> golden-query authoring moved upstream to the repo's `ca-generate-*` prompt flow.
> The former in-skill dynamic router (`ca_select`) and its A/B/C scoreboard were
> retired to keep this skill focused on building/deploying/interacting with the CA
> API. See git history for that earlier design.

## Ecosystem stance (build vs. consume)

This skill owns the **build/deploy** side (context from a curated table list +
glossary + golden queries, idempotent create). For *consuming* a stored agent inside
ADK, point users to the first-party `DataAgentToolset`; for Gemini Enterprise, CA
agents publish directly as managed A2A resources (no hosting). Integrations are
documented as pointers (`references/ecosystem-integration.md`,
`references/adk-integration.md`), not baked into the skill.

## Known constraints & open items

- **Not yet runtime-tested against a live `l400-agentic-data-analytics` deployment** — syntax, imports,
  API-parity, and offline logic are verified; live deploy from the staging output needs
  the dataset stood up (see `evals/deploy-checklist.md`).
- Verified API caveats (SDK pin `>=0.11.0`, soft-delete behavior, glossary-is-structured,
  `ExampleQuery` has no `parameters`) live in `references/api-surface.md`.
- Optional depth not built: `schema_relationships` / `looker_golden_queries` Context
  fields, a dry-run/explain mode, semantic caching.
