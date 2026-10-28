# Portable Paths, Version 0.2.2

This release makes reusable instructions portable and editorial links independent of the source computer. The [convention](path-conventions.md) distinguishes the shared engine, the application dossier, and the base used for Markdown links. The verified 0.2.1 releases remain unchanged.

## Implemented changes

- The installer generates engine-relative instructions, specifies the path base, and preserves role constraints. `--relocate-owned-paths` migrates recognized references and resolves the MCP command and directory for the actual installation location; preflight checks and symlink rejection remain enabled.
- 347 link targets have been converted across five wiki pages. The playbook generator will produce the same relative references going forward. The 98 schemas, 346 occurrences, and KA220 Youth template profile remain unchanged.
- In canonical memory, only 51 remaining targets across two pages have been converted. The observed base is `.lwc/wiki/synthesis/`: links to originals use `../../../raw/...`, distinct from `../../raw/...` in editorial files. The other 162 pages, 97 sources, all 329 citations, and provenance have been preserved; lint passes cleanly.
- The orchestrator instructions and replication guide explain how to resolve paths without depending on the current working directory (CWD). Provenance paths and historical receipts are preserved.

## Verification results

All 253 integrated tests passed. The installer's 14 tests cover relocation between directories whose names contain spaces, launching from the internal dossier, migration and idempotency, preservation of customizations, and rejection of conflicts before writing. A private replay of the 27 native definitions verifies the conversion plan; the private audit evidence is excluded from this release and is not shipped. The 347 editorial links resolve in a relocated fixture; the integrity check for the 97 sources and the index passes after `rebuild --no-cards`. These are local checks; no installation on another computer or fresh Codex discovery was performed.

The record from the new independent review remains outside the already frozen ZIP archive. The package generates native configuration surfaces in the destination root; it does not include personal configurations from the source computer.

## Live activation still required

The 27 native definitions and MCP configuration currently active in the source computer's `.codex` have not been modified. Automated authorization review rejected the action, although it recognized that it was authorized and reversible, because this surface is protected as read-only in the current environment. The exact plan and diffs are retained in the local intervention dossier; that private material is not shipped.

To complete activation, authorize and enable writing to that surface, then apply the verified migration and reload Codex. Until that restriction is lifted, do not claim that the live native instructions have been updated. Do not bypass it through indirect writes or another configuration surface.

For a new replication, run the installer from the new root as described in [replication.md](replication.md). Current-call checks, a real application, signatures, materialized attachments, and a new computer remain separate from path verification.
