# Review and Report Contract

The contract distinguishes verifiable content from session provenance. The exact technical structures and available commands are governed by `scripts/stage_gate.py`, `scripts/workflow.py`, and the phase criteria in `config/`; do not add fields required only in report prose without updating the maintained contract.

## Sufficient Package

The package contains an identified, frozen manifest; application identity (`program`, `year`, `action`, `sector`, country/agency and role/round when relevant); phase and attempt; relevant production artifacts; shared model; evidence register; form profile when needed; acceptance criteria; and action checklist. Each listed file has a safe relative path and SHA-256; sources retain source ID, version/hash, page or section, and scope. The criteria and profile are also snapshotted in the package: a link to an editable configuration is not enough.

Each criterion specifies a stable identifier, what must be observed, its source and scope or the fact that it is a local convention, the artifacts to check, the expected method/result, and its relevance to the gate. Distinguish `requirement`, `award-criterion`, `recommendation`, and `local-quality-check`. Read the selected checklist together with relevant original passages and general conditions, avoiding a selection of favorable snippets.

The production report may be an artifact to check, but it is not the premise of truth. The mandate does not include an expected score, suggested approval, or prior private discussions. A later correction creates a new version and package: the snapshot already reviewed is not altered.

## Minimum Substantive Report

The report identifies the manifest/hash, phase, attempt, and version, and returns:

- `verdict`: `accept`, `revise`, or `blocked`, with a concise reason;
- `checks` covering all manifest IDs in `acceptance_checks` and `compliance_checks`: ID, reasoned `pass|fail|not-applicable|unknown` status, artifact and location, evidence/source ID and locator, check performed;
- identified findings: `blocking|major|minor|editorial` severity, distinction between requirement/merit/recommendation, artifact and locator, evidence, verifiable correction, dependent phase to reopen;
- review limitations and missing information, without turning unknown into zero or a hypothesis into fact;
- critical summary: observed weaknesses or reasoned absence, relevant alternative, and basis for the decision;
- status of relevant automatic checks and references to their results.

An author declaring a finding “resolved” does not close it: the new validator verifies the correction in the new version. A not-applicable item has a reason specific to the route/phase; it is not a way to avoid coverage.

In code, findings are `discrepancies`. The package contains `review-schema.json`: the report uses `packet_id`, `packet_sha256`, `phase`, `reviewer_id`, `verdict`, `summary`, `checks`, `discrepancies`, and the other specified fields. Evidence for each check locates a frozen file using `file_id` and `locator`; a URL or generic judgment is not enough. Use the fields required by the actual schema, without replacing them with editorial aliases; the manifest provides the IDs to cover. The production report is hash-linked to the review, but its content and prior conclusions are not sent to the validator. The validator judges the artifacts and evidence, not the author's report.

## Coordinator-Observed Attestation

The dispatch receipt retains the agent's tool identity, `fork_turns="none"` call, local session/attempt ID, material authors, and all prior validators for the application. The new validator's ID is distinct from the authors and previous validators. The receipt links the frozen manifest, the report actually produced, and its hash, and is recorded by the orchestrator that observed the tool.

The operational path is `validation/packets/<packet-id>/manifest.json` with snapshot and schema; dispatch receipts are in `validation/dispatches/` and reports have exclusive paths in `validation/reports/`. `stage_gate.py prepare` freezes artifacts/criteria and links the production report; `dispatch` records the localized tool observation, and `verify` checks the report. `workflow.py record` links the package/report to the phase; a production `pass` requires an independent `accept` verdict on the same version.

An UUID invented in the report or the phrase “I am independent” does not prove isolation. The script can verify claimed uniqueness, structure, and integrity; it cannot certify the absence of hidden context in the runtime. If the tool does not provide a new session without history, report the limitation and do not pass the gate as independent. “External” means outside the phase's author group; it does not require an external provider or account.

`review-schema.json` is the fillable template; `report-schema.json` is the structural schema. The scripts verify the contract manually plus package-specific constraints. Repair/QA include current findings, the baseline, and archived findings with their origin, without transmitting previous verdicts. Null country, agency, role, and round values remain to be verified.
