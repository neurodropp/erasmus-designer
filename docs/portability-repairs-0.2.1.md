# Boundary and Transfer Repairs

Baseline: ED-02, ED-03, ED-18, and ED-19 from a private audit dated September 12, 2026. The initial reports remain unchanged. Acceptance requires the independent report referenced in the repair handoff. The private audit and its underlying evidence are excluded and are not shipped.

`scripts/lwc` sets and exports `LWC_PROJECT_ROOT` to the canonical engine root, even when the caller inherits a different value. Changing only the working directory did not prevent LWC from finding an ancestor database. The isolated test checks the environment, directory, and arguments without using live memory; a test with the real binary verifies selection in a nested structure.

Before reading or writing, the installer verifies every component of the `.codex/` and `.codex/agents/` destinations, the individual files, and `.agents/`. It rejects symlinks, including dangling ones, and special files. It preserves the sole `.agents/skills` symlink if it points exactly to the project's skills. Conflicts and customizations remain preserved; the concurrency repair is limited to the exact old generated content. Preflight prevents partial writes caused by predictable errors; it does not promise filesystem transactions or protection against simultaneous hostile replacements.

The export includes `index/source-reconciliation/` with an allowlist: `source-map.SHA256.json` and `reconciliation.SHA256.json`. Unrecognized names, nested directories, and symlinks are rejected. Backups and receipts remain unchanged, along with the current map; other `index/` subtrees are excluded.

Reconciliation continues to verify hashes, sizes, and uniqueness through the official CLI. An intermediate map can be re-associated with new IDs if receipts/backups link it to the originals. IDs may repeat after imports: choose a verified path to the origin in the history graph; a cycle without that path is insufficient. Verify all receipts/backups present and recheck the chosen path before replacement. The current map must match a verified result: an isolated prepared receipt that is not tied to the effective map is insufficient.

The first independent recheck reproduced an ED-19 residual: A→B→C→B→D failed because map B had two valid predecessors. The graph correction resolves this case. New v2 receipts use the digest of the entire file in the name, distinguishing different destinations even when they have the same numeric transition. The v1 receipts remain readable and unchanged. Tests cover ID reuse and transition repetition after copying the root; the patch recheck uses a new validator.

Historical roots are provenance and are not rewritten. Local verification is neither an external signature nor proof of authenticity against an adversary who replaces all evidence. Only the current map is replaced atomically, after evidence has been persisted; coordination requires a single cooperative writer, without a global lock.

## Evidence

`test_installer.py` covers symbolic directories/files and dangling discovery, rejection without external files, customizations, and idempotence. `test_lwc_root.py` verifies environment override and caller directory. `test_reconcile_lwc_sources.py` covers A→B→C→D with unchanged contents, preserved evidence, and rejection of alterations. `test_release_bundle.py` verifies roundtrip and rejection of out-of-scope paths.

Checks were run on the same host. A clean npm install, another OS/computer, actual discovery on another Codex host, and resumption of a transferred candidacy require specific testing; the repairs do not imply these have been validated.
