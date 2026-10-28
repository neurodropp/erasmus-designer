---
program: SHARED
title: Blueprint of Erasmus+ attachments and common data model
type: annex-blueprints
official: false
verified_at: 2026-09-12
status: architecture-not-populated
---

# Blueprint of Erasmus+ attachments

The two user workbooks provide layouts and processes to adapt, not new Erasmus+ requirements nor facts of a new application. [Complete catalog of 26 tabs](annex-template-catalog.md) and [attachment configuration](../../config/annexes.json) retain origin, cells, owners, columns and controls. No attachments filled with a dummy project were produced and no user files were rewritten.

**Attached status.** `internal-or-optional-until-current-form-requires` is the default. The sources/admissibility manager can classify a `required` attachment only with precise reference to the current form/call and format, limit and method of sending. A table useful for internal work does not become mandatory because it exists in the template. Any commitments included in the grant for implementation/reporting must be verified separately from the list of attachments to the application.

**Production status.** `blueprint-not-populated → draft-with-confirmed-inputs → reviewed → approved-for-specified-purpose`. A file is ready only for its stated purpose and with relevant sources/inputs/checks completed. Contracts and documents for signature start from `not-ready-to-sign`: a generated draft does not alone surpass legal validation and confirmation of the parties.

## One common data model, many views

The approved dossier maintains stable entities and IDs; each owner produces a view of the same model. Don't use line number, color, or description as a key. The following codes are technical conventions, not official Erasmus+ codes.

| Entity | Minimum and key fields | Relationships |
|---|---|---|
| Project | `project_id`, title, acronym, program, action_code, sector, call_year/round, agency, current_form_source/version, start/end, as_of_date, financial_model, currency | Contains all entities; year of the template distinguished from annuity call |
| Sources | `source_id`, URL/file, authority, publication/version, verified_at, page/sheet/range, scope, applicability, limitations | Official sources separated from user templates and internal estimates |
| Needs / Objectives | `need_id`, problem/group/test; `objective_id`, change and motivated target | Each objective responds to a need and verified applicable priority |
| Partners / Roles | `partner_id`, confirmed organization/country, expertise, role, commitment authorization | Owner and contributor of activities, budgets, evidence and gates |
| WP / Activity / Task | `wp_id`, `activity_id`, `task_id`, parent_id, objective_ids, method, target group, owner, contributors | An activity belongs to a WP; a task belongs to an activity; include dependencies and schedule |
| Outputs / Outcomes | `output_id`, immediate product/capacity; `outcome_id`, change from use | Activity produces output; use contributes to outcome, they are not synonymous |
| Deliverables / Artifacts | `deliverable_id`, output_id, type, language/version, editable source, acceptance, owner; `artifact_id`, file/URL approved | An output can have multiple deliverables/versions; related evidence and approval |
| Schedule / Milestones | `schedule_id`, entity_id, start/end, dependency IDs; `milestone_id`, gate/decision/date/owner | Single source of dates for Gantt, task file, dissemination and release |
| Budget / Effort / Trips | `budget_line_id`, activity_id/partner_id, quantity/unit/rate/source, total estimate, grant allocation, other funding; effort and trip ID | Detail feeds summaries; explicit financial model and nature of installments |
| KPIs / Evidence | `kpi_id`, scope, baseline/target, definition/unit, collection; `evidence_id`, source/file, owner, date, privacy/access, approval | KPI measures objective/output/outcome; evidence justifies value and acceptance |
| Risks / QA / Changes | `risk_id`, trigger/owner/review/response; gate ID and check; change_request_id, reason/approval/version | Risks and changes related to WPs, budget, schedule and deliverables |

Each statement/input retains `status = confirmed / assumption / to-confirm / not-applicable`, source and approver. Zero, absent and not applicable are distinct. Partners name/resume, consultations, numbers, dates, rates and commitments are acquired from real sources; they do not complete with plausibility. Examples in the workbooks remain under `raw/templates/` with non-normative authority and do not enter as approved master data.

**Calculation flow.** Approved sources/inputs/assumptions feed the calculations; the calculations feed views and summaries. Audits independently compare outputs and do not feed budget formulas or assumptions. No second editable input for data already owned by an owner. An approved change invalidates the affected views and requires a new version with controls.

## 1. Detailed budget — `budget-table`

**Single owner:** `erasmus-annex-budget`. Main schema in [config](../../config/annexes.json): `budget_line_id`, WP/activity/partner, cost category/model, quantity/unit/rate/currency, rate source/version, estimated total cost, grant allocation, other funding, assumption status, evidence.

The future file must distinguish verified inputs, build quantity × cost, detail and summaries by WP/partner/category. Effort, travel and multiplier estimates become tables linked via `activity_id` and `budget_line_id`, not three cumulative budgets. The grant model and internal budget are explicit: for KA220/KA210 a cost per day/event can be an internal estimate, without turning into an official rate. KA1 and ESC have action/category/year rules to retrieve before calculation; nothing from 2024 is automatically inherited. This catalog does not constitute a search for ESC rules.

Minimum data: verified scheme, amount requested, activities/partners, motivated quantities, cost sources and applicable co-financing. Controls: detail total = WP summary = partner summary; no sum of subtotals and children; consistent total/grant/other funding split; documented rounding; valid quantity/unit/currency; division only with appropriate denominator. For KA220 apply management ≤20% of the total, with a maximum recommendation of four implementation WPs; for KA210 the 20% reference is not an automatic ceiling. Sources: TASK `BUDGET`, `BUDGET NEW RULES`, `SETUP`; DEOR `0 - DETAILS`, overview, staff, results_budget, travel, multi; [P 2026, pp.243,249–250](<../../raw/pdf/programme-guide-2026-en.pdf>).

## 2. Dissemination — `dissemination-table`

**Owner:** `erasmus-annex-dissemination`. Columns: communication ID, output/deliverable/objective, audience, owner, channel/message, start/end/milestone, budget line, KPI, target/actual/evidence, reuse call-to-action, privacy status.

Produce the plan and the implemented register distinct in the same scheme, with results to be promoted, specific recipients, messages, adequate channels, resources and follow-up for use/adoption. Reach, impressions, attendance, unique people and adoption requests are not the same indicator. The minimum odds in the template are not official thresholds.

Controls: dissemination of a product after its approved release; owner and resources in the budget/task file; motivated targets in the master KPI; audience deduplicated when relevant; emblem/funding statement and access/licensing according to current sources. Source: TASK `DISSEMINATION!A3:I16`, DEOR `4-DISSEMINATION TABLE!C6:G16`; [P 2026, pp.13–14](<../../raw/pdf/programme-guide-2026-en.pdf>).

## 3. Gantt — `gantt-table`

**Owner:** `erasmus-annex-gantt`. Columns: schedule/WP/activity/task/deliverable IDs, owner, start/end, unit, predecessor IDs/type/lag, milestone/gate/status.

Single source of dates and derived bar view, with confirmed project start, relative months and consistent actual dates. Distinguish task, WP summary, event and milestone; gate connects decision/acceptance and predecessors. If there is only a hypothetical duration, the Gantt remains a draft and the date does not become a real commitment.

Controls: valid/start≤end dates, within applicable period; no loop; compatible predecessor and lag; WP summary min/max children, without summing parallel activities; release before the pilot/use/dissemination that depend on it. Approximate MATCH formulas on flags exported from the workbook are not reused without verification. Source: DEOR `1-GANTT!D4:AF51`, `1-EFORMS!G6:H49`; TASK `TASKS!B6:J94`.

## 4. WPs and result chain — `work-packages-table`

**Owner:** `erasmus-annex-work-packages`. Separate logical tables for WP, activities, tasks, outputs, outcomes and deliverables, with ID/parent and links; main columns: objective/need/owner/contributors, title/method/target group, learning outcomes, acceptance criteria, schedule/budget/KPI/evidence IDs.

Each activity explains how it contributes to the goal; tasks are assignable operations; output is immediate product or result; outcome is observable change from its use; deliverable is a verifiable object delivered/approved, with format, language/version and criteria. Management should not be dispersed under products to circumvent the required structure. The view for the form is a mapping to the current questions, not the historical `EFORMS` sheet assumed as official.

Controls: no deliverables without producer/owner/acceptance; activity without need/objective reported; Unique IDs and valid references; consistent costs/dates/targets; if youth, methodology and recognition of relevant learning. Source: DEOR `1-RESULTS!A12:C52`, `1-EFORMS!B6:H49`; TASK `TASKS!B6:J94`, `RESULTS!A3:J35`; [E 2026, pp.48–54](<../../raw/pdf/expert-guide-2026-v1.pdf>).

## 5. Monitoring, QA e risk — `monitoring-risk-plan`

**Owner:** `erasmus-annex-monitoring-risk`. A future file with linked monitoring, risk and quality gate registers. Monitoring: ID, KPI/entity, definition/reason, method, frequency, threshold, owner, evidence and corrective action. Risk: ID, scope, owner, trigger/when, scale/probability/impact/score, prevention/response, residual risk, status/review/evidence.

The scale is chosen and motivated by the project; 1–10 is not universal Erasmus+ standard. Do not import DEOR's static `G8:G24` scores as live formulas. Gate: deliverable, acceptance check, reviewer, date and decision. Cover actual risks, including quality, accessibility, participation, partner continuity, protection, data and rights in relevant contexts.

Controls: owner/frequency/threshold or trigger for each record; recalculable score if the method requires it; real list of QA checks, without stating “27” if not present; fixes with task/two dates; audit without reverse dependencies on business builds. Source: DEOR `4-RISK MANAGEMENT!B7:N24`, `5-MONITORING PLAN!B6:F33`; TASK checklist.

## 6. Partner Agreement — `partner-contract`

**Owner:** `erasmus-annex-partner-contract`. **Status: `not-ready-to-sign`.** There is no complete contract in the workbooks: TASK `TASKS!D7` asks to prepare it, INTRO retains representation fields. So you don't "extract" a non-existent contract.

Architecture for clauses to be parameterized: parties and powers of representation; grant and document hierarchy; roles/WP and governance; confirmed planning, contributions and financial arrangements; deliverables/acceptance/reporting; change and conflict management; rights to materials and open licenses; use of trademarks; data/confidentiality; protection of participants; duration/exit/continuity; signature; legal/court issues and liability to be validated. Columns: clause ID, topic, parameter, source reference, issue, validation owner/status, party/project/grant IDs.

**Data and legal issues for the future:** jurisdictions, nature of the parties, applicable grant agreement, law/forum proposed by professional, ownership of pre-existing/new results, coverages/liabilities, bases and roles of processing, rules on payments and modifications, powers and signature. Do not invent law/jurisdiction, ownership stakes, penalties, or rights; do not impose CC BY indiscriminately because it is present in an example mitigation. The owner prepares structure and issue list; Legal validation and confirmation of parts remain necessary before use for signature.

## 7. Reimbursement e code of conduct — `participant-rules-code`

**Owner:** `erasmus-annex-participant-rules`. Two related documents: reimbursement/evidence process and organizational/protection code. **Signature/acceptance status: `not-ready-to-sign`.** The workbooks contain travel cost estimates and checklists, not complete participant rules.

Reimbursement blueprint: activity/category, budget and current grant source, type of support vs reimbursement, conditions to verify, amount/rate only if confirmed, relevant evidence, request/approval/payment workflow and confirmed deadline, exception management to be validated. Code blueprint: expected behavior, inclusion/non-discrimination, contacts and reports, protection/security, emergencies, privacy/images, support and organizational process with verified roles. Rule, source/version, parameter, and legal status are separate fields.

Do not deduct the right to reimbursement from the grant rate; do not invent caps, penalties, deductions, guarantees, terms, waivers of rights or forum. Check category, minors/companions, authorizations and actual procedures. Future validation considers jurisdiction, grant, nature of the relationship/consent and methods of dispute. Structural source: DEOR `3 - TRAVEL!A19:R150`; TASK `CHECKLIST!C4:G73`, `MEETINGS!B4:K16`; [P 2026, pp.11,155](<../../raw/pdf/programme-guide-2026-en.pdf>).

## 8. Task file KA2 / PMQP — `ka2-task-file`

**Owner:** `erasmus-annex-ka2-task-file`. It is the operational container that connects documents owned by other owners; it does not reopen all their tables as editable. Sections: project/partner references, contacts by role, tasks, meetings, dissemination/result/evidence links, report checklist and change log.

Task columns: task/WP/activity/deliverable, owner/assignee, start/due/status/date done, predecessor, acceptance owner, evidence/version/reporting period/change ID. Dashboard summarizes approved deadlines and deliverables without redefining quantities/costs/targets. `as_of_date` of the report is distinct from the NOW() operation.

Controls: task→deliverable→schedule→consistent budget; no editable duplicate data; overdue not calculated due to missing deadline; done requires relevant proof/acceptance; valid report periods, no 09/31 and no project extension by copying reports until 2027. Source: all 12 TASK cards, with full mapping in catalog/config.

## 9. KPI/evidence plan — `kpi-table`

**Owner:** `erasmus-annex-kpi`. Columns: KPI/objective/outcome/output/deliverable IDs, scope/type/definition/unit, numerator/denominator, baseline/date, target/date/rationale, method/frequency/owner/evidence/limitations/actual.

Distinguish output, participation/reach, change and contribution to broader impact. Real baseline or "to be detected" with plan, never conventional zero; approved targets proportionate to data and resources. For partner/country/month use defined denominators and check overlap: adding for project and for partner can duplicate the same result.

Controls: major results covered with feasible load; targets not invented by example cells; consistent scope and numerator/denominator; real methods and owners; same definition in monitoring/dissemination/results. Source: DEOR `2-INDICATORS!A5:J52`, monitoring/dissemination; [E 2026, pp.50,64](<../../raw/pdf/expert-guide-2026-v1.pdf>).

## 10. Meeting/event evidence pack — `meetings-evidence`

**Owner:** `erasmus-annex-meetings-evidence`. Schema meeting/activity/event type, host, start/end/timezone, agenda/minutes deliverables, decision/task IDs, participant scope, evidence, privacy and acceptance owner. Document blueprint: agenda with learning/activity outcomes; minutes with decisions and action points; evidence of attendance only when relevant.

Controls: specific daylight saving time and timezone, valid owner/timeline, decisions transferred to task, verifiable document/version. Photos/recordings/certificates do not become automatic requirements and authorizations are not assumed to exist. Source: TASK `MEETINGS!B4:K16` and `CHECKLIST!A4:G73`.

## 11. Results/translations/release register — `results-register`

**Owner:** `erasmus-annex-results-register`. Artifact/deliverable/output/WP/activity/owner, type, language/version, editable source, published URL, license/third-party rights, acceptance criteria/date/reviewer, KPI. An output can have multiple artifacts and languages; record the approved version without exchanging “English” or five template languages ​​as a universal rule.

Controls: editable source and accessibility/license for educational materials according to applicable rules; third party rights clarified; approval before release; KPI/usage distinguish document from outcome. Source: TASK `RESULTS!A3:J35`; DEOR `1-RESULTS!A12:C52`; [P 2026, p.14](<../../raw/pdf/programme-guide-2026-en.pdf>).

## 12. Effort/timesheet/staff statement register — `timesheets-register`

**Owner:** `erasmus-annex-timesheets`. Generation conditional on the use and requirements of the relevant template/contract. Schema effort ID, person ref, partner/role/WP/activity/date/period, hours/mandays/conversion assumption, internal rate source, evidence/approval, requirement source/status. Workbooks provide an index/effort allocation, not a complete staff statement to sign.

Controls: same person/period not counted twice; expected effort distinct from actual; motivated hours-days conversion; internal tariff distinct from official installments; privacy and access. TASK `TIMESHEETS!B7` does not establish a universal obligation. Source: TASK `TIMESHEETS!B3:D47`, `SETUP!D6:K15`; DEOR staff costs.

## 13. Reporting/evidence checklist — `reporting-checklist`

**Owner:** `erasmus-annex-reporting-checklist`. Schema requirement ID, document kind/origin/applicability, activity/reporting period/deliverable/owner/due, evidence/version/status/reviewer/review date. Each line declares the source of the obligation or internal methodological necessity.

Controls: missing other than not applicable, valid deadline/period, complete status with evidence/approval, no universal requirement of five reports or photos. Terminal Checklist reads evidence and does not replace productive data. Source: TASK `CHECKLIST!A4:G84`, reporting blocks of the two budgets.

## 14. Branding e modelli documentali — `branding-register`

**Owner:** `erasmus-annex-branding`. Schema asset/template ID, type, project/language/version/owner, emblem and statement sources, license, approval/file. Relevant templates: project identity, document/presentation, report, attendance declaration when really necessary. TASK `TEMPLATES!B5:C11` preserves expected names/links; the documents themselves are not attached to the workbook.

Controls: current emblem/funding statement and relevant grant; rights to assets; sample distinct from real content; minute/attendance fields adapted and permissions not invented. Official source for communication in [search for good practices](../research/buone-pratiche-application.md).

## 15. Exploitation e sustainability — `follow-up-plan`

**Owner:** `erasmus-annex-follow-up`. Schema continuity/output/outcome/deliverable/user/adopting organisation, adoption step, owner, period/review, maintenance resources/funding/commitment status, KPI/target/evidence/risk/open access. Specify routine use and maintenance beyond the grant with confirmed resources or explicit intentions.

Controls: adoption distinct from reach; real version output; commitments not made for others; documented resources; motivated targets; rights/access/fees verified if applicable. DEOR `6-FOLLOW-UP PLAN!C4` warns that it is example and `C7:H15` concerns CONNECTED/adults 55+: do not copy “20,000 users”, five years or percentages as DEOR/new project commitments. Source: follow-up sheet, monitoring `B23:F24`, TASK results; [E 2026, pp.54–57](<../../raw/pdf/expert-guide-2026-v1.pdf>).

## Common checks before exporting a concrete attachment

1. Solve the necessary `to-confirm` and verify current call/form source, without transforming template into regulation.
2. Check for uniqueness/foreign keys and version changes: same partners/WP/activity/deliverable in each output.
3. Reconcile quantities/times/effort/budget/targets, preserving scope and units; do not count internal estimates as grant unit costs.
4. Check formula error and logic in relevant engine with input boundaries; saved cache is not proof of recalculation.
5. Check relevant privacy/licensing/protection, legal for signature documents and format/attachment requirements.
6. Render and visually check all sheets/pages of the produced file; export only the version approved for specific purpose/year.

These are professional acceptance checks of the system, not new quality thresholds or mandatory Erasmus+ lists. The evaluator examines the application against the official criteria; the quality owner checks consistency between attachments and dossiers. The production awaits the real data of the specific project.

## Processo condiviso e limiti ESC

These templates are reusable as layouts/methods for ESC after specific action, role and funding verification. Erasmus financial content and historical examples do not become ESC rules. Use the common pattern in [[project-memory-contract]]; Workbook column names are common entity aliases, not additional master data. Each WP KA220 declares `kind=management|implementation`; IDs do not demonstrate their nature. [[workflow-erasmus-esc]] · [[response-contract]] · [[esc-2026-routing]]

## Timetable of KA1 Youth activities

Dedicated Owner: `erasmus-annex-activity-timetable`; blueprint `ka1-activity-timetable` to `config/annexes.json`. For KA152 the guide requires the timetable of each planned exchange and preparatory visit, [source physical page157](../../raw/pdf/programme-guide-2026-en.pdf). Check format/template and upload of the call; do not transfer the obligation to other actions.

Columns: activity ID, day/date, start/end, session, learning objective, non-formal method, role of young people and proof of their proposals, owner/facilitator, venue, accessibility, reflection/Youthpass, linked risk. Reconcile duration and calendar with activities and budget; guarantee consistency of the inclusion/protection plan without inventing confirmations. The table is a proposed scheme, not an already approved program or an official template.
