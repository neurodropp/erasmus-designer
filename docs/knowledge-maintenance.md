# Executable annual maintenance

The [erasmus-knowledge-maintenance](../skills/erasmus-knowledge-maintenance/SKILL.md) skill coordinates collection, comparison, integration and promotion. `knowledge_maintenance.py` performs the deterministic staging work; it does not modify active sources, routing, answers or memory. It is neither a universal form extractor nor an authenticated browser. Python uses only the standard library and the existing `form_profile.py` validator.

## Identity and folders

The identity of each asset contains `program` (ERASMUS/ESC), `year`, `kind`, `action`, `sector`, `round`, `language`, `agency`, `jurisdiction` (NA/EACEA/general). For a general guide, use explicit ALL values for action/sector/round; for a form, use the verified route, without assigning KA220 or ESC30 as a default. An expert guide requires NA or EACEA and `scope_note`: coverage is not assumed for all actions in the same jurisdiction. The profile may also retain the official form code separately from the engine code, for example ESC30-SOL distinct from route ESC30.

Metadata includes `scope_note`, `data_classification` (public/project-private) and, optionally, URL, version, dates and identity evidence. `identity_verified` records a statement that the asset was observed, not a reviewer's outcome. Capture measures the remote bytes and leaves identity_verified=false. `status=active` is rejected.

Common staging belongs under `audits/<batch>/` or `maintenance-candidates/<batch>/`; private staging belongs under `projects/<ID>/inbox/` in an already created case file or in an authorized external folder. Symlinks, `.lwc/`, and destinations in active catalogs, scripts, raw and sources are prohibited. On macOS, resolve system aliases for the temporary folder before passing it as the workspace.

Each revision has the relative path:

```text
revisions/<hash-identità>/<hash-originale>/<hash-manifest>/
  payload.pdf|html|json|docx|txt|md
  metadata.json
  evidence/0001.<estensione>
  manifest.json
```

The manifest binds identity, originals, evidence, sizes, SHA256 and validator results/fingerprints. The same bytes and metadata are idempotent; new metadata/evidence or a new validator produce another revision, even with the same original. `check` detects modified bytes/manifests, extra artifacts, paths that escape the workspace, and profile mismatches. The observed manifest hash must be included in the frozen package and passed to `--expected-manifest`: hashes and content addressing are not a signature or regulatory evidence. A validator change preserves the historical integrity check, shows the current result separately and sets new_snapshot_required; `--strict` requires the new snapshot without rewriting the previous one.

## Commands

Run from the engine root. Choose a real batch name; the names below are a repeatable example, not an active call. Global options precede the subcommand. All CLI destinations `--out`, `--revision`, `--baseline`, `--candidate`, `--destination` are **relative to the workspace**, including in exports.

```bash
python3 scripts/knowledge_maintenance.py --workspace audits/annual-check inventory --out reports/inventory.json
python3 scripts/knowledge_maintenance.py --workspace audits/annual-check capture --url https://erasmus-plus.ec.europa.eu/erasmus-programme-guide --metadata audits/annual-check/page-metadata.json --out reports/capture.json
python3 scripts/knowledge_maintenance.py --workspace audits/annual-check discover --revision revisions/IDENTITY_SHA/PAYLOAD_SHA/MANIFEST_SHA --out reports/discovery.json
python3 scripts/knowledge_maintenance.py --workspace audits/annual-check stage --file INPUT.json --metadata METADATA.json --evidence COUNTER_PROOF.html --out reports/stage.json
python3 scripts/knowledge_maintenance.py --workspace audits/annual-check check --revision revisions/IDENTITY_SHA/PAYLOAD_SHA/MANIFEST_SHA --expected-manifest MANIFEST_SHA --strict
python3 scripts/knowledge_maintenance.py --workspace audits/annual-check diff --baseline revisions/OLD_ID/OLD_BYTES/OLD_MANIFEST --candidate revisions/NEW_ID/NEW_BYTES/NEW_MANIFEST --fail-on-blockers --out reports/form-diff.json
python3 scripts/knowledge_maintenance.py --workspace audits/annual-check report --out reports/review-input.json
python3 scripts/knowledge_maintenance.py --workspace audits/annual-check export --revision revisions/IDENTITY_SHA/PAYLOAD_SHA/MANIFEST_SHA --destination exports/candidate.tar.gz
```

Create `page-metadata.json` for capturing the program2026 access point, for example:

```json
{
  "program": "ERASMUS", "year": 2026, "kind": "official-page",
  "action": "ALL", "sector": "ALL", "round": "ALL", "language": "en",
  "agency": "European Commission", "jurisdiction": "general",
  "scope_note": "Guide access point: verify version and linked documents; it does not attest to every route.",
  "data_classification": "public", "identity_verified": false
}
```

`capture` performs a public GET without cookies/credentials; it verifies HTTPS host and redirects before following them, with limit8MiB, timeout20s and content type checks. No new authentication is supported. Do not use it for private sessions; use the provided export or read the authorized session with the appropriate tools. The allowlist may be extended only after verifying the authority of the new host. `discover` treats links/years as **hints**, does not follow documents, does not conclude that a new annual edition has been published, and flags incomplete discovery: dynamic libraries, filters and pagination require additional reading. Download a complete PDF only when needed for analysis, avoiding duplicates when verified originals already available are sufficient.

`stage` preserves the original file and evidence; a partial profile can still be acquired with outcome false. `check` without strict checks integrity and shows readiness; `--strict` returns code1 for missing/incomplete/invalid profiles. Identity or integrity errors always return code1. `diff --fail-on-blockers` returns1 for unresolved/reduced limits, ambiguous matching or changed coverage, while preserving the report. Existing artifacts and reports are not overwritten with different bytes: use a new name/version.

`export` preserves all verified bytes with relative operational paths in the archive; it rejects a private revision and an existing destination. Any historical paths present **inside** originals are not converted: they remain provenance, not addresses to execute. The review package must also retain the content-addressed directory or a receipt with the manifest/original hash; the archive alone is not a review attestation.

## Schemas and form comparison

The profile remains the one consumed by `form_profile.validate_profile`, `application.py` and bind-form. Preserve exact texts, kind, required, repeatability, occurrence_ids/occurrences, contexts, limits, evidence, conditional/help/options/tables/uploads, rich fields and award mappings. The comparison traverses **every** JSON key; it has no closed list of only known fields. Lists preserve order and complete content; the report also shows question_order_changes. Per-instance IDs/limits and rich payloads are not merged or omitted.

For a genuinely stable namespace, add `stable_id_namespace` and `stable_id_evidence` with evidence from the platform registry or a verified crosswalk. User template local IDs, generated during extraction or from labels, do not have this property. Without evidence, even identical IDs remain ambiguous proposals, with added/removed: they are not accepted matches. A different label with a verified official ID produces changed and requires a new review; automatic transfer of answers is prohibited.

A namespace change can be compared with `--id-map FILE.json`:

```json
[
  {"from": "OLD_CONTROL_ID", "to": "NEW_CONTROL_ID", "evidence": "Observed export p.7 and screenshot of section/WP/condition: identity verified"}
]
```

The map must be one-to-one, with existing IDs and localized evidence; the tool rejects conflicts and duplicates. The reviewer checks that the evidence exists and demonstrates identity: the `evidence` text alone is not a certification. Do not build crosswalks from fuzzy similarity or from C001… indexes/reading order.

For narrative fields, the limit must be positive and sourced. If occurrences have different limits, preserve each limit and context; an explicit null value does not borrow the general limit. A general limit may be absent only when every applicable occurrence has a verifiable limit. The tool does not invent maximums, shorten text or modify answers. Readiness for an unchanged comparison indicates technical compatibility only, never current_call_verified or authorization to reuse without review.

The user template KA220-YOU2025 contains98questions/346occurrences and partial limits. Tests compare the actual registry in a fixture without declaring it a form2026. For an actual form, the `form_instance.applicable_fields` matrix belongs to the individual application, including its actual instances; a shared schema does not replace this matrix.

## Integration, review and promotion

The tool has no publish command. The coordinator completes promotion through the existing process when the review is accepted; they do not stop at a report if the requested and authorized update can be completed.

The frozen package must include the accepted baseline and all hashes, a complete analysis of applicable conditions/criteria and conflicts, field diff, crosswalk, originals/evidence, candidate catalogs/routing/checklist/playbook, list of code changes and tests, versions/runtime, impact on case files and rollback plan. For expert guides, distinguish NA/EACEA scope and the actions actually covered: ESC2026 experts does not imply coverage of ESC51/VTHPA/humanitarian; Erasmus NA does not imply EACEA. The technical validator does not check regulatory meaning or completeness of all sources.

Build the candidate release in an isolated checkout/copy coordinated with the owners. Keep originals in separate revisions and plan an explicit annual catalog. Today `brain.py` and `workflow.py` have 2026 guards and page tags/extractions that depend on ID/version; `runtime_support` verifies these contracts and the catalog, then still reports active=false. For2027, extend source selection, routing and pagination, extraction, dossier/search/cards, action modes, workflow, form identity, checklist, stage gates and relevant recovery tests. Refactoring the guards also requires a verified maintenance adapter. Changing `config/sources.json` or `knowledge-maintenance.json` alone does not make a year supported. Tests must prove distinction between annual editions and rejection of silent fallback.

In the candidate engine:

```bash
python3 scripts/brain.py rebuild --no-cards
python3 scripts/brain.py check
python3 -m unittest discover -s tests -p 'test_knowledge_maintenance.py' -v
python3 -m unittest discover -s tests -p 'test_application.py' -v
python3 -m unittest discover -s tests -p 'test_workflow.py' -v
```

Complete the checks/retrieval and release checks required by the actual changes; these examples do not replace the relevant suite. Do not run a rebuild in the live corpus during discovery. Summaries from richer memory are updated by agents with sources, never regenerated through blind bootstrap.

A new reviewer `fork_turns="none"` reads erasmus-stage-validator and the package with hashes. Engine maintenance is not an application: do not create a false KA220 case file to obtain a gate. For existing applications use the `stage_gate.py`/fresh-step-v1 contracts and `workflow record`; for an engine gate, retain observed dispatch/session and report according to the applicable release protocol, declaring the contract. No attestation of isolation, identity, signature or accept is simulated. Every new material change requires a new package and a fresh reviewer; repair preserves baseline/before-and-after evidence.

Publish memory with the installed CLI, after rereading `--help` if the runtime has changed. Example using NAME chosen for the actual update:

```bash
scripts/lwc checkpoint create before-NAME
scripts/lwc changeset begin NAME
scripts/lwc --changeset NAME source add PATH_TO_VERIFIED_UTF8_EXTRACTION --title "Title/version/scope"
scripts/lwc --changeset NAME ingest next --source-max-chars 100000
scripts/lwc --changeset NAME ingest analyze REAL_SOURCE_ID --file VERIFIED_ANALYSIS.md
scripts/lwc --changeset NAME page put SLUG --title "Title" --kind concept --file VERIFIED_PAGE.md --source REAL_SOURCE_ID
scripts/lwc --changeset NAME ingest complete REAL_SOURCE_ID
scripts/lwc --changeset NAME lint
scripts/lwc --changeset NAME search "Specific retrieval question for call/action"
scripts/lwc changeset show NAME
scripts/lwc changeset commit NAME
scripts/lwc lint
scripts/lwc search "Specific retrieval question for call/action"
```

`source add` accepts UTF8; for PDF, use the verified extraction with a manifest originating from the original, not an invented conversion. Source ID is the one actually returned; update the local/LWC map without replacing old citations. Prepare the necessary source pages and concepts with all relevant sources. Preserve checkpoint, CLI receipts, page/citation diffs and retrieval before/after. **Source add is collection**; ingest and evidence-based synthesis complete integration. A reproducible integrity issue in the draft follows the recovery defined in this document: discard, named checkpoint, explicit live CLI update of only the manifested items, comparison of unaffected items, lint/retrieval. Do not use recovery automatically or describe it as atomic.

Selected case files receive the original/provenance in inbox and the profile in application with independent checking. Use the actual report required by workflow:

```bash
python3 scripts/workflow.py invalidate ID --phase FIRST_AFFECTED_PRODUCTION_PHASE --report projects/ID/reports/source-invalidation.json
python3 scripts/workflow.py bind-form ID --profile projects/ID/application/form-profile.json --report projects/ID/reports/form-binding.json
```

Invalidation concerns the first phase genuinely dependent on the change: new regulations may affect eligibility/idea-validation/design before answer-outlines. In the integrated process, bind-form reopens answer-outlines; in compact, it reopens draft, according to current state. The report contains local evidence and the critical_review required by the process. Preserve attempt history/budget and superseded receipts; do not bypass a gate by invalidating a future phase. A new annual edition does not automatically change the year of existing case files.

Before commit, `changeset discard NAME` abandons the draft. Afterward, `changeset rollback EXACT_RETURNED_ID` is permitted by the CLI only if there have been no subsequent live writes; otherwise plan and verify `checkpoint restore`. Also restore version/catalogs/routing/form to the accepted baseline hash, retaining the candidate and receipts, then invalidate/verify affected dependencies. Rollback does not delete evidence or make results from the replaced call valid.

## Verified access points and verification limits

Consulted on13September2026:

- [Erasmus Programme Guide](https://erasmus-plus.ec.europa.eu/erasmus-programme-guide): current2026 card, version1 dated12.11.2025; [document library](https://erasmus-plus.ec.europa.eu/resources-and-tools/documents-and-guidelines) also requires filters/pagination. Primary search finds the [2026 expert guide on a Dutch NA mirror](https://www.erasmusplus.nl/sites/default/files/2026-01/IV.1a%20-%20E%2B%20Guide%20for%20experts%20on%20quality%20assessment%202026_v1.pdf), explicitly NA; the existing catalog retains its own verified mirror and hash, without assuming remote bytes are identical.
- [ESC calls](https://youth.europa.eu/solidarity/organisations/calls-for-proposals_en) and [resources](https://youth.europa.eu/solidarity/organisations/reference-documents-resources_en): access to the 2026 guides, experts and sample ESC50/51/30; EACEA has its own calls/forms. The English program guide card reports13.11.2025; other languages may report other dates: distinguish language/revision, do not infer year from the timestamp.
- [ESC30-SOL sample2026 Round1](https://youth.europa.eu/sites/default/files/inline-files/Call-2026-Solidarity-projects-ESC30-SOL_watermark.pdf),13pages: header20Feb2026 while the call page gives18Feb2026 for Solidarity Projects. This is a **conflict to preserve**, not a deadline to transfer to the application. The export does not prove counters or all conditional branches.
- [How to apply Erasmus+](https://erasmus-plus.ec.europa.eu/resources-and-tools/how-to-apply): NA/EACEA routing; [public form-filling manual](https://wikis.ec.europa.eu/pages/viewpage.action?pageId=139690553) remains an access point to verify, not a current normative schema.
- [AIG KA220 Youth priorities2026](https://agenziagioventu.gov.it/priorita-europee-nel-contesto-nazionale-rilevanti-nel-processo-di-valutazione-dei-partenariati-di-cooperazione-ka220/) and [Italian application portal](https://www.erasmusplus.it/programma/come-fare-domanda/): verified hosts/access points for acquiring Italian provisions and priorities. INDIRE SCH/ADU/HED, INAPP VET and AIG YOU/ESC remain distinct records/scopes in the catalog; do not transfer a national priority between sectors or programs.

This implementation does not update the live corpus or memory, download new complete guides or claim support for2027. Real capture limited to public HTML and testing the actual form registry in a fixture document what has actually been proven; promotion/fresh review remain operations to complete with the coordinator under the actual mandate.

## Maintenance of award checklists and methodological adapters

The field inventory also includes `config/award-criteria/*-2026.json`, selectors/roles and subpoints, `scripts/award_criteria.py`, the `checklist.award_coverage` integration and deliveries in `wiki/checklists/award-criteria/`. For a new annual edition, compare all rubrics, variants, maxima/thresholds and complete sections; explicitly update the catalog, resolver, year guards and tests before activation. Do not only change filenames or the year of PDFs. Outcomes for each application remain in checklists and historical receipts; an update requires relevant adoption and invalidation, without attributing new consent.

The source option `html_content_scope: full-static-document` is an explicit adapter for methodological pages without a semantic main/article. Do not apply it in bulk to existing sources: check prose, tables and capture limits, as well as hashes. If an old extraction is incomplete, preserve the revision and add a new extraction/snapshot with provenance, without rewriting an immutable source already cited. Unobserved Impacttool editorial year/version remains unknown; an acquisition batch and a new extraction version do not prove a remote revision.

`knowledge_maintenance.py inventory` also includes `methodology_assets`: award catalogs, guides, contract and checker with observed hash. This list identifies dependencies to review; it does not certify merit, online freshness or a new annual edition.
