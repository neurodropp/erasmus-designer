# System validation — 12 September 2026

This is the historical bootstrap report. For the current status, see [the current architecture](architecture.md). Some build and check reports have been updated by later runs; the initial changeset receipt retains the result of the first publication.

The bootstrap has been published to the canonical local LWC memory. The result concerns the assistance system, not an application ready for submission or an autonomous service in operation.

| Check | Result and evidence |
|---|---|
| Corpus | 87 sources, 741 test records, 43 routes; report (historical private evidence excluded) |
| Completeness of supplied PDFs | 456 Programme Guide pages and 85 Expert Guide pages; no extraction failures |
| Canonical memory | 138 pages: 87 source maps and 51 summaries; list (historical private evidence excluded) |
| LWC ingestion | 87 jobs completed to compile maps and provenance; report (historical private evidence excluded) |
| Publication | Changeset `erasmus-2026-bootstrap` committed, with a safety checkpoint and materialized projection; receipt (historical private evidence excluded) |
| Lint | No findings in the draft or live version; draft (historical private evidence excluded), live (historical private evidence excluded) |
| Retrieval | 8/8 predefined questions and paraphrases retrieve the expected page among the first five results with the required source IDs, in both draft and live versions; [cases](../tests/retrieval_cases.json), draft (historical private evidence excluded), live (historical private evidence excluded) |
| Local integrity | No hash, extraction, or index issues; report (historical private evidence excluded) |
| Scope and workflow | 18 tests passed: [scope](../tests/test_brain.py), [workflow](../tests/test_workflow.py) |
| Skills | Seven skills validated; the coordinator was revalidated after integrating the retrieval commands and workflow register |
| MCP and configuration | TOML files readable, MCP handshake successful, and four tools exposed; smoke test (historical private evidence excluded) |

The tests verify that unavailable programme years and KA210-HED are rejected; sectors are inferred correctly; national provisions are not treated as rules for EACEA actions; youth priorities are not automatically applied to KA210; and HE mobility funding rules are not treated as KA220 rules. The workflow does not advance when blocked, rejects a draft changed after freeze, requires serious findings to be verified, and observes the revision limit. The missing-index test deliberately triggers an error on a nonexistent path; the check of the actual index is clean.

A specialist's behavioral test also handled correctly a university's request for “KA210-HED, €120,000 contribution,” distinguishing sector from organization type, grant from total project cost, conditional alternatives, and instructions embedded in source materials. This qualitative test is not a statistical measure of model reliability.

The initial maps and completed ingestion jobs do not demonstrate an exhaustive regulatory analysis of every action. The initial summaries provide deeper coverage of Italian priorities, good practices, and KA210/KA220 award grids. The retrieval tests measure eight stated cases, not the entire corpus of knowledge. The crawl is limited to the official sections acquired; errors and pages not acquired are listed in the report (historical private evidence excluded).

The MCP server was started and queried at the protocol level in a temporary process, then stopped. Codex must discover the new configuration by reopening the project. No real application was started because the organization, needs, partners, and application form are missing. Any future work must verify the call and corrigenda, round, deadlines, and applicable provisions online: local integrity does not certify that online information is current.
