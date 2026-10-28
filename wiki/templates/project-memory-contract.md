---
program: SHARED
status: operational-schema
---
# Consistent project memory

The wiki contains reusable standards, methods, and templates. Instead, each application uses a separate file `projects/<nome>--<tipologia>--<anno>/`: do not include partner data, hypotheses or expected results of a specific project in the general sources. Personal data and signed documents remain within the minimum necessary scope.

## Project dossier

| Files | Content and responsibility |
|---|---|
| `brief.md` | Request, organization, target group, constraints, alternatives and decisions; coordinator |
| `memory/events.jsonl` / `memory/seal.json` | Canonical append-only working memory of facts, decisions, options, hypotheses, and questions; work manager |
| `memory/index.json` / `memory/context.md` / `memory/history.md` | Deterministic index and reconstructable readable views, separated from common LWC memory |
| `evidence.json` | Claim, real/localized source, scope, version, date, status and limits; evidence/research |
| `project.json` | Single shared data model; coordinator integrates specialists |
| `concept-note.md` / `partner-concept.md` | Two products with different recipients and status |
| `answer-outlines.md` | Structure for question, tests, criteria, missing data and character budget |
| `answers.json` / `draft.md` | Plain text of the fields and submission of the application |
| `annexes/` / `annex-manifest.json` | Derived attachments, owner, destination, classification, checks and upload constraints |
| `findings.json` | Findings with criterion, severity, point, test, correction, owner and status |
| `state.json` / `reports/` / `receipts/` | Phases and reviews, critical reports and hashed immutable receipts |

## Data model

The new model uses `schema_version=project-model-v2`, with sixteen registers, including `tasks`, `deliverables`, and `milestones`. The WP registry uses `kind=management|implementation`: the name or ID of the WP does not prove its nature. Workbook aliases `outcome` correspond to template `results`; historical headings do not create a second register. Quality label ESC and allocation requests have data packages relevant to your form: do not force grants or WPs where not foreseen. The checker is not an admissibility ruling.

The structural scheme is `config/project-model.schema.json`; `scripts/project_check.py` checks references and main numerical constraints. Semantic checks remain with specialists.

### Identity, logic and organization

| Registry | Essential fields beyond `id` | Links |
|---|---|---|
| project | program, year, action, sector, round, form_profile, duration_months, currency, requested_grant, financial_model, financial_model_evidence, management_wp_id | Work identity; no automatic program/year substitutions |
| partners | name, country, expertise, expertise_evidence, capacity, confirmed_status | Type of entity other than the project sector |
| priorities | label, source_id, locator, scope, verification_status | Specific and applicable link; not just keywords |
| needs | problem, evidence, cause_hypothesis, scale, target, baseline, existing_response_gap | scales: organization, participants, community, European when relevant |
| objectives | statement, need_ids, priority_ids, target, deadline, assumptions | Actionable change, not product list |
| work_packages | title, kind, objective_ids, activity_ids, task_ids, deliverable_ids, milestone_ids, lead_partner_id, dependency_ids, start_month/end_month/due_month optional | Use WP if appropriate for the action; predecessors in the same register |
| activities | title, wp_id, objective_ids, partner_id, assignment_evidence, start_month, end_month, dependency_ids, task_ids, deliverable_ids, resource_requirements | Owner motivated by skills and abilities |
| tasks |. tasks title, activity_id, wp_id, partner_id, start_month, end_month, dependency_ids, deliverable_ids | A task belongs to only one activity; dependencies between tasks |
| deliverables | title, task_ids, output_ids, wp_id, partner_id, due_month, start_month/end_month optional, acceptance_criteria, versions | Verifiable delivery; optional interval as delivery window; `versions` contains id, language, version, status and acceptance proofs when declared |
| milestones | title, wp_id, partner_id, activity_ids/task_ids/deliverable_ids, due_month, optional start_month/end_month, dependency_ids, acceptance_criteria | Concrete gate connected to one or more entities; optional range as gate window |

### Products, changes and resources

| Registry | Essential fields beyond `id` | Links |
|---|---|---|
| outputs | description, activity_ids, wp_id, deliverable_ids, format | Product made; the language versions belong to the canonical deliverable |
| results | change, output_ids, objective_ids, target_group, measurement | Effect on recipients: not synonymous with published file |
| impacts | change, result_ids, scale, time_horizon, attribution_limits, adoption_path | Distinguish plausible contribution from unproven causal attribution |
| kpis | objective_ids/output_ids/deliverable_ids/result_ids/impact_ids, optional wp_id, baseline, target, unit, measurement_source, frequency, partner_id, collection_method | Don't invent baselines; zero is a data to be proven, it does not replace unknown |
| budget_lines | optional wp_id, activity_id, task_id/deliverable_id, partner_id, grant_allocation, estimated_cost, quantity, unit_rate, currency, amount_evidence | Contribution allocation and estimated cost are distinct quantities |
| dissemination | audience, objective, output_ids, channel, start_month/end_month, partner_id, kpi_ids, accessibility, adoption_action | Visibility does not equal use or impact |
| risks | activity_ids/wp_ids, partner_id, likelihood, impact, mitigation, trigger, contingency, review_frequency | Updateable ratings with owners and observable signals |

Budget, dissemination, Gantt, WP, KPI and task tables report these IDs. The specialist does not create a second version of the numbers: he reports a proposed change to the coordinator, who updates `project.json` and regenerates the dependent outputs. An inconsistent WP/activity assignment, a cyclic dependency, an out-of-life calendar, or an unreconciled total prevent the consistency conclusion.

## Canonical contract, views and migration

The fields `partner_id`, `dependency_ids`, and `result_ids` are canonical. The aliases `owner_partner_id`, `depends_on_task_ids`, and `outcome_id` belong to workbook views; they do not become parallel registers in `project.json`. A historical result `outcome` maps to `results.id`; `artifact_id` maps to `deliverables.versions[].id`, while `deliverable_id` remains the delivery ID common to all languages. `schedule_id` uses the entity ID and `row_kind` declares its registry.

The chain is activity → task → deliverable → output → result → impact. The reverse lists, when present, must agree; the task/activity, deliverable/task and output/activity links have the same WP. In strict grant each output requires activity, and each KPI at least one measured object; if a KPI declares `wp_id`, products measured indirectly through results/impacts must also belong to it. In strict KA220, or in a grant that adopts the task/deliverable detail, operational activities require tasks and deliverable products. Accreditations, Quality Labels, allocations and other grants without that detail do not receive mandatory fictitious records. Cardinalities are method checks; the official requirement for an attachment still requires the source of the call.

### Calendar and dependencies

The canonical calendar uses project months, integers from 1 to duration. A task remains in the activity calendar; a delivery does not precede the end of the tasks that produce it. Monthly precision does not determine the order of days within the same month. `duration_months` must be a positive integer if the calendar is used or required by the phase mode. The admissible durations of the specific call remain to be verified.

WP, activities and tasks describe the productive period: an additional `due_month` can follow `end_month`, but not precede it. For deliverables and milestones the optional interval indicates a delivery window/gate: it must be complete, ordered and contain `due_month`. A delivery with only `due_month=12` and tasks/activities completed in month 9 is valid and is projected as point 12→12. The two null extremes mean absent interval; only one valorized extreme is incomplete and is rejected. They are internal semantics of the model, not normative rules invented for a call.

WP dependencies, when declared, are lists of unique, existing WP IDs, without autocycles or loops. `work_package_calendar` resolves the same calendar in predecessor control and Gantt: explicit range → full ranges of all declared `activity_ids` → point `due_month` → unknown calendar. The predecessor must finish by the start of the next WP, to the monthly precision. If a real dependency has no verifiable calendar, strict remains open with `wp-dependency-calendar-unverified`; the preview can keep it without inventing months. WP without dependencies or actions without WP do not receive fictitious obligations.

### Versions, views and migration

Each deliverable version has a unique ID, unique language/version pair, and status `planned|draft|submitted|accepted|superseded`. A planned/draft version does not require a built file. Accepted status requires file or URL, ISO date, approving partner, and localized testing; the checker does not certify the content or validity of the test.

To materialize common data without changing ID:

```bash
python3 scripts/project_check.py projects/ID-COMPLETO/project.json --strict --projections-output projects/ID-COMPLETO/production/canonical-annex-views.json
```

The views cover WP, Gantt, task file, results register and budget. They maintain project months, owners, predecessors, tasks and deliverables; a budget line remains a single allocation, with associated task/delivery lists, without duplicating amounts per language. They are semantic views (`semantic_only=true`), to be transformed into the required formats and checked/rendered when the files are produced. They do not give acceptance to attachments.

The Gantt keeps `due_month` separate from start/end. For WPs it includes `calendar_origin=declared_interval|activities|due_only|unknown` and `calendar_activity_ids` for a derivation from activities: it explains the origin without writing dates in `project.json`. In the task file `end_month` it is the end of production; `due_month` keeps any additional deadline and, when absent, uses the end of the task as the view deadline.

An older model with missing new registers remains readable in non-strict, which uses empty lists only in memory. Strict reports `project-model-migration-required` even when the explicit v2 mark is missing, with all registers present. Do not edit frozen receipts: keep the historical model, integrate real registers, add the v2 brand and invalidate the first phase involved. No migration invents tasks, versions, owners or dates.

## Attachments and signatures

In the manifest use `classification=internal|optional|required`. `required` requires `requirement_source` the current call/form; the user template is not enough. Each file has `id`, `type`, `path`, responsible agent, status and checks. For uploads, confirm format, size and number of attachments.

A contract can be `delivery_status=draft-for-review` with a verified structure, keeping the legal verification open. `ready-to-sign` requires parties, powers, applicable grant agreement, jurisdiction and rules verified with `legal_review_evidence`. Do not make "complete application" and "all contracts already valid and signed" coincide when the call does not require it. No model authorizes a signature or communication.

## Reusable memory

The [registered working memory](../../docs/project-working-memory.md) is opened for each session and phase via `scripts/project_memory.py context ID --phase PHASE`. The manager records each new decision, fact, relevant option or change of state with its declared author, observed provenance, evidence and relationships. `proposed|confirmed|rejected|superseded` distinguish declared status and history; a proposal does not withdraw a confirmation. The IDs include the file, and `supersedes` adds events without rewriting the past. Hypotheses, open questions and contradictions remain visible in the context. In-memory confirmations do not change the model, workflow or gate. Do not automatically import the brief as a set of confirmed facts.

The local index is rebuilt only after the log, chain and seal checks; canonical inconsistencies cannot be remedied by recalculating hashes. Local proofs retain the observed hash and flag changes; normative sources remain in the shared corpus and are referenced by actual IDs/locators. Do not record chains of thought or unnecessary personal data. For decisions about the engine project, use only `--engine-memory` in `work/engine-memory/`, with a separate namespace, never the application file or LWC.

The form profile is frozen together with the draft and verified during review/QA. To bind it after creating the file, use `workflow.py bind-form` with the profile and localized report; if work is already in the responses phase, that phase is reopened. `invalidate` records the reason and reopens the first affected phase. Receipt hashes are checked twice before status, record and invalidation operations; archived reports are not edited to correct the project.

Publish only confirmed lessons on the wiki, with context, action/year and source. Do not turn examples in user files into organizational experience. Do not retain chains of thought, expectations of success or scores as evidence. [[workflow-erasmus-esc]] · [[response-contract]] · [[annex-blueprints]]

## Step versions and validations

`stages/PHASE/product.md` retains the integrated phase product; exclusive specialist outputs can be stored in `production/PHASE/ATTEMPT/`. `validation/packets/PACKET_ID/` preserves the manifest, snapshot and schema; `validation/dispatches/` records the observed spawn; `validation/reports/` receives the new validator report. `sessions/` retains observed calls. Receipts and snapshots are immutable under the protocol; invalidation marks superseded gates without altering their history.

A new validator reads approved dependencies without the authors' conversation. Repair/QA receives findings to verify against their origin and a before/after baseline. Do not reuse an old approver. Phase outlines and route reminders are retrieved as needed; do not duplicate the entire corpus in each chat. The user's KA220 form is Youth; every other form keeps its own profile.

## File creation and replication

The engine creates `projects/` via the init workflow; type/year and directory names are in config/project-layout.json. [Project creation](../../docs/project-creation.md) and [replication](../../docs/replication.md) distinguish shared memory, assignments, rebuildable configurations and frozen archives.

## Strict validation and projections after independent review

Strict enforces the entire v2 schema via the explicit subset stdlib validator (`scripts/model_schema.py`): every keyword of the current schema is supported, while unsupported keywords/formats/refs fail. `requested_grant` in strict is number|null; `dependency_ids=null` is not a valid array. Route, reference and calendar controls are added to the scheme.

WP↔milestone and activity↔deliverable are inverse relationships, checked in both directions when lists are present; an empty list is not the same as an absent list. If a WP declares start/end, the calendar must be positive, within the duration and contain the included activities. The WP calendar is not added to the model due to lack of data; a projection can only derive an already proven interval from the declared activities, with explicit origin. Each exported calendar must also be consistent in the previews. A present `dependency_ids` WP property must be an array even in preview: null or object are not silently converted in the absence of predecessors.

A budget line with tasks and deliverables must associate truly connected entities; one of its indicated activities must belong to the delivery tasks and to the specific task when indicated. Delivery projections derive only its tasks, filtered by activity; a WP allocation-only line does not invent more detailed associations. The amounts remain only once, with no implicit distributions.

`annex_projections` is a non-strict semantic preview for open/legacy data. Materialize the attachments after passing check strict, via the command with `--strict`, and verify/render the resulting files. A preview does not confirm acceptance or upload validity. [Details and replay of fixes](../../docs/model-form-repairs-0.2.1.md).
