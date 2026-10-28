# Release 0.2.0 preparation

Local preparation on 12 September 2026. No installation or `npm ci` was run on another PC; no cloud transfers, application submissions, or signatures were made. Agent definitions are instructions, not processes to be transferred. Testing on the destination PC is still required.

## Results of the actual import

An LWC CLI 0.18.5 archive was actually imported into an empty memory in a temporary location on the same machine, using the same reused binary. The temporary destination was removed after the test. This was not a new runtime installation or a test on another operating system.

- 164 pages and their contents are identical.
- 97 source snapshots, titles, and hashes are identical.
- 329 structured citations are identical when compared by `content_hash`.
- 1007 links and 6 page provenance records are identical.
- 96 numeric source IDs change; 95 absolute origins become `sync:CONTENT_HASH` as a result of the upstream decompress choice.

The destination's active map was reconciled with [the tool](../scripts/reconcile_lwc_sources.py): the original bytes were backed up identically, only the operational map was replaced, the completion hash was consistent, and a second application made no writes. Original origins and IDs remain in the verified catalog and the fullDB checkpoint. Historical packages and attestations are not rewritten. The comparison that includes origin and ID remains different, as reported in the receipts: byte-for-byte identity between the two databases is not claimed.

Initial test (historical private evidence excluded), reconciliation test (historical private evidence excluded), and content/origin comparison (historical private evidence excluded) preserve distinct results. The initial `passed` field remains false for the comparison that includes differing metadata; `passed_with_documented_metadata_changes` is true for the checked content/citations and reconciliation. Imported lint reported no findings, SQLite integrity was OK, and there were no foreign-key violations; discovery was regenerated and the local index rebuilt with no issues found by `check`.

## Delivery contents

The final package will contain the verified engine archive, CLI semantic memory, compressed fullDB recovery, safe-unpack tool bootstrap, instructions, and separate manifest/checksums. Release certifications are kept outside the engine ZIP to avoid hash cycles. Intermediate candidates remain on the source machine and are not included in the final package.

The fullDB recovery file comes from the online-backup checkpoint created by the official CLI and preserves the complete original state. It is a backup to retain for recovery: do not copy it over the `wiki.db` of an active memory; it is not imported by `decompress` and is not equivalent to the semantic archive. Full recovery requires the backup/checkpoint procedure in the [replication guide](replication.md), with verification and CLI restore in the correct memory. A new PC normally uses `memory.lwc.zst` and reconciliation.

The verified engine passed 127 tests; reusable regulatory checklists remain partial, and current forms must be acquired for each application. Year 2026 only. [Modes](action-modes.md), [checklist](checklist-workflow.md), [form](form-intake.md), [relocation](relocation.md), and [bundle](release-bundles.md) are the shared contracts.

An independent engine recheck accepted the tooling and D1/D2 corrections across 48 frozen files and 127 tests. It did not include the final package or another PC. Its certification is kept alongside the delivery, outside the frozen engine; the excluded audit evidence is not shipped.
