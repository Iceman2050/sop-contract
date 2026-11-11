from pathlib import Path

from sop_contract import spec

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def test_bundled_examples_are_valid():
    for name in ("refund-approval.contract.yaml", "support-triage.contract.yaml"):
        contract = spec.load_contract(EXAMPLES / name)
        assert spec.validate(contract) == [], name


def test_json_contract_loads(tmp_path):
    p = tmp_path / "c.json"
    p.write_text('{"workflow": "w", "objective": "o", "permitted_tools": ["t"]}')
    contract = spec.load_contract(p)
    assert spec.validate(contract) == []


def test_missing_fields_rejected():
    errs = spec.validate({"permitted_tools": ["t"]})
    assert any("workflow" in e for e in errs)
    assert any("objective" in e for e in errs)


def test_empty_permitted_tools_rejected():
    errs = spec.validate({"workflow": "w", "objective": "o", "permitted_tools": []})
    assert any("permitted_tools" in e for e in errs)


def test_bad_escalation_rejected():
    contract = {"workflow": "w", "objective": "o", "permitted_tools": ["t"],
                "human_escalation": [{"id": "r", "field": "amount",
                                      "maximum": "lots", "action": "auto_approve"}]}
    errs = spec.validate(contract)
    assert any("maximum" in e for e in errs)
    assert any("unsupported escalation action" in e for e in errs)


def test_required_step_tool_must_be_permitted():
    contract = {"workflow": "w", "objective": "o", "permitted_tools": ["t"],
                "required_steps": [{"id": "s", "tool": "other"}]}
    assert any("not in permitted_tools" in e for e in spec.validate(contract))


def test_duplicate_ids_rejected():
    contract = {"workflow": "w", "objective": "o", "permitted_tools": ["t"],
                "required_steps": [{"id": "s", "tool": "t"}, {"id": "s", "tool": "t"}]}
    assert any("duplicate" in e for e in spec.validate(contract))
