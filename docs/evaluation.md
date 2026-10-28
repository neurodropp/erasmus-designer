# Repeatable skill and evaluator tests

Structural regressions and model judgments are different kinds of evidence. `evaluation.py` imports predictions that were actually produced and compares them with separate labels; it does not invoke a model or turn static checks into a reasoning benchmark. The existence of predictions must be supported by an observed mandate and the producer’s report. Local declarations of blindness to labels do not authenticate the provider.

## Skill selection

`tests/routing_cases.json` contains synthetic requests written from scratch; `tests/routing_labels.json` contains the controller’s expectations. A new tester reads only the requests and the descriptions catalog, makes its own judgment, then reads the body and references of the selected skill and records their hashes. It receives no labels, expected answers, or audit conclusions. Out-of-domain requests may be left without a skill; ambiguous requests must identify the alternatives and ask for the necessary information. Micro-delegation also requires a role that is actually available in the host: a task name and a skill name do not create an `agent_type`.

The September 13 test has 24 requests: 18 relevant selections, three out of domain, and three ambiguous. The separate check finds 24/24 agreements with these expectations. This is model-assisted selection from an explicit catalog, not a test of automatic discovery or the host’s implicit routing. The tester identified a residual overlap in the annex-budget body; the coordinator corrected it after the test. The report hashes refer to the version actually read; they are not rewritten to appear current.

## Qualitative critique of the evaluator

`tests/evaluator_cases.json` contains twenty invented excerpts; labels are separate in `tests/evaluator_labels.json`. The tester reads the rules and scope, excluding configuration subtrees that contain expected labels. Without the call’s scoring grid, it produces only `supported` or `needs-evidence`, a localized reason, a correction, a null score, indeterminate compliance, and no prediction. Synthetic flags do not replace the text: contradictions must be reported.

The observed test distinguishes ten supported excerpts and ten insufficient excerpts at the sample’s abstract level. The fixtures’ historical vocabulary uses `insufficient`, while the mandate uses `needs-evidence`: the import explicitly normalizes these two equivalent labels. The first literal comparison, 10/20, remains preserved in the `evaluator-vocabulary-before.json` report; the normalized comparison is 20/20. No tester prediction or label was changed. This simple sample does not measure capability on entire applications, agreement with the agency, causal improvement, or out-of-sample performance. The configuration’s eight guards remain static checks, not eight additional observed model judgments.

## Repeat and expand

Create a new tester with no history and exclusive outputs for each run. Preserve inputs/versions, the effective mandate, observed identity, files actually read, predictions, errors, and actually measured timings. Then run:

```sh
python3 scripts/evaluation.py routing --labels tests/routing_labels.json --predictions PREDICTIONS --output RESULT
python3 scripts/evaluation.py evaluator --labels tests/evaluator_labels.json --predictions IMPORT_ENVELOPE --output RESULT
python3 scripts/verify_retrieval.py --output RESULT_RETRIEVAL
```

The evaluator envelope links the original `predictions.json` with its hash and `cases` list, plus the observed declaration `labels_read=false`; preserve the tester’s original. Grading checks exact coverage, localized reasons, and the prohibition on unsubstantiated scoring/consent/funding claims. It does not use private training, applications, or assessment APIs.

The current retrieval set contains ten question/paraphrase pairs, with required supporting evidence, prohibited supporting evidence, and scope text for ESC, roles, year, Sport, and template limitations. This is a fixed lexical regression: it checks ranking, sources, and the presence of caveats, not comprehension or complete application of all rules. The actual call matrix remains necessary.

Demonstrating superior performance requires new cases not used in development, real tasks synthesized without private data, observed implicit-routing errors on the host, comparison with a baseline, and measured costs/tokens. Without this evidence, RUNTIME-005 remains partially open. Calibration against agency judgments requires initially concordant pairs matched by name, code, and phase; do not substitute final reports. See [calibration and privacy](evaluator-calibration.md).

The final catalog regression was assigned to another new agent with no history, using the current compact catalog: 24/24 agreements. The current 1.1.0 calibration regression reused the producing agent on twenty cases it had already seen, recording new hashes at read time: 20/20 normalized agreements. This is neither a new holdout nor the independent gate. Earlier versions and the initial vocabulary error remain preserved. The final manifest check finds 49 public files read with hashes matching the current bytes.
