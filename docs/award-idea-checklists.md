# Award Criteria at the Idea Validation Stage

Every 2026 engine route has a specific checklist, with explicit variants where the rubric, lot, or role changes. Reusable sheets are in `wiki/checklists/award-criteria/`; verified source data are in `config/award-criteria/`. They derive from complete sections of the relevant guides, with physical PDF pages numbered from 1. They do not certify that the call is up to date, that Italian priorities have been checked, or that the effective form limits have been verified.

Official criteria and their subpoints are rewritten separately from the engine's operational questions. Maximum scores belong only to official criteria; IDs and control questions are internal. There are no sub-scores, official idea scores, or funding probabilities. National Erasmus+ rubrics do not apply to EACEA or ESC actions. The user's KA220 DOCX does not become an official form merely because some extracted criteria are normative.

## Selecting the Checklist

Identify the programme, year, action, sector, agency, and relevant selectors. For a route with multiple rubrics, read the options; do not select the first one automatically. In projects, `project.json.metadata.award_criteria_variant` retains the type/lot selector; `role`, `strand`, `region`, and other context fields remain explicit where required. The resolver reads this data without confirming it or modifying the model. Sector and role must be compatible with the route and variant: metadata cannot override the dossier's identity. `context_required` contains the data essential to selecting the rubric; `context_to_verify` contains applicability details for a shared rubric, which must be treated as explicit research if still unresolved. Each detail generates a methodological row distinct from the official criteria, with a rationale, owner, and credible verification plan. For example, CBHE uses a shared rubric: the topic may remain open at the idea stage if it has not yet been identified; it must be verified before finalizing the design and application. Jean Monnet Networks, by contrast, distinguishes the HED rubric from the SCH/VET one, and ESC roles retain their own scopes. A human decision is recorded only if observed, in accordance with working memory.

```bash
python3 scripts/award_criteria.py catalog
python3 scripts/award_criteria.py show --action KA220-YOU --max-chars 8000
python3 scripts/award_criteria.py show --action ERASMUS-MUNDUS --variant EMJM --max-chars 8000
```

The window reports coverage and `next_offset`: continue with `--offset` until the complete rubric has been read. Use the exact selector value returned by the catalog; do not infer it from a similar name. To manually review all sheets:

```bash
python3 scripts/award_criteria.py export --output wiki/checklists/award-criteria
```

## Completing the Idea Matrix

`checklist.py init ID --phase idea-validation` integrates `award_coverage` into the dossier checklist; the compact process uses `eligibility`. The matrix reports the criterion, subpoint, source, control question, evidence relevant to the phase, subsequent verification, and design implication. For each row, add an owner, rationale, available evidence, and a plan where research is needed:

| Maturity | Meaning at the idea stage |
|---|---|
| evidence-supported | The proposal is supported by real, located evidence. This does not mean the final criterion has been definitively satisfied. |
| plausible | Promising logic or choice, with assumptions and limitations stated. |
| research-needed | Evidence or validation is needed; define the collection/method, owner, and verification timing. |
| redesign-needed | A substantial issue must be addressed by changing the idea before expanding the text. |
| not-applicable | A conditional subpoint is out of scope, with a reason and evidence of context. |
| unassessed | An item has not yet been considered; do not call the checklist complete. |

The core need, added value, minimum logic, necessary capacities, and incompatibilities with the action require immediate critical judgment. Baselines, consultations, partnership, target group, or adoption that have not yet been validated remain explicit gaps; the research plan must be realistic. Do not invent evidence to complete the table. Idea validation assesses selection, coverage, plausibility, and treatment of gaps; it does not demand all evidence for the final application, and it does not turn every incomplete future criterion into a blocking defect.

## Gate and Reuse

The gate freezes the checklist, relevant catalog, and all cited original sections, including conditional prerequisites. New idea checklists are automatically marked as accepted products bound to hashes: protection remains active even if the operator omits `--artifact`. The accepted copy passes to dependent phases. An unresolved profile, data essential to selection, or incompatible context prevents formalizing validation against the wrong rubric. `method-award-design` checks that all subpoints have been considered and that decisions/gaps support a realistic idea. The checker verifies coverage, identity, and locators; the fresh validator judges merit, credibility, and which gaps are decisive at this stage.

Explicitly include `research/checklist-idea-validation.json` (or the compact `eligibility` checklist) among the idea gate's `--artifact` items as well: it becomes an accepted step-product in addition to serving as a checklist. Pass the accepted copy as a dependency to subsequent phases. This binds outcomes to the exact content; do not use a modified current copy as approved. Before regenerating an accepted checklist, invalidate its owning phase and retain the historical snapshot.

The matrix feeds [the design plan](design-methodology.md), research, and question/instance plans, preserving canonical IDs. Changing the route, selector, or a substantive premise requires invalidating the first affected phase and performing new dependent checks. Do not rewrite accepted historical receipts or checklists. To adopt an updated catalog in an existing dossier, retain the previous checklist, regenerate the current version after the relevant invalidation, and transfer only outcomes/evidence that remain valid; there is no automatic migration.

Accreditations, Quality Labels, qualitative assessments, and allocation requests retain their own procedures. Where no new award rubric exists, checks concern prerequisites and allocation and are marked NONaward. The absence of published scores does not authorize inventing them. Profiles outside the catalog or new annual editions require [verified maintenance](knowledge-maintenance.md) before adoption.
