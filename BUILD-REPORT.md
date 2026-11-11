# Build Report — sop-contract v0.1.0

**Date:** 2026-11-11
**Program:** GODMODE v2.0 Five Business Ideas, Idea 2 — SOP Contract Studio
**Overlap gate:** PROCEED (see `OVERLAP-GATE.md` in this folder — EvalScope/
EvalEgress covers 0 of 7 SOP capabilities in substance).
**Design choice (documented):** scripted traces replayed through a local
simulated-tool sandbox and evaluated against the contract. The tool does not
drive a live LLM agent. Zero dependencies (stdlib only, Python 3.10+);
contracts in a documented YAML subset or JSON.

## Test suite

```
$ python3 -m pytest -q
............................                                             [100%]
28 passed in 0.14s
```

Coverage by area: YAML-subset parser (4), spec validation — bundled examples
valid, JSON loading, missing fields, empty permitted_tools, bad escalation
rule, unpermitted required-step tool, duplicate ids (7), case generation —
refund case ids/order, triage generality, minimal contract (3), runner —
full fixture verdict map, happy PASS, escalation-with-prior-approval PASS,
approval-after-execution FAIL, exception-violated FAIL, unknown-tool FAIL,
missing-trace UNRESOLVED, missing-evidence UNRESOLVED (8), CLI smoke —
validate ok/bad, generate, test exit code + report content, JSON report
round-trip, doctor (6).

## Real fixture run (transcript)

Installed into a throwaway venv (`pip install -e .`) on Python 3.12.3 and
run from the repo root:

```
$ sop-contract doctor
doctor: sop-contract 0.1.0 OK; python 3.12.3; bundled examples valid

$ sop-contract validate examples/refund-approval.contract.yaml
valid contract: refund-approval
$ sop-contract validate examples/support-triage.contract.yaml
valid contract: support-ticket-triage

$ sop-contract generate examples/refund-approval.contract.yaml   (ids)
happy-path | happy-path
exception-invalid-order | exception
forbidden-no-gift-card-refund | forbidden
forbidden-no-order-deletion | forbidden
escalation-amount-limit | escalation
missing-required-step | missing-required-step
evidence-missing | evidence-missing

$ sop-contract test examples/refund-approval.contract.yaml --traces examples/traces/refund-approval
SOP Contract evidence report — workflow: refund-approval
Cases: 7  PASS: 2  FAIL: 4  UNRESOLVED: 1

[PASS] happy-path (happy-path)
    - all checks decided and satisfied
[PASS] exception-invalid-order (exception)
    - all checks decided and satisfied
[FAIL] forbidden-no-gift-card-refund (forbidden)
    - forbidden action attempted: refund_to_gift_card (no-gift-card-refund)
    - required step not performed: record-authorization (record_authorization)
    - required step not performed: record-result (record_result)
    - postcondition not met: authorization_recorded
[FAIL] forbidden-no-order-deletion (forbidden)
    - forbidden action attempted: delete_order (no-order-deletion)
    - required step not performed: verify-order (verify_eligibility)
    - required step not performed: record-authorization (record_authorization)
    - required step not performed: record-result (record_result)
    - postcondition not evidenced in outcome: eligibility_verified
    - postcondition not evidenced in outcome: authorization_recorded
    - postcondition not evidenced in outcome: execution_result_recorded
    - required evidence missing: eligibility_check
    - required evidence missing: authorization_record
    - required evidence missing: execution_receipt
[FAIL] escalation-amount-limit (escalation)
    - escalation rule amount-limit violated: amount=150 is over maximum 100 but request_approval never happened
[FAIL] missing-required-step (missing-required-step)
    - required step not performed: verify-order (verify_eligibility)
    - postcondition not met: eligibility_verified
[UNRESOLVED] evidence-missing (evidence-missing)
    - cannot decide escalation rule amount-limit: no value for field amount in trace
    - required evidence missing: authorization_record

UNRESOLVED means the trace did not carry the evidence needed to decide the case; it is never counted as a pass.
exit=1

$ sop-contract test examples/support-triage.contract.yaml --traces examples/traces/support-triage
Cases: 7  PASS: 1  FAIL: 0  UNRESOLVED: 6
[PASS] happy-path; the other six cases are UNRESOLVED with
"no trace provided for this case" (only a happy-path trace ships for
triage — UNRESOLVED working as designed, not a pass).
exit=1
```

The required demonstrations are real outcomes of the runner, not fixtures
labelled by hand: the escalation trace refunds $150 with no approval event
and FAILs on the amount-limit rule alone; the evidence-missing trace omits
the amount and the `authorization_record` evidence and is UNRESOLVED.

## Ship record

Filled in after the upload steps complete (repo creation, topics read-back,
first CI run, v0.1.0 release) — see the final delivery report for the
verified values.
