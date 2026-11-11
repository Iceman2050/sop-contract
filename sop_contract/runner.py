"""Evaluate recorded/simulated agent traces against a contract.

Verdicts: PASS (every check decided and satisfied), FAIL (a hard
violation: forbidden/unpermitted/unknown tool, required step missing,
exception path not followed, escalation rule violated, postcondition
false), UNRESOLVED (the trace does not carry the evidence needed to
decide — never silently passed).
"""

import json
from pathlib import Path

from . import spec
from .sandbox import Sandbox

PASS, FAIL, UNRESOLVED = "PASS", "FAIL", "UNRESOLVED"


def load_traces(path):
    """Load traces from a .json file or a directory of .json files.

    Each trace is a dict with a ``case_id`` matching a generated case.
    A single trace file may also be a JSON list of traces.
    """
    p = Path(path)
    files = sorted(p.glob("*.json")) if p.is_dir() else [p]
    traces = {}
    for f in files:
        data = json.loads(f.read_text(encoding="utf-8"))
        for trace in data if isinstance(data, list) else [data]:
            traces[trace["case_id"]] = trace
    return traces


def _field_value(trace, field):
    """Escalation field value: trace context first, then event args."""
    ctx = trace.get("context") or {}
    if field in ctx:
        return ctx[field]
    for event in trace.get("events") or []:
        args = event.get("args") or {}
        if field in args:
            return args[field]
    return None


def evaluate_trace(contract, trace, sandbox=None):
    """Return (verdict, reasons) for one trace against the contract."""
    sandbox = sandbox or Sandbox()
    fails, unresolved = [], []
    called, _ledger, unknown = sandbox.replay(trace)
    called_set = set(called)
    permitted = set(contract.get("permitted_tools") or [])
    forbidden = {f["tool"]: f["id"] for f in spec.steps(contract, "forbidden_actions")}

    for tool in called_set:
        if tool in forbidden:
            fails.append(f"forbidden action attempted: {tool} ({forbidden[tool]})")
        elif tool not in permitted:
            fails.append(f"unpermitted tool used: {tool}")
    for tool in set(unknown):
        fails.append(f"tool not in sandbox registry: {tool}")

    ctx = trace.get("context") or {}
    exception_triggered = False
    for exc in contract.get("exception_paths") or []:
        field = exc["when_field"]
        if field not in ctx:
            unresolved.append(
                f"cannot decide exception path {exc['id']}: context lacks {field}")
            continue
        if ctx[field] == exc["when_equals"]:
            exception_triggered = True
            if exc["expected_tool"] not in called_set:
                fails.append(f"exception path {exc['id']}: expected "
                             f"{exc['expected_tool']} was not used")
            for bad in exc.get("must_not_use") or []:
                if bad in called_set:
                    fails.append(f"exception path {exc['id']}: {bad} must not be used")

    if not exception_triggered:
        for step in spec.steps(contract, "required_steps"):
            if step["tool"] not in called_set:
                fails.append(f"required step not performed: {step['id']} ({step['tool']})")
        for rule in contract.get("human_escalation") or []:
            value = _field_value(trace, rule["field"])
            if value is None:
                unresolved.append(
                    f"cannot decide escalation rule {rule['id']}: "
                    f"no value for field {rule['field']} in trace")
                continue
            if isinstance(value, (int, float)) and value > rule["maximum"]:
                approval_tool = rule.get("approval_tool", "request_approval")
                events = trace.get("events") or []
                approval_idx = next((i for i, e in enumerate(events)
                                       if e.get("tool") == approval_tool), None)
                if approval_idx is None:
                    fails.append(
                        f"escalation rule {rule['id']} violated: {rule['field']}={value} "
                        f"is over maximum {rule['maximum']} but {approval_tool} never happened")
                else:
                    approval = events[approval_idx]
                    if (approval.get("result") or {}).get("approved") is False:
                        fails.append(f"escalation rule {rule['id']}: approval was denied "
                                     "but execution continued")
                    exec_idx = next((i for i, e in enumerate(events)
                                     if e.get("tool") != approval_tool
                                     and (e.get("args") or {}).get(rule["field"]) is not None),
                                    None)
                    if exec_idx is not None and approval_idx > exec_idx:
                        fails.append(f"escalation rule {rule['id']}: execution "
                                     "happened before approval")
        outcome = trace.get("outcome")
        if outcome is None:
            unresolved.append("no outcome recorded in trace")
        else:
            for post in contract.get("postconditions") or []:
                if post not in outcome:
                    unresolved.append(f"postcondition not evidenced in outcome: {post}")
                elif outcome[post] is not True:
                    fails.append(f"postcondition not met: {post}")
        evidence = trace.get("evidence")
        if evidence is None:
            unresolved.append("no evidence block in trace")
        else:
            for key in contract.get("evidence") or []:
                if evidence.get(key) is None:
                    unresolved.append(f"required evidence missing: {key}")

    if fails:
        return FAIL, fails + unresolved
    if unresolved:
        return UNRESOLVED, unresolved
    return PASS, ["all checks decided and satisfied"]


def run_cases(contract, cases, traces, sandbox=None):
    """Evaluate every generated case; a case with no trace is UNRESOLVED."""
    sandbox = sandbox or Sandbox()
    results = []
    for case in cases:
        trace = traces.get(case["id"])
        if trace is None:
            verdict, reasons = UNRESOLVED, ["no trace provided for this case"]
        else:
            verdict, reasons = evaluate_trace(contract, trace, sandbox)
        results.append({"case_id": case["id"], "kind": case["kind"],
                        "verdict": verdict, "reasons": reasons})
    summary = {v: sum(1 for r in results if r["verdict"] == v)
               for v in (PASS, FAIL, UNRESOLVED)}
    summary["total"] = len(results)
    return {"workflow": contract.get("workflow"), "summary": summary,
            "cases": results}
