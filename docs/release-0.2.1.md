# Release 0.2.1 and Replication

Local review dated September 12, 2026. The [corrections](repairs-0.2.1.md) are based on a review; subsequent checks without production history accept all 22 findings and the model's six additional residual issues. The integrated suite passes 243 tests. Verification of the final container is separate, with an independent report alongside the ZIP; this note does not replace that result. Excluded audit evidence is not shipped.

## Memory and Local Evidence

An official LWC changeset updated 26 distinct pages. A subsequent changeset restored the non-normative provenance of the memory contract, which had been omitted during a subtitle refresh: the initially failed comparison remains in the receipts. Final verification: 138 unrelated pages identical, 97 sources unchanged, 329 citations and provenance records preserved, and no lint findings. Subsequent contract changes are recorded with new checkpoints and dedicated comparisons.

The updated semantic archive was imported into an empty root in the same environment, reusing the official 0.18.5 binary. Discovery and the evidence index were rebuilt from the originals; SQLite/foreign keys, page/source contents, links, citations by content_hash, and provenance were verified. The map was reconciled through the CLI; the second application was idempotent. A subsequent export/import preserved identical reconciliation-history files. No runtime was installed on another machine.

During import, 96 numeric IDs changed, as in the previous trial; the semantic archive preserves content without promising identity of origins, IDs, operational history, or database bytes. The originals remain in the identity catalog and complete checkpoint. Original receipts are not rewritten. New v2 receipts are identified by the complete digest; v1 remains readable.

## Delivery Components

The final container includes the engine with manifest/checksum, CLI semantic archive, compressed full recovery derived from the official checkpoint, safe unpack tool, and instructions. It includes the new v2 contracts, owners/skills, and case-file creation procedures. External certification avoids cycles between package hashes and the report.

`recovery-full.db.zip` preserves the complete checkpoint state, including operations and changesets. It is a backup separate from semantic memory: do not import it with decompress or copy it over the active wiki.db. Full recovery must follow the [replication procedure](replication.md), using CLI checkpoint restore and verification. A complete restore on another machine has not been attested.

## Operational Limitations

The corpus is 2026, regulatory checklists are partial, and the KA220-YOU 2025 form is historical: obtain and verify the current form for each application. Earlier models require intentional migration before strict mode. Derived annexes are semantic views until materialized/rendered according to the skill. Tests do not attest to any real project, signature, submission, or funding.

On a new host, runtime, discovery, MCP, a genuine fresh spawn, and rendering tools must be tested; credentials, accounts, model instances, and plugins are not transferred through the archive. Release 0.2.0 and the original audit remain unchanged as history; this release does not overwrite them.
