import json
from pathlib import Path

import pytest

from sop_contract import cli

ROOT = Path(__file__).resolve().parent.parent
CONTRACT = str(ROOT / "examples" / "refund-approval.contract.yaml")
TRACES = str(ROOT / "examples" / "traces" / "refund-approval")


def test_validate_ok(capsys):
    assert cli.main(["validate", CONTRACT]) == 0
    assert "valid contract: refund-approval" in capsys.readouterr().out


def test_validate_bad(tmp_path, capsys):
    p = tmp_path / "bad.yaml"
    p.write_text("workflow: x\n")
    with pytest.raises(SystemExit) as exc:
        cli.main(["validate", str(p)])
    assert exc.value.code == 1


def test_generate(capsys):
    assert cli.main(["generate", CONTRACT]) == 0
    cases = json.loads(capsys.readouterr().out)
    assert len(cases) == 7


def test_test_command_exit_1_on_failing_fixtures(capsys):
    assert cli.main(["test", CONTRACT, "--traces", TRACES]) == 1
    out = capsys.readouterr().out
    assert "[FAIL] escalation-amount-limit" in out
    assert "[UNRESOLVED] evidence-missing" in out


def test_test_json_and_report_roundtrip(tmp_path, capsys):
    saved = tmp_path / "report.json"
    assert cli.main(["test", CONTRACT, "--traces", TRACES,
                     "--format", "json", "--out", str(saved)]) == 1
    capsys.readouterr()
    assert cli.main(["report", "--input", str(saved)]) == 0
    assert "PASS: 2" in capsys.readouterr().out


def test_doctor(capsys):
    assert cli.main(["doctor"]) == 0
    assert "OK" in capsys.readouterr().out
