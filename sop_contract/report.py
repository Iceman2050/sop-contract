"""Render an evidence report dict as JSON or human-readable text."""

import json


def render(report, fmt="text"):
    if fmt == "json":
        return json.dumps(report, indent=2)
    s = report["summary"]
    lines = [
        f"SOP Contract evidence report — workflow: {report['workflow']}",
        f"Cases: {s['total']}  PASS: {s['PASS']}  FAIL: {s['FAIL']}  "
        f"UNRESOLVED: {s['UNRESOLVED']}",
        "",
    ]
    for case in report["cases"]:
        lines.append(f"[{case['verdict']}] {case['case_id']} ({case['kind']})")
        for reason in case["reasons"]:
            lines.append(f"    - {reason}")
    lines.append("")
    lines.append("UNRESOLVED means the trace did not carry the evidence "
                 "needed to decide the case; it is never counted as a pass.")
    return "\n".join(lines)
