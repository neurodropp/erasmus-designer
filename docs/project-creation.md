# Create and resume a project

The engine is shared; an application is a dossier in `projects/`. Open the Erasmus Designer root in Codex; do not duplicate skills, sources, databases, or native configuration inside each application. The Codex project is the engine container; the dossier is the operational context for an individual application.

## Phase 0 and creation

For a new idea, start in the preliminary workspace without choosing an action and sector by analogy:

```sh
python3 scripts/workflow.py idea-init bridge --title "BRIDGE" --year 2026 --max-revisions 3
python3 scripts/workflow.py idea-status bridge--2026
```

The command creates `work/idea-lab/bridge--2026/`, not `projects/`. Complete the free-form `brainstorm.md`, structured register `brainstorm.json`, `research/checklist-phase-zero.json`, and versioned products `stages/phase-zero/decision.md` and `decision.json` according to the [procedure](phase-zero-idea-lab.md) and [contract](../wiki/templates/phase-zero-decision-contract.md). The gate requires a main formulation, a relevant alternative, provenance, and the reason for convergence; an exception without an alternative must be localized and evidenced. Technical evaluation uses the same principle as dossier gates:

```sh
python3 scripts/stage_gate.py prepare-idea bridge--2026 --report work/idea-lab/bridge--2026/reports/phase-zero.json --producer-id ID_REALE_PRODUTTORE
python3 scripts/stage_gate.py dispatch-idea bridge--2026 --packet ID_PACCHETTO --agent-id ID_NUOVO_VALIDATORE --session-id ID_SESSIONE --fork-turns none --observation work/idea-lab/bridge--2026/sessions/spawn.json
python3 scripts/stage_gate.py verify-idea bridge--2026 --packet ID_PACCHETTO --report work/idea-lab/bridge--2026/validation/reports/REPORT_REALE.json
python3 scripts/workflow.py idea-record bridge--2026 --report work/idea-lab/bridge--2026/reports/phase-zero.json --validation-packet ID_PACCHETTO --validation-report work/idea-lab/bridge--2026/validation/reports/REPORT_REALE.json
```

The IDs and files in the example must come from a real `fork_turns="none"` spawn; do not create them to simulate the gate. If the accepted recommendation is `PROCEED`, present the exact version and route to the user. Record the observed choice with `idea-decide --decision-file FILE`: the file uses `phase-zero-human-decision-v1` and binds the decision, rationale/provenance, observed reference, packet ID, and hash. Only after this transition:

```sh
python3 scripts/workflow.py promote-idea bridge--2026 --project-name bridge --title "BRIDGE"
```

Promotion derives the action and sector from the verified route, copies the decision/checklist/packet into `inbox/phase-zero-handoff/` with manifest and hash, and creates the `integrated` process starting from the `idea-validation` phase. `REFINE` and `PIVOT` reopen the Idea Lab, consuming a revision; `STOP` does not create a dossier.

## Import of already routed work

From the root, for work that has already been routed and imported with a real action and sector:

```sh
python3 scripts/workflow.py init bridge --title "BRIDGE" --action KA220 --sector YOU --year 2026 --country IT --agency AIG --process integrated
python3 scripts/workflow.py status bridge--ka220-youth--2026
```

The first line generates `projects/bridge--ka220-youth--2026/`. Name and type are distinct in the state: `name=bridge`, `title=BRIDGE`, `action=KA220-YOU`, `sector=YOU`, `id=bridge--ka220-youth--2026`. The youth tag is readable; the route retains the official code. The folders do not confirm eligibility, partners, consultations, or the current application form. These commands are examples: they are not run to create fictitious applications in the engine.

Direct init preserves compatibility for migrations and bounded assignments that have already been routed, but records `phase_zero_status=bypassed-direct-init`: it does not attest brainstorming, route comparison, or a Phase 0 decision. Do not use it as a shortcut for a new idea.

Other examples:

```sh
python3 scripts/workflow.py init voices --title "VOICES" --action KA152 --sector YOU --country IT --agency AIG
python3 scripts/workflow.py init community --title "COMMUNITY" --action ESC30 --sector ESC --country IT --agency AIG
```

Corresponding folders: `voices--ka152-youth-exchange--2026` and `community--esc30-solidarity--2026`. For other routes, the tag derives from the full code; check `config/actions.json`. Years without a corpus are rejected, not silently replaced with 2026. After a new call is indexed, this constraint must be extended along with the sources and profiles.

`name` is a lowercase slug of up to 64 characters, letters/digits/hyphens. The double separator -- is reserved for full IDs and cannot appear in the short name. `--title` preserves the readable name. For two projects with the same name but different types, always use the full ID: an ambiguous short name is rejected. An existing folder is not overwritten, even if it contains only input.

## Generated tree

```text
projects/bridge--ka220-youth--2026/
  AGENTS.md, README.md          dossier context and instructions
  brief.md                     request, facts, decisions, and missing data
  project.json                 v2 model: partners, needs, WP, activities, tasks, deliverables, milestones, KPIs, budget
  evidence.json                real evidence and locators
  answers.json, draft.md        canonical answers; initially empty
  annex-manifest.json           files, owner, status, and upload constraints; unverified
  findings.json, state.json     findings, identities, phases, revision budget, and gate
  inbox/                       material supplied for this application
  research/                    research on needs and impact
  memory/                      canonical events, seal, and local recovery of working memory
  design/                      concept and intervention logic
  partners/                    partner competencies, contributions, and confirmations
  application/                 outline and editorial versions
  annexes/<tipo>/               relevant annex workspaces
  production/<phase>/           separate producer outputs; attempt when needed
  stages/<phase>/               integrated product; product.md only after actual work
  reports/, receipts/           production reports and frozen receipts
  validation/packets/           manifest, snapshot, and schema of new gates
  validation/dispatches/        receipts of observed sessions
  validation/reports/           exclusive outputs of new validators
  sessions/                    actual spawn observations
  exports/                     verified deliverables for the requested destination
```

Phase folders are prepared for the selected process; attempts, products, and packets are created when run. No phase is completed by creating its folder. `draft.md` is empty; registers contain no approved values or placeholders to submit.

## Annexes and application form

`config/project-layout.json` is the maintained tree contract, with indicative defaults by action/family. `config/annexes.json` maintains blueprints and owners. To add workspaces during initialization:

```sh
python3 scripts/workflow.py init learning --action KA220 --sector ADU --annex gantt-table --annex reporting-checklist
```

To add a workspace to an existing dossier, the coordinator can create only the folder under `annexes/`, assign an owner, and update the manifest when an actual file exists. An unknown annex ID is rejected by init. Do not create a new dossier just to add an annex. KA220 folders include budget, dissemination, Gantt, WP, monitoring/risk, contracts, task file, KPIs, results, and follow-up. They are not a list of mandatory uploads. Timetable is prepared for KA152; applicability of other timetables requires the source for the relevant action.

`--form-profile` is optional in init: do not associate DOCX2025 as if it were verified for a new call. Before answer-outlines, the coordinator uses bind-form and documents the current profile/form, applicable fields, and actual limits. The user playbook is exclusively for KA220-YOU; KA1 and ESC require distinct profiles. The process remains open while decisive information is missing. [Form intake](form-intake.md) provides for a user-supplied export or authorized reading on the authenticated platform.

## Resumption and validation

A request to Codex could be: “Use erasmus-designer and resume projects/bridge--ka220-youth--2026. Read the status, brief, findings, and receipts; continue from the open phase.” The coordinator updates project.json through integration; specialists write to separate paths. The application and annexes derive from the same IDs and numbers.

At each resumption and before a phase, open `python3 scripts/project_memory.py context ID --phase PHASE`; `workflow status` includes the memory context in its output without saving it to the state. The responsible person records new facts, choices, relevant options, and status changes with author, provenance, and observed evidence. `workflow init` creates empty memory; for earlier dossiers, use `project_memory.py init ID` explicitly. Confirmations do not automatically integrate data into the model or close gates. [Working memory contract](project-working-memory.md) describes append-only events, a rebuildable index, supersessions, hypotheses, and contradictions.

```sh
python3 scripts/stage_gate.py prepare bridge--ka220-youth--2026 --phase idea-validation --report projects/bridge--ka220-youth--2026/reports/idea-validation.json --producer-id ID_REALE_PRODUTTORE
```

stage_gate CLI inputs may be absolute or relative to the engine root (as in the examples); for compatibility, dossier-relative paths are also accepted if the file does not exist in the root. In all cases, reports, observations, and artifacts must remain in the assigned dossier. Preparation requires an actual report and product. Then a new fork-none spawn writes the independent report; dispatch and record use observed IDs. Read [orchestrator-protocol.md](orchestrator-protocol.md) and [report-contract.md](../skills/erasmus-stage-validator/references/report-contract.md). Do not simulate a gate to test the structure.

## Legacy, transfer, and maintenance

Do not directly move historical `wiki/projects/` dossiers: the resolver recognizes them and requires an explicit migration, because receipts and manifests may freeze paths. Do not rename accepted folders: IDs and paths are part of the verified context. The current engine does not automatically migrate these archives.

For replication of the engine, memory, and dossiers, read [replication.md](replication.md). Check the structure with `python3 scripts/structure_check.py`; real applications also require their own status, form, model, and gate checks. A technical check of the tree does not demonstrate application quality or compliance.

KA120/KA150 accreditations and Quality Labels are distinct from grant requests in matrix0.2.0: init does not require fictitious amounts. QA checks the plan/capacity and relevant evidence according to the [mode](action-modes.md), as well as the real call form and checklist; the structural distinction does not attest full eligibility.

For engine0.2.0, init resolves the [application mode](action-modes.md) and initializes relevant fields without fictitious evidence. Before prepare, generate and complete the [phase checklist](checklist-workflow.md) at the standard path research/checklist-PHASE.json: the new protocol requires it and also freezes the checks matrix.

The current version also initializes `wayfinder/` with an empty map, `approval/` for future decisions on the exact QA bundle, and `validation/lifecycle/` for recovery events. Folders and the map do not create decisions or consent: use [Wayfinder](wayfinder.md) and [approval](human-approval.md). For an earlier dossier, initialize Wayfinder explicitly; do not import assumptions from the brief as confirmed.
