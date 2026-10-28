# Local Evidence Repairs 0.2.1

Corrections ED-06, ED-20, ED-21, and ED-22 from the audit have been implemented. This verification covers evidence integrity and routing; it does not certify regulatory analysis for all 50 routes.

## Original → derived → index integrity

Previously, a change from `20%` to `99%` in a Markdown page could be returned with the digest of the original PDF. The check verified the document without checking the bytes of the extracted evidence or the FTS index.

The `derived-evidence-v2` schema stores separately the digest of the original document, the UTF-8 digest of each page, the paths to the current copy and revision, the digest of the full text, and a page manifest. The index stores the digest of the body actually indexed and the signature of the current catalog. `show`, `search`, and `dossier` run a full check before returning content: originals, pages in both copies, full texts, manifests, metadata, docs/FTS cardinality, and indexed bodies. A deleted or altered FTS row is an error rather than a false search result.

Migration does not simply calculate a digest for the old Markdown. `rebuild --no-cards` rereads the original PDF/HTML/text, verifies its registered digest, and regenerates the derived content. For texts imported from templates, it also verifies the user original when the catalog retains its path and digest. Earlier metadata and indexes without these digests are rejected until this rebuild is run. An original that differs from the catalog is rejected; consciously updating its version and registry requires a source review.

Consumers that freeze files directly use the stdlib API `brain.integrity_for_root(CATALOG_ROOT, include_cards=False)`: it returns the list of errors without writing a report or changing shared module variables. A non-empty list must be rejected before any snapshot or package write. The coordinator incorporates this check into the gate; package tests that artificially replace `route_evidence` remain tests of the synthetic contract, not of the authentic corpus.

Digests are local checks for alteration and staleness, not cryptographic signatures from an authority. The verified catalog and originals are the basis for reconstruction. Derived copies can be restored from the original; this does not authorize rewriting already frozen packages or receipts. An actual change to bytes used by an application requires reopening the first affected phase. The `repaired_from_verified_original` data records restored pages that differed; the corpus index does not replace application receipts.

Migration and verification commands, to run after editorial updates have been integrated:

```text
python3 scripts/brain.py rebuild --no-cards
python3 scripts/brain.py check
python3 -m unittest discover -s tests -p test_knowledge_integrity.py -v
```

## Route dependencies

The Erasmus catalog now declares Part A, Part C, and physical glossary pages 443–456 for each route. KA210/KA220 partnerships include common and sectoral priorities 227–234. KA150–KA155 Youth mobility routes include the introduction on p.143 and all Youth Standards; KA120/121/122 SCH/ADU/VET include the standards for their respective mobility actions. Action families have explicit contextual cross-references where relevant.

Routes with a relevant national grid include the expert principles on pp.9–14. National KA210/KA220 partnerships and KA240 include cost-effectiveness on pp.70–71 and the 2026 lump sum handbook. KA2 Sport and other EACEA actions do not receive the national grid or handbook as applicable dependencies. ESC retains its own sources and dependencies; it does not receive Erasmus priorities or criteria.

Each dossier dependency returns `source`, page range, revision files, original digest, page-ID digests, full-text path/digest, URL, and an indication of local consistency. Dependency classification and notes define the document's role: a glossary is not a criterion, and a handbook does not mandate every budget table. Reading the full sector-specific pages remains necessary.

Physical page 149 contains both the conclusion of KA150 accreditation and the start of KA151 allocation. It is now included in both routes; queries and the dossier retain ID `programme-2026:p0149`. The sample of other checked boundaries includes 72/73, 164/165, and 179/180; family introductions 143, 224–226, 258, 289, 364–365, and 375 are distinct contextual dependencies. No comprehensive review of every boundary paragraph is claimed.

## Expert guide links

The `discovery_url` field identifies the HTML library. `document_url` identifies the [2026 v1 expert PDF on the official mirror of the Greek National Agency](https://erasmusplusyouth.gr/wp-content/uploads/2026/01/IV.1a-EPlus-Guide-for-experts-on-quality-assessment-2026_v1.pdf), opened and verified as a PDF, version, and 85 pages. This verification does not claim that the remote bytes have the same digest as the local PDF. Local digests remain those of the authentic attachment.

`sync_lwc.evidence_links` adds `#page=N` only to a URL whose path is a PDF. If only a discovery URL exists, it preserves the LWC source page and the local PDF locator without inventing a fragment in the HTML library. This fix is a transformer; it does not automatically republish curated memory. Selective canonical card updates and their lint/retrieval checks are the coordinator's responsibility after integration.

Dependency references are also confirmed by primary sources: [2026 Partnerships for Cooperation priorities](https://erasmus-plus.ec.europa.eu/programme-guide/part-b/key-action-2/partnerships-cooperation), [Cooperation Partnerships rules and reference to the National Agency handbook](https://erasmus-plus.ec.europa.eu/programme-guide/part-b/key-action-2/cooperation-partnerships), [Youth Standards](https://erasmus-plus.ec.europa.eu/sites/default/files/2021-10/erasmus-youth-quality-standards_en.pdf). These targeted checks do not silently update the entire corpus or the current form.

## Tests and delivery limitation

Tests generate a real PDF with Poppler and run in temporary directories. They verify a positive baseline, numeric alteration, byte restoration, regeneration from the original, explicit migration, altered full text, altered or missing bodies/FTS rows, stale catalog, program replacement, and manifest ambiguity. The full corpus was rebuilt from 97 originals in a temporary copy: 929 evidence items, 50 routes, zero errors. No live derived content, canonical LWC database, or bootstrap was modified by this specialist.

Observed test evidence and commands are in `audits/repairs-0.2.1/knowledge/`. A fresh independent verification of the integration is still required before declaring the repair phase complete.

Excluded private audit evidence is not shipped.
