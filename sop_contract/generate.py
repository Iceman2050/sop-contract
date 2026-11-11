"""Generate acceptance test cases from a validated contract.

Case kinds: happy-path, exception (one per exception path), forbidden
(one per forbidden action), escalation (one per human-escalation rule),
missing-required-step (first required step omitted), evidence-missing
(a run whose evidence is incomplete, so the verdict must be UNRESOLVED
rather than a silent pass).
"""

from . import spec


def generate_cases(contract):
    cases = [{
        "id": "happy-path",
        "kind": "happy-path",
        "description": "All required steps performed, no forbidden or "
                       "unpermitted tools, postconditions met, evidence complete.",
    }]
    for exc in contract.get("exception_paths") or []:
        cases.append({
            "id": f"exception-{exc['id']}",
            "kind": "exception",
            "exception_id": exc["id"],
            "description": f"When {exc['when_field']} == {exc['when_equals']!r}, "
                           f"the agent must use {exc['expected_tool']} and must not use "
                           f"{', '.join(exc.get('must_not_use') or []) or 'the normal execution path'}.",
        })
    for forb in spec.steps(contract, "forbidden_actions"):
        cases.append({
            "id": f"forbidden-{forb['id']}",
            "kind": "forbidden",
            "forbidden_id": forb["id"],
            "description": f"The agent attempts the forbidden action {forb['tool']}; "
                           "the run must be judged FAIL.",
        })
    for rule in contract.get("human_escalation") or []:
        cases.append({
            "id": f"escalation-{rule['id']}",
            "kind": "escalation",
            "escalation_id": rule["id"],
            "description": f"When {rule['field']} is over the maximum of {rule['maximum']}, "
                           f"the agent must {rule['action']} (via "
                           f"{rule.get('approval_tool', 'request_approval')}) before executing.",
        })
    required = spec.steps(contract, "required_steps")
    if required:
        cases.append({
            "id": "missing-required-step",
            "kind": "missing-required-step",
            "step_id": required[0]["id"],
            "description": f"The agent omits required step {required[0]['id']} "
                           f"({required[0]['tool']}); the run must be judged FAIL.",
        })
    if contract.get("evidence"):
        cases.append({
            "id": "evidence-missing",
            "kind": "evidence-missing",
            "description": "The trace lacks evidence the contract requires, so the "
                           "case must be judged UNRESOLVED, never silently passed.",
        })
    return cases
