---
program: SHARED
status: operational-method
---
# Workflow to design Erasmus+ and ESC

The proposed process is a good production sequence, but leaves some crucial checks too late. Research can disprove the idea, not just support it. Economic feasibility, risks, measurement and partner commitments must be set together with the design. Attachments are refined after drafting, but their data exists before writing. The final evaluation verifies an application that has already undergone intermediate checks.

This is a working method of the assistant, not a mandatory sequence of the program. Criteria, priority, funding and formulary depend on `program`, annuity, action, sector, country, role and round. **Erasmus+ and ESC share the process, not the rules.**

## Phase 0 before applying

A new idea is born in `work/idea-lab/`, before the file. The [Phase 0](../../docs/phase-zero-idea-lab.md) procedure keeps brainstorming free and makes convergence verifiable: alternatives, current official routes, hierarchy of priorities, primary/secondary targets, needs→problems→solutions→activities→outputs→results→impact chain, scale scenarios and tiers only when they exist. The product concludes with `PROCEED`, `REFINE`, `PIVOT` or `STOP`, with no official rating or funding forecast.

A new validator checks the frozen version. `PROCEED` accepted then requires the user's observed choice for that version and route; only then does the workflow create `projects/<ID>/`. The subsequent `idea-validation` remains mandatory and applies the complete award criteria checklist for the route. `REFINE` and `PIVOT` produce a new version in the Idea Lab; `STOP` keeps reasons and alternatives without creating a nomination.

## Dieci fasi e decisioni critiche

| Phase | Work and observable product | Check to proceed |
|---|---|---|
| 1 Formal validation of the idea | Accepted Phase 0 snapshot, brief, chosen route, preliminary eligibility, capability and full variant/role award checklist | Confirm that the promoted version holds true compared to the real course and that future gaps have a credible plan. An incompatibility or an implausible need reopens Phase 0/design; don't invent a priority to justify an idea that has already been decided. |
| 2 Research needs and impact | Register of sources, local and EU data, authentic consultations, baselines, existing interventions and hypotheses for change | Distinguish observed problem, hypothesized cause and solution. Consider a local solution without EU funding when appropriate. Don't use funded examples as proof of effectiveness. |
| 3 First concept note | Problem, target group, interim objectives, rationale for change, candidate activities, partnership and indicative resources | Legible and proportionate concept; visible hires, no results or declared partners confirmed without proof. |
| 4 Intervention logic | Needs → objectives → activities → outputs → results → impact; applicable priorities, KPIs and sustainability | Every connection has a causal explanation and a verification. Cover relevant impacts on organisation, participants, community and European level; do not fabricate impacts on all levels unless justified. |
| 5 Activities, WP and responsibilities | Activities/tasks, WP, deliverables, owners for documented skills, calendar, first budget table, risks and monitoring | Realistic dependencies and capabilities; reconciled costs; no decorative assignments. For actions without mandatory WPs use a proportionate structure and do not impose a KA220 model. |
| 6 Concepts for partners | Shareable version with roles, contributions, loads, indicative allocations, required decisions and open issues | Actual alignment and recorded confirmations. Generating the document does not authorize sending, signing or contact with third parties. |
| 7 Answer plan | Matrix for each question: criteria, elements, evidence, structure, limitation, missing data and references to attachments | Relevant form and coverage verified; unknown limits are open problems. The model tables guide the answer, the examples do not become facts. |
| 8 Extensive Application | Final text of each field in `answers.json`; presentation in `draft.md`; counts and cross-checks | No overruns; same numbers and IDs as the common model. A design deficiency is corrected in the model, not with additional rhetoric. |
| 9 Extensive attachments | Dedicated specialists materialize tables and documents from common data; manifest with internal/optional/required status | Cross-checks of budget, WP, Gantt, tasks, KPIs and risks; upload requirements mentioned. Contracts distinguished between draft, legal verification and version ready for signature. |
| 10 Evaluation and improvement | Independent evaluator, per-criterion findings, weak fixes, full version QA | Clear, evidence-based judgment; no desired grade or funding guarantee. Three initial reviews, then delivery of unresolved issues. |

## Loop and memory

The built-in register uses `idea-validation → needs-impact-research → concept-note → intervention-design → work-packages → partner-concept → answer-outlines → application-draft → annexes → review → eventuale repair/review → qa`. `qa` is the closing control of phase 10. For limited interventions the `compact` process remains available.

Each integrated report contains `critical_review`: **weaknesses** (limitations or weaknesses observed, or a precise reason if they do not emerge), **alternatives** (relevant option or reason for keeping only one), **decision_basis** (evidence and criterion for the choice). No artificial share of criticism: Don't invent flaws to appear harsh. Separate inadmissibility, unproven content, doubt and editorial preference.

Criticism is part of each phase; the independent evaluator intervenes at least on the concept when the design is complex and on the integrated application. If a source, partnership, calendar, or critical data point changes, use `workflow.py invalidate` towards the first dependent phase or document the reopened controls in the repair report. Already consumed revisions remain tracked. Sources and reports have hashes; receipts archive the contents instead of pointing to an overwritable file.

Before the review **text, template, responses, register of sources and attachments** are frozen. A changed budget or Gantt requires a new integration, even if the text remains identical. The specialists work on distinct outputs, at most three in parallel in addition to the coordinator. Logical dependencies remain sequential.

## Risorse operative

[[project-memory-contract]] · [[response-contract]] · [[ka220-question-playbook]] · [[annex-template-catalog]] · [[annex-blueprints]] · [[esc-2026-routing]] · [[indice-azioni]]

The KA220 playbook is derived from the 2025 user model, it is not the official 2026 playbook. Do not apply to ESC, KA1, KA210 or Centralized Sport. ESC routes and their headings are in [[esc-2026-routing]].

## Gate at the end of each step

Each completed phase has a new validator who is independent from all previous authors and validators of the application. `fork_turns="none"` is the actual orchestrator call; Declared file/IDs do not themselves certify the runtime. The package freezes the phase product, input, form profile, original route tests, checklist and acceptance criteria. Includes approved dependencies; in repair/QA includes findings log and baseline of disputed steps, without conveying a grade or desired outcome.

The report covers each check once, documents limitations, checks performed, tests, discrepancies/classification and phase to reopen. `accept` makes the dependent step proceedable; `revise` and `blocked` keep fixes or impediments open. A changed approved product requires explicit invalidation, which preserves history and marks passed gates. The initial budget is one attempt plus the three configured reviews; do not increase it yourself.

[[compliance-checklists]] contains specific reminders for Youth actions. The user form model is KA220-YOU, not universal. Partial checklists require full route reading and source-grounded augmentation for the actual call.

[[orchestrator-architecture]] describes responsibilities, dependencies, packages, and reopening phases.
