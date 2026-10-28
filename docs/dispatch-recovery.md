# Writers and dispatch recovery

`project_lock.project_lock(path)` serializes cooperative project writers using an exclusive, nonblocking `flock`, shared by workflow, stage gate, and other writers that adopt it. The lock is reentrant within the same thread/process. The `.workflow.lock` inode remains on disk: the file's presence does not indicate a live writer and it must not be deleted. The kernel releases the lock when the process closes. The CLI acquires the lock before reading and holds it through writing; the prepare/dispatch/verify/recover APIs also check CAS of the supplied state against `state.json`. Budgets and global identity reservations are checked under the same lock. Init serializes creation using the existing engine-root lock; invalid input or layout does not create projects or project folders.

This protection prevents lost updates among cooperative writers; it does not make a multi-file transaction atomic. A crash after creating an archive and before saving state can leave an unindexed artifact: preserve it, compare hashes and state, and document recovery before proceeding. Do not delete observations to regain attempts. Manual or hostile writers that ignore the lock are outside this protection.

An archived dispatch is immutable and consumes an attempt even if it produces no report. Before retrying, the actually observed interruption may be recorded:

```sh
python3 scripts/stage_gate.py dispatch-status ID --packet PACKET
python3 scripts/stage_gate.py recover-dispatch ID --packet PACKET --status interrupted --observation sessions/interrupt.json --reason "Observed reason"
```

`cancelled` uses the same command after the observed interruption action. The local observation requires `tool=collaboration.interrupt_agent`, `request.target` equal to the dispatched ID, and a non-empty observed `result`. Do not execute the interruption inside the CLI or fabricate the receipt; a cancellation request alone is not evidence that the action occurred. Recovery does not promise host authentication: these are records made by the coordinator, not a signature from the tool provider.

Append-only terminal events in `validation/lifecycle/PACKET/` are bound to the dispatch hash and immutable evidence copy; a hash anchor in state.json detects removed or altered terminal events. After interrupted/cancelled, that dispatch's report cannot close a gate. A phase already recorded cannot be cancelled through recovery. Prepare a new packet and call a new fork-none validator within the remaining budget. All previous identities and attempts remain reserved; revision counters do not change. No automatic expiry/watchdog or budget increase is implemented.

For new packets, `deterministic_checks_policy=allowlisted-python-v1` reruns `check_answers` and `check_model` imported from the engine, in strict mode at QA. A declared pass does not override the actual result. Report command strings are data and are never executed. Frozen v1 receipts without the policy remain valid within their declared historical scope, without rewriting them or retroactively attributing executions. Non-allowlisted checks fail explicitly. These checkers do not establish merit, originality, host identity, or routing quality.
