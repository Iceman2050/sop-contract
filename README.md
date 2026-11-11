# sop-contract

Convert human-approved standard operating procedures (SOPs) into executable
agent acceptance tests.

An agent doing real work — refunds, ticket handling, approvals — should be
checked against the *procedure a human actually approved*, not against a
generic benchmark. `sop-contract` takes that procedure as a small contract
file, generates acceptance test cases from it, evaluates recorded or
simulated agent behaviour against it, and emits an evidence report with a
per-case verdict of **PASS**, **FAIL**, or **UNRESOLVED**.

Zero dependencies. Python 3.10+, standard library only.

## Workflow

1. A human writes — and a qualified human approves — a procedure contract
   (YAML subset or JSON, see below).
2. `sop-contract validate` checks the contract spec.
3. `sop-contract generate` derives acceptance test cases from the contract:
   the happy path, one case per exception path, one per forbidden action,
   one per human-escalation rule, a missing-required-step case, and an
   evidence-missing case.
4. `sop-contract test` replays scripted agent traces (JSON) through a local
   simulated tool sandbox and evaluates them: required steps happened,
   forbidden actions never happened, exception paths were followed,
   escalation rules fired, postconditions and evidence requirements met.
5. The evidence report (text or JSON) lists PASS / FAIL / UNRESOLVED per
   case. A case that cannot be decided from the evidence provided is
   reported **UNRESOLVED — never silently passed**.

## What this tool does and does not do — honestly

- It evaluates **recorded or simulated** agent behaviour (traces) against a
  contract. It does **not** drive a live LLM agent, and it does not observe
  a live agent unless traces are exported from that agent into the trace
  format below.
- The sandbox tools are **local simulations only** (in-memory fakes). No
  real systems are touched, no real refunds are issued, no real customer
  data is involved.
- A PASS means "this trace satisfies this contract, on the evidence in the
  trace." It is not a certification, and this tool never claims an agent or
  a workflow is "certified compliant."
- An LLM may draft a contract, but **a qualified human must review the
  rules before they are treated as operational policy.** A contract is only
  as good as the procedure the human approved.

## How this differs

- **EvalEgress** (formerly EvalScope) statically scans declared config/file
  text for eval-to-prod *exposure* (secrets, permissive roles). It never
  executes or evaluates a procedure run. sop-contract evaluates procedure
  behaviour against an SOP.
- **HarnessProof** runs curated, fixed scenario suites against live agent
  endpoints (generic harness mechanics). sop-contract's cases are generated
  from *your* SOP contract — your required steps, exceptions, and approval
  limits — and run against recorded/simulated traces.
- **Agentic Receipts** records pre-transaction authorizations (what was
  approved, amount, expiry) and performs no runtime verification.
  sop-contract is the other half: it tests whether the run actually
  followed the approved procedure.

## Install

```bash
pip install -e .
sop-contract doctor
```

## Quick start

```bash
sop-contract validate examples/refund-approval.contract.yaml
sop-contract generate examples/refund-approval.contract.yaml
sop-contract test examples/refund-approval.contract.yaml \
    --traces examples/traces/refund-approval
sop-contract test examples/refund-approval.contract.yaml \
    --traces examples/traces/refund-approval --format json --out report.json
sop-contract report --input report.json --format text
```

`test` exits 0 only when every case is PASS; it exits 1 when any case is
FAIL or UNRESOLVED.

Expected result on the bundled refund fixtures (by design — the fixtures
include deliberate violations):

```
Cases: 7  PASS: 2  FAIL: 4  UNRESOLVED: 1
[PASS] happy-path
[PASS] exception-invalid-order
[FAIL] forbidden-no-gift-card-refund
[FAIL] forbidden-no-order-deletion
[FAIL] escalation-amount-limit   — amount=150 is over maximum 100 but
                                   request_approval never happened
[FAIL] missing-required-step     — verify-order (verify_eligibility) omitted
[UNRESOLVED] evidence-missing    — no amount in trace; required evidence
                                   authorization_record missing
```

A second contract, `examples/support-triage.contract.yaml` (support-ticket
triage), ships with a happy-path trace to show the format is not
refund-specific; its other cases report UNRESOLVED until traces are
provided for them — which is the point of UNRESOLVED.

## The contract spec

```yaml
workflow: refund-approval
objective: Refund a customer order only when ...
preconditions:
  - order_exists
  - payment_captured
permitted_tools:
  - get_order
  - verify_eligibility
  - issue_refund
required_steps:
  - id: verify-order
    tool: verify_eligibility
forbidden_actions:
  - id: no-gift-card-refund
    tool: refund_to_gift_card
exception_paths:
  - id: invalid-order
    when_field: order_valid        # trace context field
    when_equals: false
    expected_tool: deny_request
    must_not_use:
      - issue_refund
human_escalation:
  - id: amount-limit
    field: amount                  # numeric threshold rule
    maximum: 100
    action: require_approval
    approval_tool: request_approval
postconditions:
  - eligibility_verified
  - authorization_recorded
  - execution_result_recorded
evidence:
  - eligibility_check
  - authorization_record
  - execution_receipt
```

Fields: workflow name, objective, preconditions, permitted tools, required
steps (ids + tool), forbidden actions, exception paths
(condition → expected behaviour), human-escalation rules (numeric field,
maximum, `require_approval`), postconditions, and evidence requirements.

The bundled refund contract encodes the rules: **verify-order** (required),
**amount-limit** (maximum 100 → `require_approval`), **invalid-order**
(deny); completion requires `eligibility_verified`,
`authorization_recorded`, and `execution_result_recorded`.

### YAML subset and JSON

Contracts are accepted in JSON (standard `json` module) or in a documented
YAML subset parsed by the bundled parser: `key: value` mappings nested by
indentation, lists of scalars, lists of mappings, plain/quoted strings,
integers, floats, booleans, `null`, `#` comments, `[]`. Anchors, tags,
multi-line strings, and flow mappings are **not** supported — write the
JSON form if you need more than the subset.

## Trace format

A trace is one JSON object (a file per case, or a JSON list) with:

```json
{
  "case_id": "happy-path",
  "context": {"amount": 50, "order_valid": true},
  "events": [
    {"tool": "verify_eligibility", "args": {"order_id": "ord-1"},
     "result": {"eligible": true}}
  ],
  "outcome": {"eligibility_verified": true, "authorization_recorded": true,
              "execution_result_recorded": true},
  "evidence": {"eligibility_check": "check-1",
               "authorization_record": "auth-1",
               "execution_receipt": "rcpt-1"}
}
```

Verdict rules, in order: any hard violation (forbidden, unpermitted, or
unknown tool; required step missing; exception path not followed;
over-limit execution without prior approval; a postcondition recorded as
false) → **FAIL**. Otherwise, any check that cannot be decided from the
trace (missing context field, missing outcome/evidence, no trace at all)
→ **UNRESOLVED**. Otherwise → **PASS**.

## Development

```bash
pip install -e ".[dev]"
pytest -q
```

## License

MIT — see `LICENSE`.
