# Orchestration Repairs 0.2.1

Immutable baseline: Astra audit dated 12 September 2026, findings ED-01, ED-04, ED-05, ED-15, ED-16, and ED-17. The underlying audit evidence is excluded from this distribution and is not shipped. These changes concern the technical register; they do not attest to the quality or eligibility of an application.

## Paths and writes

`project_paths.confined_path`, `project_input`, and `preflight_dossier` apply the same confinement to workflows and gates. Commands accept absolute paths, `projects/ID/...` paths relative to the engine, and paths relative to the application dossier. Every component is checked before reads, copies, or writes. Symbolic links beneath the trusted root are rejected, even when they point to an internal file; this is an explicit, conservative restriction. To use an external input, copy its bytes into the dossier while preserving its provenance and hash.

`init` also verifies every layout path before creating the directory: an invalid layout writes no state, model, or partial directories.

`prepare` verifies all inputs and accumulates snapshot bytes in memory; it creates the package only after verification is complete. An invalid requirement or path leaves no partial package. `route_evidence` calls the read-only verifier `brain.integrity_for_root` before reading or freezing the corpus: the originals register, derived-file manifests, both page and full-text copies, index, and scope must be consistent. The `general_sources` dependencies are consumed for Erasmus+ and ESC; the package includes metadata and the source register.

Receipts are created with exclusive creation, preventing an archive from being overwritten. State is saved to a new temporary file in the same location, then the final file is replaced. Ambiguous forms are rejected by the shared validator `form_profile.validate_profile`, including during bind/readiness. A profile belonging to another dossier cannot be bound to the selected application. New models declare `project-model-v2` and initialize the common TABLES, including tasks, deliverables, and milestones.

## History and resumption

`invalidate` is a rewind: it requires a productive phase that has already been reached and all preceding accepted dependencies still active. It cannot advance a newly created application or skip a reopened phase. Counters, dispatches, and previous receipts are retained.

A blocked or revise phase preserves its package in full, but the rejected product is not imposed as the live version and is not passed as an accepted dependency. Production may correct it and prepare another gate; consumed attempts remain counted. This also applies to `needs-revision` in a productive phase, which now leaves that same phase open.

During repair, dependent application products (`draft`, `application-draft`, `annexes`, `review`, `repair`, `qa`) may be modified while preserving their snapshots. Products from the earlier design remain binding: changing them requires `invalidate` at the first affected phase. An accepted repair supersedes earlier dependent versions, adds the link to its packet, and requires a new review. The new validator receives only active accepted products as dependencies and frozen baselines as before/after evidence; a new review can therefore reach a different judgment about the corrected text.

## Dispatch and reports

Dispatch verifies the phase and state hash before reserving identities or attempts. A stale package writes neither dispatch nor observation copies and consumes no budget. The observed identity remains distinct from all historical producers and validators.

Each new dispatch copies the observation bytes to `validation/observations/PACKET.json` and binds them to the dispatch with a hash. Historical verification uses this copy; the working original may be moved or deleted. Changes to or deletion of the historical copy are detected. For existing dispatches without a copy, the expected original is verified: missing evidence is not reconstructed.

The report schema also types checks, evidence, discrepancies, limitations, missing information, critique, and automated controls. The stdlib verifier enforces every keyword present in the contract and rejects unsupported keywords. It uses the schema actually frozen among the package files; modifying `report-schema.json`, which remains a service copy, does not weaken the contract.

## Evidence and limitations

Reproducible evidence, the hashed baseline copy, and the adapted replay are excluded audit materials and are not shipped. All applications, spawn observations, and verdicts in the fixtures are synthetic and identified as such. They do not attest to real agent calls or provider isolation. The regression suite checks skips, rewinds, retries with different products, repair/review, historical hashes, paths, schema, and dispatch without improper budget consumption.

These checks assume the single orchestrator specified by the protocol. They do not provide a global filesystem transaction: a crash or I/O error after a write begins may leave an incomplete local artifact that needs examination. They do not protect against hostile concurrent path replacement between check and use, nor do they certify the authenticity of claims stored in JSON files. No tests have been conducted on a new host or on a real application.
