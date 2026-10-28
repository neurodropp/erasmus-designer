# Common Model and Form Repairs 0.2.1

This phase covers ED-07–ED-14 from a private audit. These are structural and numerical checks: they do not certify merit, complete regulatory evidence, legal validity, or the content of an annex. The private audit evidence and its case data are not included in this distribution.

| Finding | Verifiable correction |
|---|---|
| ED-07 | In strict grant mode, outputs are linked to activities and KPIs to a measured object. WPs are consistent across activities and outputs, and between a KPI with a declared WP and outputs measured through results/impacts. |
| ED-08 | Canonical `project-model-v2` contract with task, deliverable, and milestone registers; references, owners, schedule, dependencies, inverse lists, language versions, and acceptance are verified. Common projections can be exported for WPs, Gantt, task files, results, and budget. |
| ED-09 | A single WP management allocation for KA220; sum all allocations with that classification, even when the designated ID would be incomplete. The 20% cap applies only to KA220 routes specified by the matrix. |
| ED-10 | Annex type is compared with the register and a recognized ID; a conflict cannot disable the legal gate. Draft agreements remain distinct from `ready-to-sign`. |
| ED-11 | Matrix by question/instance pair, membership of each answer, uniqueness, and partner/WP/activity/role context consistent with the physical occurrence. |
| ED-12 | Profile is validated before indexing: duplicate question/occurrence pairs and invalid structured types are rejected, regardless of order. |
| ED-13 | Positive integer duration when a schedule is present or required by the mode; 0/null/bool/missing duration do not disable comparisons. |
| ED-14 | Quantity, rate, and estimated cost must each be non-negative and are each checked even when the product is incomplete; the quantity×rate check remains distinct from the allocated grant. |

## Contract and migration

New files: `schema_version=project-model-v2`, with all sixteen registers initially empty. The checker does not add or modify data. In non-strict mode, a historical model missing the new registers is normalized in memory only; strict mode requires an intentional migration with all registers and an explicit v2 marker. Preserve the historical version and invalidate the first modified phase without rewriting frozen receipts.

`tasks`: an `activity_id`, a consistent `wp_id` if the activity belongs to a WP, `partner_id`, title, `start_month/end_month`, and `dependency_ids` pointing to tasks. `deliverables`: `task_ids`, `output_ids`, consistent WP, owner, `due_month`, acceptance criteria, and `versions[{id,language,version,status}]`. `milestones`: owner, due date, and at least one activity/task/deliverable link, with concrete criteria. Present inverse lists must agree; nonexistent references are not ignored.

In strict KA220, or a grant using task/deliverable registers, every operational activity has a task and every output is a deliverable. For other grants without that level of detail, the minimum chain is activity→output; accreditations, allocations, and Quality Labels do not receive fictitious tasks or budgets. Whether a table/upload is required must still be established from the actual call. The durations checked here are internal domains, not eligibility ranges for every action.

A planned/draft version does not require an already produced artifact. An accepted version requires a file or URL, ISO date, approving partner, and localized evidence. Structural validation alone never means the document has been accepted on its merits.

## Projections for owners

```bash
python3 scripts/project_check.py projects/ID-COMPLETO/project.json --strict --projections-output projects/ID-COMPLETO/production/canonical-annex-views.json
```

Output is written only if the requested check passes, including any manifest required with `--manifest`. `annex_projections(model)` exposes the same views through the stdlib API. Preserve canonical IDs and use project months; owners materialize and verify daily dates, formats, upload files, and content. Projections are `semantic_only=true`: they do not certify an XLSX/PDF/DOCX.

A single deliverable can have multiple tasks and language versions. `deliverable_id` remains the common ID; `artifact_id` is the ID of an individual version. `row_kind/entity_id` distinguish registers in WP views; `schedule_id` refers to the entity in the Gantt. `owner_partner_id` and `depends_on_task_ids` in the views derive from `partner_id/dependency_ids` in the model; workbook `outcome_id` derives from `results.id`. A budget allocation is exported once, with task/deliverable lists, avoiding amount duplication by language.

## Forms

`form_profile.validate_profile(profile)` returns `passed/issues` and is called by `form_profile.py` and `application.check_answers` before indexes are built. The strict matrix resolves every pair; a P7 answer is not covered by P1's NA decision. Additional instances of the actual form require a declaration, context, and evidence for the field; for a field previously marked non-repeatable, `current_repeatable=true` is also required. A response cap must match the matrix's `max_chars` when recorded. An override still requires current evidence and does not truncate text.

The distributed profile preserves exactly 98 schemas and 346 occurrences, byte-identical to the private audit snapshot. The 2025 year and 2026 form/limits have not yet been verified. Evidence and per-question structures remain separate from internal chain of thought.

## Verification and limits

The private audit replay scripts and case inputs are excluded from this distribution. The replay loaded prior scripts from an immutable private audit ZIP, with isolated configurations in a temporary directory. Eleven original negative inputs were reproduced before/after: all passed before and are now rejected with the expected specific codes, as well as any migration requests. The original positive response continues to pass; the historical positive model passes in non-strict mode and requires migration in strict mode. A synthetic positive v2 model with two tasks and two language versions of the same deliverable passes and reconciles across the five views without duplicating budget.

Targeted tests are `test_project_check.py`, `test_model_contract.py`, and `test_application.py`. Synthetic fixtures do not attest to partner data, consultations, signatures, real acceptances, or a new validation session. A new independent evaluation must read this phase's frozen files and evidence.

## Second correction: MR-01–MR-04

The earlier independent review remains immutable in private audit evidence, which is not shipped. The new replay and its incorporated reviewer inputs are also excluded; the replay did not reuse the reviewer's agent.

- **MR-01:** Inverse WP↔milestone and activity↔deliverable lists are checked in both directions when present. A present but empty list cannot omit a linked entity; an absent optional list remains absent and does not generate fictitious data.
- **MR-02:** `budget_lines.task_id` must belong to the deliverable specified on the same row. A specified `activity_id` must be an activity of at least one task for that deliverable; if the task is explicit, it must belong to exactly the specified activity. Projections with an explicit deliverable derive only its tasks, filtered by activity when specified; a WP-only row does not invent tasks/deliverables or split/multiply amounts.
- **MR-03:** Strict mode applies the entire `config/project-model.schema.json` file through `model_schema.validate_instance`, in addition to route invariants. `requested_grant` is number|null in strict mode; decimal strings for budget entries remain allowed where the schema permits them. A present plural reference with a null value is rejected by the schema. Every present WP schedule has positive months, within duration and a consistent range; if start/end are specified, they must contain all included activities. These schedule checks also apply in non-strict previews: negative months or months beyond duration cannot enter the exported Gantt.
- **MR-04:** Every explicit or inferred identity dimension must be present and equal in the context of the selected physical occurrence. WP9 cannot use an occurrence that identifies only a partner/role. Declared matrix aliases preserve the occurrence identity; a new partner of the same contextual type may be declared with context and current evidence. A new dimension absent from the profile's occurrences requires a verified profile update; it cannot be added to borrow a cap. Unknown keys in runtime answer/matrix contexts are errors; editorial metadata in template contexts remains data.

### Stdlib schema validator

The module implements the explicit subset used by the v2 file: `$schema`, `$defs`, `$ref`, `type` and union, `properties`, `required`, `additionalProperties`, `items`, `oneOf`, `const`, `enum`, `uniqueItems`, `minimum`, `minLength`, `minItems`, `minProperties`, `pattern`, `format`, title, and description. Preflight reads all nodes, including unused definitions. Unknown keywords or formats, malformed schemas, unresolved/external/cyclic references are rejected without weakening validation. This is not a general JSON Schema validator: supported references are local and non-recursive; the current schema's decimal ASCII pattern is checked using stdlib regex; `format=date` is always enforced as a real ISO date. Non-finite numbers and non-JSON values are rejected. More restrictive schedule and action invariants remain in force after schema validation.

### Preview and materialization

`annex_projections(model)` continues to use non-strict checks as a **semantic preview**, useful for legacy and open work. It does not attest to a strict-ready model. Owners materialize annexes only after strict checks pass, using the CLI with `--strict` or the same gate checks. The CLI default is preview mode; with `--strict`, no new output is written if the schema, model, or required manifest fails. A previous output is not deleted automatically: each version must be linked to its own model/hash.

### Verified replay

All 50 model inputs and 11 reviewer response inputs were replayed, along with the reviewer's unrelated task/deliverable budget pair: before-results match the immutable report, and after-results match the requested outcomes. Seven negative variants of the four remaining findings passed before and fail after. Seven positive model cases and three positive response cases remain valid, including absent inverse lists, a complete WP schedule, activity-only/WP-only/deliverable-only budgets, compatible aliases, and a declared additional current partner. Fixtures are synthetic and do not attest to the 2026 call. The distributed profile retains 98 schemas/346 occurrences with unchanged bytes.

## Third correction: MR2-01–MR2-02

The independent report and its inputs remain immutable private audit evidence and are not shipped. The new replay is excluded as well; it imported prior code from `frozen-model-round2/engine` and repeated the reviewer's incorporated inputs. It did not execute or modify the reviewer's script in the historical directory.

**MR2-01:** All supplied start/end/due months for WPs, activities, tasks, deliverables, and milestones are positive integers within duration, including in preview mode. A declared range requires both endpoints and start≤end. Two null endpoints mean no range; a single populated endpoint is rejected. For deliverables/milestones, the optional range represents a delivery/gate window that must contain the due date. Without a range, due-only remains a point. WPs/activities/tasks represent production: any supplemental deadline must be ≥end and may follow the end of the work. These are declared internal semantics; they do not establish call requirements. Valid example: task/activity end in month 9, due-only delivery in month 12; the Gantt retains the point 12→12. `due_month` remains a separate field in the Gantt, and the task file keeps production end and deadline separate.

**MR2-02:** `work_packages.dependency_ids` is now in the contract and schema: an array of unique, existing, acyclic WP IDs. When present, null or a non-array type fails even in preview; it is not hidden as an empty list. The schedule used by temporal checks and the Gantt is resolved by the same pure function, `work_package_calendar(wp, activities)`: explicit range → complete range of all declared activities → due-only → unknown. The view reports `calendar_origin` and `calendar_activity_ids` to make derivation verifiable, without modifying `project.json`. Where a real dependency exists, the predecessor must end by the successor's start. Strict mode requires a verifiable schedule for that relationship; non-strict mode may leave unknown months open without inventing them. WPs without dependencies, or routes without WPs, remain valid within their scope.

### Replay and compatibility

Replay completed on the same 89 models, 18 responses, five synthetic contracts, and 1,213 reviewer schema mutations. All before-results match the frozen report; all after-results match the requested outcomes. The 11 variants for the two new findings passed before and fail after, including 12→1, null→1, window 1→2 with due date 12, WP404, self-cycle, duplicates, and non-array type. The four CLI checks use the reviewer's exact source files and new temporary outputs: the positive case exports identical API/CLI results; the three negative cases emit no new views. The six budget projections preserve two allocations, total 120000, and the exact task/deliverable IDs.

Eleven additional positive cases preserve due-only schedules, delivery windows, deadlines after production, WP dependencies with explicit or derived ranges, and Quality Label without a WP; no data is added to the model. All 95 targeted tests across the four modules pass (18 project-check, 26 application, 39 model-contract, 12 model-schema). Projections preserve IDs and add the separate deadline field and WP schedule origin; a consumer must read these fields when present. This is not annex rendering or certification. Legacy continues to pass in preview without automatic migration; strict mode requires intentional v2 migration. The profile remains byte-identical, with 98 schemas/346 occurrences; the current call has not been verified.
