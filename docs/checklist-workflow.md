# Application-Specific Checklist

`config/compliance/` stores reusable profiles and declared coverage: in-depth but partial KA152 coverage, targeted checks for six other Youth actions, and routing for other routes. This is not equivalent to a complete requirements matrix for all 50 routes. `scripts/checklist.py` creates a matrix with results in the actual case file, without inventing data or automatically closing checks.

Use the case file initialized by `workflow.py init` and its complete ID:

```text
python3 scripts/checklist.py init <FULL-ID> --phase intervention-design
python3 scripts/checklist.py validate <FULL-ID> --input research/checklist-intervention-design.json
```

For a later version, use `--output research/checklist-intervention-design-v2.json`, or a JSON path in `stages/<phase>/`. Creation does not overwrite files; the shared resolver handles IDs, ambiguous names, and legacy cases. Paths outside the case file are rejected, including through symlinks. Do not create a dummy project to try the system: tests use temporary fixtures.

## Contents and Required Work

The matrix preserves scope (programme, year, action, sector, country, agency, role, round), phase, profiles, and original gaps. It imports applicable checks through `stage_gate.compliance(state, phase)`, preserving text, classification, stages, and sources in full. Every result starts as `to-verify`.

For each check, fill in `status`, `evidence`, `artifact_locators`, `discrepancy`, `severity`, `required_fix`, `owner`, `reason`. The statuses are `satisfied / not-satisfied / to-verify / not-applicable`. Assessed results require an owner and located evidence; satisfied/not-satisfied also require case-file artifacts. NA requires a scope-specific reason and evidence. An unsatisfied finding requires a discrepancy, severity, and corrective action. Do not turn a recommendation into an eligibility condition.

An evidence reference uses `{source_id, locator, path}` or `{source_id, locator, url, verified_at, version}` for an online source. `source_path_or_url` is an accepted alias. For artifacts, use `{path, locator}`; optional `sha256` is checked. Prefer paths relative to the case file for artifacts and project evidence; an evidence path `sources/…` is relative to the catalogue. Confined absolute paths are also accepted. Local evidence must be in the case file or the `sources/` corpus; artifacts must be in the case file. The check verifies presence and structure, not the truth of the content or the actual authority of a URL: those are for the reader and independent validator to assess.

`section_coverage` requires complete reading of the action section, general conditions, relevant expert guide, and applicable indexed national/standard/handbook documents. Sources contain the version, original hash, and actual references to immutable revisions; every expected physical page is listed. `read_locators` contains `source_id:pNNNN` or `source_id:full-document`. Satisfied requires all locators, evidence, and an owner. If a passage continues beyond the range, open the adjacent pages and cite them in extensions/evidence; catalogue ranges are a starting point, not a guarantee of complete requirements coverage.

Explicit rows remain for current call/corrigenda, territorial and round provisions, the actual form, and completion of the matrix. Even without the real form, the checklist supports research and design; it does not invent questions, limits, or uploads. The `expert-scope` row remains open when the catalogue offers no relevant grid, until a source or substantiated NA rationale clarifies the case. The catalogue's national provisions do not certify that they include all provisions of the actual call.

In phases before answer-outlines, the absence of the form may remain an open item. Any NA for the form check is phase-limited, reasoned, and evidenced: it does not mean the form is optional for the application. From answer-outlines onward, the actual form and a verified profile are required before field planning. The validator applies the phase contract and explains the results; do not automatically block the entire design because all checks in the first copy start as to-verify.

Expand `extensions` with a unique `project-…` ID, `classification`, `check`, `applicability`, `owner`, `scope` equal to the matrix scope, located `sources`, and all result fields. Do not modify baseline checks. Link extracted checks using `derived_check_ids` in the sections read. Closing `coverage-extension` requires extensions; a partial checklist cannot become complete simply by reading its pre-existing checks. `coverage_gaps` retains open gaps; remove them only after documented verification, preserving the history in the previous version. Original gaps remain visible in `baseline_coverage`.

## Results and Gate

`valid=true` indicates a structurally sound matrix, even when work remains open. `ready_for_independent_review=true` additionally requires no to-verify/not-satisfied results and no open gaps. It does not certify eligibility, substantive compliance, or funding. `validate` returns code 1 for structural defects and 0 for a valid matrix; always read `unresolved_items` and `coverage_gaps`.

Freeze the completed matrix with the phase package and pass it to the new independent validator required by `fresh-step-v1`; do not suggest a verdict. A change to accepted products requires invalidation of the first affected phase and new validation. The script does not record completed phases, generate receipts, or simulate a spawn. Orchestrator/gate integration must distinguish open results permitted during work from requirements needed to accept the relevant phase.

New case files have `checklist_protocol=project-checklist-v1`: stage_gate.prepare requires the matrix at the standard location `research/checklist-PHASE.json`, verifies its structure, freezes sources and local evidence, and adds every extension check to the mandatory coverage of the independent report. An alternative `--output` is for standalone work; use the standard path before the gate. Added online sources must also have `local_snapshot` with the path to the local export/snapshot, which is to be frozen; URL, version, and date alone do not prove the content to the validator. The declared reading and the author's results still require independent verification.

From the answer-outlines/draft phases onward, current-form and shared-form cannot have a not-applicable result. Structural validation rejects this, and the gate report cannot skip shared-form. A to-verify check leaves work open: it does not permit acceptance with an independent check marked unknown.

## Award Criteria from the Idea Phase

For compact `idea-validation` and `eligibility`, `award_coverage` is derived from the route catalogue and actual selectors. Fill in all sub-points with maturity, evidence, and a gap plan, without official scores; [instructions and coverage](award-idea-checklists.md). The gate freezes all cited pages and automatically marks new initial checklists as protected accepted products. Even without `--artifact`, a change requires invalidation of the owning phase; prior snapshots and receipts remain unchanged.
