from pathlib import Path

from sop_contract import generate, runner, spec

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"


def _refund():
    return spec.load_contract(EXAMPLES / "refund-approval.contract.yaml")


def _run_refund_fixtures():
    contract = _refund()
    cases = generate.generate_cases(contract)
    traces = runner.load_traces(EXAMPLES / "traces" / "refund-approval")
    return runner.run_cases(contract, cases, traces)


def test_fixture_verdicts():
    rep = _run_refund_fixtures()
    verdicts = {c["case_id"]: c["verdict"] for c in rep["cases"]}
    assert verdicts == {
        "happy-path": "PASS",
        "exception-invalid-order": "PASS",
        "forbidden-no-gift-card-refund": "FAIL",
        "forbidden-no-order-deletion": "FAIL",
        "escalation-amount-limit": "FAIL",
        "missing-required-step": "FAIL",
        "evidence-missing": "UNRESOLVED",
    }
    assert rep["summary"] == {"PASS": 2, "FAIL": 4, "UNRESOLVED": 1, "total": 7}


def _happy_trace(**overrides):
    trace = {
        "case_id": "happy-path",
        "context": {"amount": 50, "order_valid": True},
        "events": [
            {"tool": "verify_eligibility", "args": {}, "result": {"eligible": True}},
            {"tool": "record_authorization", "args": {}, "result": {}},
            {"tool": "issue_refund", "args": {"amount": 50}, "result": {}},
            {"tool": "record_result", "args": {}, "result": {}},
        ],
        "outcome": {"eligibility_verified": True, "authorization_recorded": True,
                    "execution_result_recorded": True},
        "evidence": {"eligibility_check": "c", "authorization_record": "a",
                     "execution_receipt": "r"},
    }
    trace.update(overrides)
    return trace


def test_happy_trace_passes():
    verdict, _ = runner.evaluate_trace(_refund(), _happy_trace())
    assert verdict == "PASS"


def test_escalation_with_prior_approval_passes():
    trace = _happy_trace(context={"amount": 150, "order_valid": True})
    trace["events"].insert(2, {"tool": "request_approval",
                               "args": {"amount": 150},
                               "result": {"approved": True}})
    trace["events"][3]["args"] = {"amount": 150}
    verdict, reasons = runner.evaluate_trace(_refund(), trace)
    assert verdict == "PASS", reasons


def test_escalation_approval_after_execution_fails():
    trace = _happy_trace(context={"amount": 150, "order_valid": True})
    trace["events"].append({"tool": "request_approval",
                            "args": {"amount": 150}, "result": {"approved": True}})
    verdict, reasons = runner.evaluate_trace(_refund(), trace)
    assert verdict == "FAIL"
    assert any("before approval" in r for r in reasons)


def test_exception_violated_fails():
    trace = {"case_id": "x", "context": {"amount": 10, "order_valid": False},
             "events": [{"tool": "issue_refund", "args": {"amount": 10}, "result": {}}],
             "outcome": {}, "evidence": {}}
    verdict, reasons = runner.evaluate_trace(_refund(), trace)
    assert verdict == "FAIL"
    assert any("invalid-order" in r for r in reasons)


def test_unknown_tool_fails():
    trace = _happy_trace()
    trace["events"].append({"tool": "teleport_money", "args": {}, "result": {}})
    verdict, reasons = runner.evaluate_trace(_refund(), trace)
    assert verdict == "FAIL"
    assert any("sandbox registry" in r for r in reasons)


def test_missing_trace_is_unresolved():
    contract = _refund()
    rep = runner.run_cases(contract, generate.generate_cases(contract), {})
    assert all(c["verdict"] == "UNRESOLVED" for c in rep["cases"])


def test_no_evidence_is_unresolved_not_pass():
    trace = _happy_trace(evidence=None)
    verdict, _ = runner.evaluate_trace(_refund(), trace)
    assert verdict == "UNRESOLVED"
