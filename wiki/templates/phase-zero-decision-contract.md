---
program: SHARED
status: internal-template
---
# Decision contract — Phase 0 Idea Lab

Fill out this template according to [Step 0 — Idea Lab](../../docs/phase-zero-idea-lab.md). It is an internal product, not a required form or attachment. Report observable summaries, evidence and decisions; not chain of thought. Don't invent consultations, capabilities, partners, baselines or target data.

Divergence is also preserved in `brainstorm.json` (`phase-zero-brainstorm-v1`): one `primary` formulation, at least one `alternative`, non-empty fields for problem/primary target/mechanism/scale, observed provenances, and reasons for convergence. The set formed by the chosen option and the compared options must include at least one `primary` and one `alternative`; the alternative may become the preferred choice after comparison. Only when no relevant alternative exists can `alternative_exception` be used, with reason, owner and localized evidence: an internal laboratory file or a truly resolved `source_id` from the local catalog. The evidence of the exception is frozen in the packet with locator and hash. `idea_version` must match the version of `decision.json`.

With `PROCEED`, `route_handoff.candidate_id` identifies a single candidate `verified`; canonical identity (`program`, `year`, `action`, `sector`, `country`, `agency`, `role`, `round`) and `evidence` list of the handoff must coincide exactly with the candidate one. Irrelevant contextual fields are preserved as `null`, not omitted. `selected_route`, promotion and manifest use the same identity. Each reference uses only one selector among `local_snapshot`, `path`, `url`, and `source_id`, and is frozen in the package.

## Document control

| Field | Value |
|---|---|
| Idea Lab ID | |
| `idea_version` and hash/manifest | |
| Date/year and round considered | |
| Observed authors/producers | |
| Status | `draft|decision-ready|decided|closed|superseded` |
| Analytical recommendation | `PROCEED|REFINE|PIVOT|STOP` |
| Choice observed | `PROCEED|REFINE|PIVOT|STOP|not-yet-observed` |
| Origin/date of choice | Do not infer consent from silence or the brief |
| `selected_route` — program/year/action/sector/country/agency/role/round | `unknown` until verified; use explicit `null` for irrelevant fields |
| Call/agency/management | |
| Source snapshot/manifest and verification date | |
| Previous version/supersedes | |

## 1. Brief and provenance

| Element | Contents | Status | Provenance/proof | Limit or verification required |
|---|---|---|---|---|
| Desired change | | `user-stated|evidence-supported|hypothesis|proposal` | | |
| Problem and context | | | | |
| Organisation/role | | | | |
| Initial target groups | | | | |
| Geography/countries | | | | |
| Assumed duration/resources | | | | |
| Constraints/non-negotiable | | | | |

## 2. Options emerging from brainstorming

| Option | Problem addressed | Target group | Proposed mechanism | Scale | Strength | Weakness/assumption | Status |
|---|---|---|---|---|---|---|---|
| IDEA-01 | | | | | | | `active|alternative|rejected` |

Record at least one relevant alternative or justify why it cannot be constructed. A proposal does not become a confirmed fact because it appears in this table.

## 3. Route discovery or verification of the indicated call

| Route/call | Year/round | Program/action/sector | Management/Authority | Applicant/role | Target/activity | Financial regime/tier | Status | Sources and locators | Reason |
|---|---|---|---|---|---|---|---|---|---|
| | | | | | | | `candidate|conditional|incompatible|not-verified` | | |

**Preferred and alternative route:**  
**Reason for choice:**
**Conditions still open:**

Do not issue `PROCEED` with unverified current route or sources.

## 4. Priority matrix

| Priority/framework | Level `A|B|C|D` | Source/version/scope | Need connected | Concrete contribution | Expected change | Current test | Decorative risk | Next check |
|---|---|---|---|---|---|---|---|---|
| | | | | | | | | |

- Level A: route/call; B: Erasmus+ applicable; C: contextual EU framework; D: complementarity with other programs/policies.
- European Youth Goals or other frameworks become official only when the applicable source of the route refers to them; otherwise they remain context.
- Priorities from other programs do not transfer criteria, eligibility or resources.

## 5. Primary and secondary target groups

| Target group | Type | Specific problem/need | Profile and context | Route compatibility | Access/barriers/supports | Role in the project | Expected outcome | Numbers/intensity and baseline | Evidence or plan |
|---|---|---|---|---|---|---|---|---|---|
| TG-01 | `primary|secondary` | | | | | | | | |

**Distinctions:** communication audiences, stakeholders, participants and indirect beneficiaries do not automatically coincide with primary or secondary targets.

## 6. Tier, resources and scale

| Scenario | Official tier or internal scenario | Essential activities | Duration/geography/participants | Partners and capabilities | Plausible resources/costs | Outputs needed | Realistic outcomes | Scale Risk | Outcome |
|---|---|---|---|---|---|---|---|---|---|
| SCALE-01 | | | | | | | | | `plausible|refine|reject` |

**Source of any tier:**
**Minimum credible version:**  
**Reason for increasing the scale, if proposed:**

Do not call a range not included in the call a tier.

## 7. Chain from needs to impact

| ID | Need | Addressable problem/cause | Solution/mechanism | Indicative activities | Output | Result/outcome | Contribution to impact | Level | Test/Hypothesis | Next intake/test |
|---|---|---|---|---|---|---|---|---|---|---|
| CHAIN-01 | | | | | | | | `persona|organisation|community|system|european` | | |

**European added value:**
**Adoption pathway:**  
**Attribution limits:**  
**Unintended effects/external factors:**

Output, result/outcome and impact remain distinct. Phase 0 formulates a plausible chain; research and design must verify it.

## 8. Strength assessment

| Size | Result `strong|promising|fragile|unsupported` | Evidence/reason | Weakness or limitation | Consequence on design |
|---|---|---|---|---|
| Route fit | | | | |
| Preliminary award readiness | | | | |
| Relevance/priority | | | | |
| Causal coherence | | | | |
| European added value | | | | |
| Feasibility/scale | | | | |
| Target groups and participation | | | | |
| Gaps/differentiation | | | | |
| Verifiability | | | | |

These descriptors are not official scores, funding probabilities, or substitutes for award criteria.

## 9. Hard blockers, gaps and actions

| ID | Type | Description | Status | Try | Owner | Action/test | Deadline or Phase | Effect on the decision |
|---|---|---|---|---|---|---|---|---|
| GAP-01 | `hard-blocker|gap|assumption|risk` | | `confirmed|open|resolved|not-applicable` | | | | | |

Unknown data is a gap. It becomes an impediment when it blocks route selection/verification; `STOP` requires confirmed impossibility or a justified absence of alternatives.

## 10. Decision

**Analytical recommendation:** `PROCEED|REFINE|PIVOT|STOP`  
**Observed Choice:** `PROCEED|REFINE|PIVOT|STOP|not-yet-observed`
**Author/provenance/date of choice:**
**Binding of choice:** `idea_version` + `selected_route` + snapshot/manifest sources
**Brief evidence-based rationale:**  
**What remains valid:**
**What needs to change or be verified:**
**Rejected alternatives and criterion:**
**Conditions that would change the decision:**

### Follow-up actions

| Order | Action | Owner | Proof of Completion | Destination/Phase |
|---|---|---|---|---|
| 1 | | | | |

`REFINE` and `PIVOT` open a new revision of the same Idea Lab. `STOP` closes without creating `projects/<ID>/`. `PROCEED` is first a recommendation: the handoff requires an observed choice referring to the exact binding; each binding change requires a new review and a new choice.

## 11. Handoff to `idea-validation`

Compile only with recommendation `PROCEED` and choice observed on exact binding:

| Element | Reference/version | Status and limitation |
|---|---|---|
| Verified route/role/sector | | |
| Call and current sources | | |
| Brief and decision contract | | |
| Best alternative | | |
| Priority matrix | | |
| Primary/secondary target groups | | |
| Scale/tier scenario | | |
| Preliminary causal chain | | |
| Available evidence | | |
| Gap/plan/owner | | |

`idea-validation` must check preliminary eligibility and complete the route specific `award_coverage` checklist. No Phase 0 hypothesis passes as fact. With `REFINE`, `PIVOT` or `STOP` the next gate is not started.

## 12. Source register

| Claim | Source ID/URL or path | Locator | Scope | Version/date | Verified at | Status/Limit |
|---|---|---|---|---|---|---|
| | | | | | | `confirmed|interpretation|not-verified|conflict` |
