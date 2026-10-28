# Protected LWC bootstrap

`sync_lwc.py` is a deterministic bootstrap for editorial inputs that have already been reviewed. Maintaining a richer wiki requires agents, evidence and the [knowledge maintenance](knowledge-maintenance.md) process. The old command without a manifest is rejected. This repair did not recompile or promote the real corpus.

The `stage` command does not write the active map, commit, or automatically discard a failed changeset. A failure leaves only the candidate artifacts and the draft to be explicitly inspected/discarded. `publish-map` is instead an explicit publication command: it commits the changeset and atomically replaces `index/lwc-source-map.json` only after confirming the receipt and comparing IDs/content of the **live** sources, in addition to the expected pages. Before committing, it verifies the candidate hash, draft identity, baseline map, sources, pages and lint. The actual receipt and the previous map bytes remain in the candidate workspace; the previous history is not rewritten.

## Required manifest

Prepare a `bootstrap-support-manifest-v1` manifest under `audits/<batch>/` or `maintenance-candidates/<batch>/`. There is no automatic support generator or preapproved production manifest. The reviewer examines the applicability and completeness of the evidence; hashes certify neither merit nor approval.

```json
{
  "schema_version": "bootstrap-support-manifest-v1",
  "config_sha256": {
    "sources.json": "SHA256 of config bytes",
    "actions.json": "SHA256 of config bytes",
    "wiki-purpose.md": "SHA256 of config bytes",
    "wiki-schema.md": "SHA256 of config bytes"
  },
  "sources": {
    "ID-CATALOGO": {
      "sha256": "SHA256 sources/ID-CATALOGO/full.md",
      "metadata_sha256": "SHA256 sources/ID-CATALOGO/metadata.json",
      "data_classification": "public"
    }
  },
  "pages": {
    "SLUG": {
      "path": "wiki/PATH/SLUG.md",
      "sha256": "SHA256 of original editorial bytes",
      "sources": ["ID-CATALOGO", "ALTRO-SUPPORTO-ESATTO"],
      "data_classification": "public"
    }
  }
}
```

Every catalog source and every compilable editorial page must be listed, with no duplicate slugs. `wiki/index.md`, `wiki/log.md` and the legacy `wiki/projects/` folders are excluded. Private sources/pages or those without public classification, symlinks, protected paths and mismatched hashes are rejected. The `public` declaration is the manifest's responsibility: the tool does not automatically recognize personal data hidden in a file declared public. Do not use private application templates in the shared corpus.

The manifest contains **all** page-specific supports, including templates, national provisions, methodological evidence and relevant shared sources. The compiler also checks explicit Markdown/source locator references and rejects missing or unknown supports. Action pages require `programme_source` and, where applicable, the declared route/programming's `expert_source`: ESC30 retains ESC guides; it does not receive the Erasmus fallback. The current KA220 playbook still requires `programme-2026`, `expert-2026`, `template-ka220-user`; a future playbook requires a dedicated contract, not a silent change of year.

## Protection of maintained memory

Before every mutation, the tool compares draft/live pages and the live map with the exact contents of the manifested sources. An existing editorial page whose content or set of supports differs from the reviewed input blocks the bootstrap: update it through agentic maintenance. An identical page is **skipped**, preserving its existing metadata, provenance, links, title, summary and history. Source maps and live pages outside the target remain untouched. The candidate retains hashes of draft/live records; it does not copy their text into a new index or the manifest. No generic branch selects two guides to replace richer citations. A historical ID not manifested in the active map blocks the bootstrap instead of being deleted.

This is a guard against blind recompilation; it is not a complete regulatory analysis of the supports. The contents of a new source map are declared deterministic. Compilation does not attest that the guide is up to date online and does not replace `brain.py check`, the regulatory matrix, specific retrieval and independent review.

## Commands and recovery

Only in an authorized candidate workspace, after integrity checks of originals/projections and review of the manifest:

```sh
scripts/lwc changeset begin NAME
python3 scripts/sync_lwc.py stage --changeset NAME --manifest audits/BATCH/supports.json --out audits/BATCH/candidate
```

Examine artifacts, lint and retrieval. After the independent gate required by the process, the following command **performs a real LWC commit** and promotes the derived map against the live identities:

```sh
python3 scripts/sync_lwc.py publish-map --candidate audits/BATCH/candidate/candidate.json --expected-candidate-sha256 REVIEWED_SHA256
```

The command does not itself implement a new candidacy gate or interpret an invented `accept`. The real CLI must retain the documented `changeset show/commit`, `source show`, `page list/show`, ingest and lint interface. Isolated tests use an observable fake CLI; no write compatibility with a future runtime is certified.

Failure before commit or discard keeps the active map. Failure after commit may leave the corpus published and the previous map in place: the receipt is preserved, `publish-map` is not retried automatically, and no implicit rollback is performed. Compare hashes, receipt, candidate and live sources; use explicit reconciliation or the rollback provided by the process. LWC commit and filesystem map are not a single transaction. Interruptions or hostile concurrent writes have no global atomicity guarantee; the tool checks for map changes before replacement and rejects an already existing temporary file. Keep the failed draft and artifacts until an explicit decision is made.

Local verification without real LWC:

```sh
python3 -m unittest discover -s tests -p 'test_sync_lwc.py' -v
```
