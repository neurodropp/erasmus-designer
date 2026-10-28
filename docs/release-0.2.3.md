# Working Memory and Maintenance, Version 0.2.3

This version adds persistent memory and source maintenance to the Erasmus+ and ESC engine. [Version 0.2.2](release-0.2.2.md) preserves the historical record of the native-write block: after the user's authorization and the effective change in permissions, the migration was applied. Earlier releases and frozen receipts have not been rewritten.

## Added capabilities

- [erasmus-project-memory](../skills/erasmus-project-memory/SKILL.md) records decisions, facts, hypotheses, and open questions. Each application has its own log, local seal, rebuildable index, and context in `projects/<ID>/memory/`. Engine decisions are stored in `work/engine-memory/`, in a separate namespace. The orchestrator reads the context each time work resumes; an internal decision is not equivalent to user approval and does not automatically change the model, responses, or gate.
- [erasmus-knowledge-maintenance](../skills/erasmus-knowledge-maintenance/SKILL.md) manages the two programme guides, the two expert guides, national provisions, and forms. Staging, a complete revision and field comparison, evidence for matches, and dependency impact analysis must precede verified promotion. Existing dossiers are migrated selectively. Character limits are not inferred from sample PDFs, and Erasmus criteria are not carried over to ESC.
- The local native surfaces comprise 29 definitions and 29 skills. The installer preserves customizations and resolves paths against the effective root. The actual reload and discovery by the new Codex process remain to be observed after the user restarts it.
- The gate also freezes the available memory log, seal, and context. Changing memory during a review requires a new package; recording the outcome after the gate closes does not rewrite the history of accepted products.
- The engine container includes only `work/engine-memory/` among the workspaces. Real application files require a separate, explicit transfer; temporary acquisitions and other workspaces are excluded.

## Scope and checks

The active corpus remains 2026. A new programme year requires verified guides, updates to the engine's effective capabilities, and route checks; changing a JSON label is not sufficient. Creating the maintenance process does not certify that the regulatory content is fully up to date as of today. Demonstration acquisitions remain outside the active corpus.

The integrated suite passed 297 tests after the editorial index was rebuilt, without regenerating summaries. Checks of the 97 sources, the structure of the 29 skills and definitions, the integrity of the six memory records, and persistent retrieval all passed. The shared canonical memory retains identical records across all 164 pages and 97 sources; the semantic archive and complete checkpoint are reused byte for byte.

Production checks and the subsequent independent report are retained in the intervention dossier. For the frozen delivery, validation records are kept outside the ZIP container; excluded private audit evidence is not shipped. Checksums identify the verified bytes; they do not imply external signatures, author authentication, successful installation on another computer, or assessment of a real application. Gate rules and organizational responsibility remain applicable.

To replicate the setup, follow [the short guide for another computer](quick-start-another-computer.md) and the new container's `INSTALLA.md`, which reports the engine's effective checksum. Accounts, authentication, and model availability must be verified on the target system.
