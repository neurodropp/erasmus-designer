# Engine Corrections 0.2.1

A private audit in September 2026 reproduced 22 findings against the previous version: 10 major and 12 minor. The original reports remain unchanged and are excluded from this delivery. Version 0.2.1 fixes all reproduced technical cases and the six additional model residuals found during follow-up checks. Fresh Astra reviews with no production history accepted the corrections within the local scope; the register, rejected attempts, and evidence remain in the private audit records and are not shipped.

## Corrected contracts

| Area | Findings | Required behavior |
|---|---|---|
| Orchestration | ED-01,04,05,15,16,17 | Resolver confined before mutations; no skipping to future phases; only active accepted dependencies; repeatable rejected attempts; frozen historical observations; complete report schema; dispatch of the current phase only. |
| Memory and sources | ED-06,20,21,22 | Extraction manifests from verified originals; checks of derived bytes and the index; complete route dependencies; KA150/KA151 page 149 overlap; PDF locators distinct from HTML discovery pages. |
| Model and form | ED-07,08,09,10,11,12,13,14 | Mandatory output/KPI/WP relationships; task/deliverable/milestone registers; consistent KA220 management; contracts recognized by ID as well; coverage of question/instance pairs; unambiguous profiles; positive duration; non-negative quantities and rates. |
| Installation and transfer | ED-02,03,18,19 | Explicit LWC root; native-surface preflight; export of reconciliation history; verified chain for subsequent transfers. |

Specifications and test cases are in the notes on [orchestration](orchestration-repairs-0.2.1.md), [sources](knowledge-repairs-0.2.1.md), [model/form](model-form-repairs-0.2.1.md), and [portability](portability-repairs-0.2.1.md). These are local engine checks: they do not add regulatory requirements to a call.

## New and existing application files

New application files use `project-model-v2`: the shared model also includes tasks, deliverables, and milestones. Annex owners derive annexes from these registers and retain the same IDs. Projections provide semantically consistent data; a deliverable XLSX/DOCX/PDF must still be materialized and verified according to the relevant skill.

An earlier model can be read in non-strict mode; strict verification requires explicit migration, without inventing tasks or deliverables. The orchestrator compares the earlier structure with the [memory contract](../wiki/templates/project-memory-contract.md), integrates the actual data into the new registers, and reopens the first affected phase. Historical reports and receipts are not rewritten. No real application file was migrated during this engine correction.

An evidence index predating the derived manifest is rejected. Rebuild it from verified originals:

```sh
python3 scripts/brain.py rebuild --no-cards
python3 scripts/brain.py check
```

`--no-cards` preserves maintained editorial summaries. This does not update sources online or certify that calls, forms, or national priorities are still current.

## Verification and limitations

Review status: **22 original findings and six additional model residuals accepted within the local technical scope; 243 integrated tests passed**. The private verification summary (not shipped) links to the independent reports included in the delivery. The underlying private audit evidence is excluded and is not shipped. The final package also requires its own fresh recheck, with the report kept outside the ZIP. Validators receive frozen inputs and a mandate, without the authors' conversation, and also examine discrepancies introduced by the corrections.

Current forms for each application still need to be obtained, regulatory checklists for the actual call need to be completed, and an installation on the target computer needs to be tested. No technical evidence replaces assessment of the project's merits, substantive review of the contracts, or the agency's actual evaluation. No applications, contracts, or messages to partners were sent.
