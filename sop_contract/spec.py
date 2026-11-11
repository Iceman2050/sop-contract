"""Contract loading and validation.

A contract is a dict (from the YAML subset parser or from JSON) with:
  workflow (str, required), objective (str, required),
  preconditions [str], permitted_tools [str] (required, non-empty),
  required_steps [{id, tool}] (a bare string means id == tool),
  forbidden_actions [{id, tool}] (a bare string means id == tool),
  exception_paths [{id, when_field, when_equals, expected_tool,
                    must_not_use [tool]}],
  human_escalation [{id, field, maximum (number), action: require_approval,
                     approval_tool (default request_approval)}],
  postconditions [str], evidence [str].
"""

import json
from pathlib import Path

from . import yamlmini

ESCALATION_ACTIONS = ("require_approval",)


def load_contract(path):
    text = Path(path).read_text(encoding="utf-8")
    if Path(path).suffix.lower() == ".json":
        return json.loads(text)
    data = yamlmini.parse(text)
    if not isinstance(data, dict):
        raise ValueError("contract top level must be a mapping")
    return data


def steps(contract, key):
    """Normalise a [{id, tool}] or [str] list into [{id, tool}]."""
    out = []
    for item in contract.get(key) or []:
        if isinstance(item, str):
            out.append({"id": item, "tool": item})
        elif isinstance(item, dict):
            out.append({"id": item.get("id"), "tool": item.get("tool")})
    return out


def validate(contract):
    """Return a list of validation errors (empty list = valid)."""
    errs = []
    if not isinstance(contract, dict):
        return ["contract must be a mapping"]
    for field in ("workflow", "objective"):
        if not contract.get(field) or not isinstance(contract.get(field), str):
            errs.append(f"missing or non-string field: {field}")
    tools = contract.get("permitted_tools")
    if not tools or not isinstance(tools, list) or not all(isinstance(t, str) for t in tools):
        errs.append("permitted_tools must be a non-empty list of tool names")
        tools = []
    for key in ("preconditions", "postconditions", "evidence"):
        val = contract.get(key)
        if val is not None and (not isinstance(val, list) or not all(isinstance(v, str) for v in val)):
            errs.append(f"{key} must be a list of strings")
    seen_ids = set()
    for key in ("required_steps", "forbidden_actions"):
        for item in steps(contract, key):
            if not item["id"] or not item["tool"]:
                errs.append(f"{key} entry needs both id and tool: {item!r}")
            elif item["id"] in seen_ids:
                errs.append(f"duplicate step/action id: {item['id']}")
            seen_ids.add(item["id"])
            if key == "required_steps" and item["tool"] and item["tool"] not in tools:
                errs.append(f"required step {item['id']} uses tool not in permitted_tools: {item['tool']}")
    for exc in contract.get("exception_paths") or []:
        if not isinstance(exc, dict):
            errs.append(f"exception_paths entry must be a mapping: {exc!r}")
            continue
        for f in ("id", "when_field", "expected_tool"):
            if not exc.get(f):
                errs.append(f"exception path missing {f}: {exc!r}")
        if "when_equals" not in exc:
            errs.append(f"exception path missing when_equals: {exc!r}")
        if exc.get("id") in seen_ids:
            errs.append(f"duplicate id: {exc.get('id')}")
        seen_ids.add(exc.get("id"))
    for rule in contract.get("human_escalation") or []:
        if not isinstance(rule, dict):
            errs.append(f"human_escalation entry must be a mapping: {rule!r}")
            continue
        for f in ("id", "field", "action"):
            if not rule.get(f):
                errs.append(f"escalation rule missing {f}: {rule!r}")
        if not isinstance(rule.get("maximum"), (int, float)) or isinstance(rule.get("maximum"), bool):
            errs.append(f"escalation rule maximum must be a number: {rule!r}")
        if rule.get("action") and rule["action"] not in ESCALATION_ACTIONS:
            errs.append(f"unsupported escalation action {rule['action']!r} (supported: {ESCALATION_ACTIONS})")
        if rule.get("id") in seen_ids:
            errs.append(f"duplicate id: {rule.get('id')}")
        seen_ids.add(rule.get("id"))
    return errs
