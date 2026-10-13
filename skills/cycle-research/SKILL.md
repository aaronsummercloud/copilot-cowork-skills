---
name: cycle-research
description: >
  Phase 0 of the work cycle: check current, sourced facts before planning so outdated model
  knowledge doesn't creep into the work. Use at the start of a cycle when the task depends on
  external or time-sensitive facts (library/API versions, product features, regulations,
  policies, prices, market data), or when the user says "research this", "check the latest",
  "is this still current", "look it up", or "what's the current version". Produces a dated,
  sourced Research Brief. Do NOT use for internal-only tasks with no external facts (log a
  skip instead) or to plan the work (use cycle-plan).
---

# Overview
The model's built-in knowledge has a cutoff and goes stale. This phase finds the facts the task
depends on, checks each one against a current source, and labels anything unchecked as
`UNVERIFIED`, so it can't silently become part of the plan or the acceptance criteria.

# Entry Check
- Read the ledger. If there's none, follow `cycle-run` to create one first.
- This is the first phase, so there's no prior gate to check.
- The Cycle Contract applies: read `reference/cycle-contract.md`.

# Instructions
1. **Decide whether research is needed.** List the external or time-sensitive facts the task depends on.
   - If there are none, for example an internal-only task that relies on M365 content which `cycle-plan` will retrieve anyway, set `gates.research: skipped` with a one-line reason and exit.
2. **Write down your assumptions first.** Before searching, list what you *believe* to be true from model knowledge, one line each. These are the claims you'll check. Also read `Documents/Cowork/memory/lessons.md` for entries tagged `stale-knowledge` in this area. Those beliefs are known to have gone stale before, so always re-check them.
3. **Check each claim**, using sources in this order of preference:
   - **code:**
     1. The project itself: lockfiles and manifests such as `package-lock.json`, `requirements.txt`, `pyproject.toml`, `*.csproj`, and `go.mod`. **The installed version beats the latest docs.**
     2. The official docs and changelog for *that* version.
     3. Release notes and migration guides.
     4. Web search.
   - **m365 / general:**
     1. Authoritative sources: official docs, the regulator, the vendor.
     2. The organization's own M365 policy documents.
     3. Reputable secondary sources, via web search.
   - Prefer the most recent source. Note any conflicts between sources rather than picking one silently.
4. **Classify each claim:**
   - `CONFIRMED`: a current source agrees.
   - `CHANGED`: the source contradicts your assumption. Record the old belief and the new fact.
   - `UNVERIFIED`: no source was found or available.
5. **Save the evidence.** For any source that's likely to change or disappear, such as a vendor page or a pricing table, save a short excerpt to `<project_path>/research/F-#-<topic>.md` using `template/research-snapshot.md`. Link it from the brief.
6. **Flag the tools you couldn't use.** If web search isn't available, for example because an admin disabled web grounding, say so in the brief. In that case, any external claim you couldn't check against M365 or repo content stays `UNVERIFIED`.
7. **Show the brief** and highlight every `CHANGED` and `UNVERIFIED` item. Ask the user to resolve the `UNVERIFIED` items in one of three ways: provide a source, accept the risk, or drop the dependency.

# Output: ledger section 0
Write the ledger section using `template/ledger-section-0-research-brief.md`. Fill every `{{placeholder}}` and keep the headings, IDs, and table columns exactly as they are.

# Exit
- Researched: set `gates.research: passed` and `phase: plan`.
  `Gate research: PASSED — Next: cycle-plan — <c> confirmed, <x> changed, <u> unverified`
- Not needed: set `gates.research: skipped` and `phase: plan`.
  `Gate research: SKIPPED — Next: cycle-plan — <reason>`

# Guardrails
- Never present a model-memory claim as a fact. If it isn't sourced, it's `UNVERIFIED`.
- Every source needs a link and the date it was retrieved.
- Stay scoped to the facts this task depends on. This isn't a literature review: aim for 3–15 claims.
- Don't plan or draft anything here.
