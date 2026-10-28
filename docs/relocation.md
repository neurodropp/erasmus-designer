# Relocating a case file without losing its history

A validation package preserves both a frozen copy and the path to the original file. For example: `/old/engine/root/...` might become `/new/engine/root/...`. The bytes may be identical, but the old path is unavailable on the new PC. Rewriting the manifest would change the package hash and break previous receipts.

The system therefore keeps the archives unchanged and distinguishes their integrity from the ability to resume work. The new [read-only audit](../scripts/relocation_audit.py) applies an external mapping solely to compare files, without modifying them or accepting gates:

```sh
python3 scripts/relocation_audit.py ID --old-root "/path/to/original/engine"
```

The JSON distinguishes preserved snapshots and receipts, mapped originals, missing/changed files, and the need for a new baseline. A matching hash does not amount to revalidation. The audit does not replace full verification of the receipt chain, does not migrate `wiki/projects/`, and is not consumed by the workflow to ignore old paths.

Before resuming a transferred case file, record the mapping and audit outside the frozen packages. If accepted products have remapped paths, a new baseline and invalidation from the first affected phase with a new validator are required. The workflow can invalidate products from reopened phases but continues to require intact archived receipts: an incomplete copy must be recovered from backup. Do not reset attempts or revisions, alter historical attestations, or mark a phase accepted solely because of a transfer.

Transferring the engine alone does not have this problem: native agents are regenerated in the new root, and each new project starts with new paths. Absolute origins of LWC sources remain historical provenance; citations use the maintained snapshots, which must be verified after import.
