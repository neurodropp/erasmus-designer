# Orchestrator Protocol

The orchestrator maintains a coherent application through verified steps. Its responsibility is to define the work, surface blockers, integrate data and evidence, and prevent unverified outputs from becoming premises for subsequent steps. It does not replace critical judgment with an agent count or higher scores.

## Before producing

If starting from an idea, first apply [Phase 0 — Idea Lab](phase-zero-idea-lab.md) and `config/phase-zero.json`. Work in the preliminary space managed by the workflow, without creating `project.json` or choosing a route out of habit. Brainstorming may diverge freely; convergence compares current routes, priorities with distinct authority, primary/secondary targets, causality, and the actual scale/tier. A fresh validator checks the frozen package for the idea version. Only an accepted `PROCEED` and an observed human choice on the same version, route, and source snapshot authorize promotion to the project file; `idea-validation` remains the project's first gate.

Open the project's [working memory](project-working-memory.md) with `project_memory.py context ID-COMPLETO` (or `--engine-memory` for the engine project). Retrieve active decisions, hypotheses, and open questions; record new facts and choices with status/author/evidence through `erasmus-project-memory`. References included in the mandate must remain verifiable; confirming a note does not automatically update the model or a receipt.

For connected choices, read [Wayfinder](wayfinder.md) and resume the project's frontier. Available research can be claimed by an owner; human choices require an actual decision. The memory link prevents proposed or superseded options from being used as premises. Do not generate a ticket for every simple task.

Regulatory and form maintenance is a separate mandate to `erasmus-knowledge-maintenance`, following [knowledge-maintenance.md](knowledge-maintenance.md). An update is first acquired/compared, then integrated into a candidate version of the engine and memory; after testing and a new independent judgment, it is promoted. Real project files retain their bound version until a selective migration is decided, reopening the first phase that depends on the changed inputs.

Identify the user's request, programme, year, action/sector, country/agency, relevant role, and round. If the idea is still open, keep alternatives in the Idea Lab without fixing on KA220 out of habit. Retrieve actual sources for the route and current provisions; distinguish requirements, award criteria, recommendations, contextual EU frameworks, priorities from other programmes, and examples. The form supplied by the user is KA220 Youth: preserve its scope and provisional limits, verifying them against the actual form before declaring final compliance.

Select the phase acceptance criteria and action checklist before the production mandate. Each criterion must have an observable artifact and verification method; call rules/criteria must have a located source and scope, while local checks must be identified as such. Do not let the producer choose its own approval threshold after writing the result.

Each production mandate identifies a bounded task, skill to read, input/version, sources and exclusive path, missing data, and verifiable result. Identify the shared engine root and project file `projects/<ID>/` according to [the path conventions](path-conventions.md); textual references to skills, scripts, and configurations are relative to the engine, even when the shell is working inside an application. The central model is updated only through integration: producers propose changes, they do not rewrite `project.json` in parallel. Do not request chain of thought; request checklists, evidence, assumptions, concise decisions, and blockers.

## Integrate and freeze each step

When available, the package includes the log, seal, and working-memory context, after a consistency check. Decisions and hypotheses are declared inputs, not conclusions suggested to the validator. While a review is pending, do not append to the frozen register: record the outcome after workflow record, or prepare a new package if information arrives that changes the inputs. New notes after closure do not rewrite gate history; a decision that changes an accepted product requires invalidation of the first relevant phase.

Collect the actual results, check decisive evidence, and integrate the artifacts. Run relevant deterministic checks: scope, data/IDs, arithmetic, calendar, per-instance limits, placeholders, and annex constraints. Also check educational elements that scripts cannot demonstrate, for example young people's active role in the Youth Exchange.

Create an immutable package for the attempt with manifest/hash, full identity, relevant artifacts, model/profile, original evidence, criteria, and photographed checklist. The selection must enable independent judgment: do not omit a conflicting source, an open question, or an annex that influences the decision. Do not include expectations of approval, desired scores, or the authors' chat.

Preflight rejects symlinks in project-file components before reads and writes. The gate checks the integrity of originals, manifests, derivatives, and index before copying evidence, and uses the declared general dependencies for the route. The question/instance profile is validated before building field indexes; the strict model requires `project-model-v2`. [Specifications0.2.1](repairs-0.2.1.md) and the related contracts define the updated checks.

Open a new `collaboration.spawn_agent` with `fork_turns="none"`, the [erasmus-stage-validator](../skills/erasmus-stage-validator/SKILL.md) skill, the manifest, and an exclusive path for the report. Immediately record the tool's observed ID, the authors, and previous validators: the new ID must differ from all of them. Do not reuse the validator, even to correct the same step. “External” means independent of production; an external provider is not required.

## Handle the result without complacency

Verify cited manifest/hash, actual report/hash, criteria coverage, and dispatch receipt. Tools verify structure and recorded declarations; they do not by themselves certify runtime freshness. If the tool does not allow a new session without context, declare the loss of independence and do not attest that the gate is satisfied.

| Decision | Orchestrator action |
|---|---|
| accept | Record the gate against the exact version; proceed only to dependent phases for that version |
| revise | Assign localized corrections to producers, update shared data and findings, regenerate dependencies; create a new package and use a new validator |
| blocked | Preserve the blocker and the necessary data/evidence/decision; continue independent parts and request only the indispensable information |

A validator finding may be challenged with relevant original evidence: preserve the comparison, correct the package, and request a new independent assessment without rewriting the historical report. Do not impose a quota of criticisms; do not accept a requirement as satisfied because the prose is convincing. Do not close a finding based on an author's assertion.

## Reopenings and budget

Any substantive change to a source, form identity, partner, activity, budget, KPI, or duration reopens the first dependent phase. Preserve previous outcomes for history, marking them superseded for the new version; do not treat them as approvals that remain valid. An isolated editorial change reopens only the checks actually affected; document the reason for the chosen scope.

The revision budget is explicit in the project file. Do not reset it through invalidation or hide failed attempts. At the limit, deliver the current version, findings, and blockers; a question to the user may be needed to choose among real alternatives, not to keep the cycle artificially moving. Review, repair, and QA are also steps subject to a new validator; no agent approves its own repair.

Invalidate cannot advance to a phase that has never been reached. Only still-active accepted dependencies constrain current products: blocked/revise attempts remain in history and may receive new products. Repair supersedes the previous review before the new verification; counters are retained. The receipt contains an immutable copy of the spawn observation. Dispatch checks the current phase/status before recording a session or consuming the budget.

## Closure and memory

Closure verifies the complete bundle, all relevant gates for the current version, the current form, materialized artifacts, and resolution of blocking findings. Preliminary acceptance does not demonstrate application readiness. Producing a concept for a partner or contract does not authorize submission/signature, and a legal draft does not become ready for signature solely by passing the drafting gate.

QA closure prepares the bundle for [technical human approval](human-approval.md). Record an observed decision with exact scope, evidence, and manifest/hash; changes and invalidations supersede the approval without erasing history. For an interrupted dispatch, apply [the recovery procedure](dispatch-recovery.md): lifecycle does not return budget and does not authorize reuse of the validator. The lock/CAS protects cooperative writers; JSON observations remain distinct from provider authentication.

Keep decisions and evidence in project files, and only confirmed lessons with context and scope in the wiki. Update the regulatory second brain through LWC changesets, lint, and retrieval checks; do not rewrite the corpus from a project file. Folders and responsibilities are described in [architecture.md](architecture.md).

## Framework and award criteria during production

Apply [the design method](design-methodology.md) and `config/design-methodology.json`. Before delegating, retrieve the relevant grid and define the progressive matrix criterion/subpoint → choice/ID → evidence → gaps. Handbook2026 governs the method for relevant Partnerships for Cooperation NA; Impact Tool KA1/KA2 supports Erasmus+ impact. No grid or rule is universal.

The complete design produces `design/design-plan-vN.md`; response planning produces `application/answer-plan-vN.md` (`answer-outlines` integrated, `draft` compact before writing; in compact, the plan and texts share the gate). These are versioned products: explicitly include them among the artifacts for the owning phase's gate, together with the integrated product. Gate history binds accepted step-products; do not modify them for later additions. Create a new version and invalidate at the first phase actually changed. The numerical model remains `project.json`; the plan documents diagnosis, assumptions, alternatives, SMART/RACER, and criteria coverage by ID and by question/instance. New frozen packages also include the method contract and policy with `method-*` checks; historical packages remain unchanged.
