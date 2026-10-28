# Human decision on the exact bundle

`ready-for-human-review` is a handoff for review. `human-approved` records a user decision observed by the coordinator on the current QA accepted bundle. It does not authenticate the user's identity through a provider, sign documents, or authorize submission, upload, or contracts: the engine contains no submission runner.

The `human-review-bundle-v1` bundle contains the ID and route of the single dossier, the hashes of the active accepted QA package/report/dispatch, the exact manifest of model, application, evidence, annex-manifest, and attachment bytes present in that manifest, the profile, and the physical original of the form. `answers.json.form_instance.form_source` must have a `path` confined to the dossier and the `sha256` of the acquired original. `stage_gate prepare` freezes that file as `form-source`. The full identity of `form_instance` also receives a canonical hash. An earlier QA without that original may remain historical; approval requires integrating the form by reopening the first affected phase and performing new QA.

Commands from the engine root, using a real ID only for the actual decision:

```sh
python3 scripts/workflow.py approval-bundle ID
python3 scripts/workflow.py approval-status ID
python3 scripts/workflow.py approve ID --decision inbox/decision.json
python3 scripts/workflow.py reject ID --decision inbox/decision.json
```

The `observed-human-decision-v1` input requires `decision` to match the command (`approve` or `reject`), `project_id`, `bundle_sha256`, `artifacts` copied exactly from the bundle, `scope=approve-exact-bundle-for-handoff`, `rights=["handoff"]`, the declared `author`, and `provenance={type:"user-instruction",reference,observed_by}`. `evidence` requires a `path` to a separate local proof, `sha256`, `locator`, an exact `quote` present in the proof, `provenance="user-instruction"`, and `quote_authorized=true`. The coordinator retains a minimal, relevant quotation that was actually authorized, without fabricating consent or transcripts. Do not use the decision input itself as proof. An agent's statement does not replace the user's instruction.

The CLI verifies confinement, hashes, fields, quotes, and scope; it cannot distinguish a wholly fabricated local export from one that was genuinely observed. `verification_limit` makes this boundary explicit: provenance must be observed in the runtime, but an authenticated host exporter is absent. Do not create session UUIDs or provider attestations to bridge this limitation.

The decision and proof copy are created exclusively in `approval/`; the hash and index are recorded in `state.json`. A second decision supersedes the first in the index without rewriting archives. Invalidations, bind-form, and subsequent registrations supersede consent. `approval-status` computes `stale` when a bound byte changes; `workflow status` records the detected supersession. Modified accepted products continue to require invalidate. Additional files outside the manifest are not approved and do not expand rights. Changes to the decision or proof copy are detected.

New receipts are local integrity checks, not tamper-resistant signatures. An author with full access who coherently rewrites the data and hashes remains outside the authentication model. No approval of a real application was generated for the repair tests.
