from pathlib import Path

from sop_contract import generate, spec

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def _cases(name):
    return generate.generate_cases(spec.load_contract(EXAMPLES / name))


def test_refund_case_set():
    cases = _cases("refund-approval.contract.yaml")
    ids = [c["id"] for c in cases]
    # 1 happy + 1 exception + 2 forbidden + 1 escalation + 1 missing-step + 1 evidence
    assert ids == ["happy-path", "exception-invalid-order",
                   "forbidden-no-gift-card-refund", "forbidden-no-order-deletion",
                   "escalation-amount-limit", "missing-required-step",
                   "evidence-missing"]


def test_triage_case_set_is_general():
    cases = _cases("support-triage.contract.yaml")
    kinds = [c["kind"] for c in cases]
    assert kinds == ["happy-path", "exception", "forbidden", "forbidden",
                     "escalation", "missing-required-step", "evidence-missing"]


def test_minimal_contract_generates_happy_only():
    contract = {"workflow": "w", "objective": "o", "permitted_tools": ["t"]}
    cases = generate.generate_cases(contract)
    assert [c["id"] for c in cases] == ["happy-path"]
