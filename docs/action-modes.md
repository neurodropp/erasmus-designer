# Checks matrix by application mode

The [matrix](../config/action-modes.json) routes all 50 routes in the 2026 catalogue to grant, accreditation, Quality Label, or allocation. It is a control contract for the shared model, distinct from the complete regulatory checklist and the fields actually required by the form.

| Mode | Checker behaviour |
|---|---|
| Grant | Financial request, evidenced eligible financial model, and relationships among activities, partners, results, schedule, and budget. |
| Accreditation | Evidence-backed plan and capacity for accreditation; no fictitious grant or mandatory budget to pass QA. |
| Quality Label | Organisations, role, and label requirements with evidence; no grant amount required. |
| Allocation | Access title, planned activities, financial model, and allocation rules with evidence; requested amount and activity detail only where applicable. |

`project_check.py` resolves programme, exact action, sector, and year; unknown or inconsistent scope fails. QA uses the same strict check through workflow.readiness. Empty tables remain in the model to preserve its schema, but only relevant ones are mandatory. Numbers and references that are present are checked even in a mode that does not require them.

The generator saves the resolved mode and leaves requirement evidence empty. For non-financial modes it initializes `financial_model=not-applicable`, keeping `requested_grant=null`; financial applications remain `unverified` until the model is documented. The declared mode cannot replace the one derived from the catalogue. For accreditations, Quality Labels, and allocations, the checker requires the corresponding evidence field; non-empty text alone does not establish merit, which is for the validator to judge.

The matrix sources are immutable revisions of official guides with hashes and physical page numbers. Maintained checks do not certify every condition of each action. Before applying, the call, round, national provisions, current form, and complete requirements matrix are still needed. Expert guides are used only within their coverage.
