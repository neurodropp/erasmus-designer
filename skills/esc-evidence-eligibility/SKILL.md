---
name: esc-evidence-eligibility
description: Verify sources, action, role, eligibility, priorities, finance and ESC criteria; do not transfer Erasmus+ rules.
---
# ESC Evidence and Eligibility

Read [the contract](../erasmus-designer/references/evidence-contract.md) and [the ESC 2026 map](../../wiki/research/esc-2026-routing.md). Use `program=ESC` and the actual route in `config/actions.json`: ESC50 requires the role, ESC51 is an allocation application, and ESC30 is a solidarity project; the humanitarian Quality Label and centrally managed actions have their own rules.

In Phase 0, an ESC route is a candidate to compare, not a generic container for youth ideas. Apply `config/phase-zero.json`, verify the role, primary target, activities, geography, scale and financial model of the specific action, and retain the excluded alternatives. Frameworks such as the European Youth Goals remain contextual unless incorporated by the applicable ESC source; do not transfer Erasmus+ priorities, award criteria or tiers.

Retrieve LWC, then run `python3 scripts/brain.py dossier --action CODICE --program ESC`; search for original evidence with `search --program ESC --action CODICE --layer evidence` and open the actual ID. Use physical pages and ESC source IDs. Do not apply KA220-YOU priorities or the 25/30/20/25 grid to ESC. The attached expert guide covers only ESC50 and ESC30; host/support are pass-fail, the lead is numeric, and ESC51 has no new qualitative assessment. Humanitarian Label deadlines may refer to the grant call for the following year.

Verify the programme, year, role, country/age, capacity, qualifications/label, target groups, activities, grant and relevant AIG/EACEA/SALTO scope before reaching a conclusion. For central calls, read the current topic and its annexes; the map does not certify that they have already been acquired. Quality and eligibility remain distinct.

Deliver a requirement → data → evidence → status matrix, the actual scoring grid and applicable priorities, critical issues, an alternative and missing facts. Be precise about interpretations and limitations; a source not found does not prove that no requirements exist.

## Award checklist iniziale

For idea validation, use [award-idea-checklists](../../docs/award-idea-checklists.md) and the specific ESC profile in `scripts/award_criteria.py catalog/show`. Confirm the role/variant and read the subpoints in the relevant guide; retain pass-fail, the points grid, qualitative assessment or allocation without introducing a new rubric. The matrix records maturity, evidence and the gap plan at this phase: it is not a final score. Do not import Erasmus+ profiles, NA experts for EACEA, or example values as project data.
