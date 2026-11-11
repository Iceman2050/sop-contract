"""Local simulated tool sandbox.

Every tool here is an in-memory fake: no real systems, no real refunds,
no real customer data. A trace (a recorded sequence of tool calls) is
replayed against this registry; replay only records what was called and
accumulates a fake ledger (e.g. simulated refund amounts). Tools an agent
is *forbidden* from using are registered too — an agent can misuse a real
capability, and the runner needs to recognise the call when it appears
in a trace.
"""


def _record(ledger, tool, event):
    ledger["calls"].append(tool)
    args = event.get("args") or {}
    if "amount" in args:
        ledger["amounts"].append(args["amount"])
    return ledger


# Simulated tools for the bundled example domains (orders/refunds and
# support tickets). Each is a stub: replay bookkeeping only.
SIMULATED_TOOLS = {
    name: _record
    for name in (
        # refund-approval domain
        "get_order", "verify_eligibility", "record_authorization",
        "issue_refund", "record_result", "request_approval", "deny_request",
        "refund_to_gift_card", "delete_order",
        # support-ticket-triage domain
        "read_ticket", "classify_ticket", "assign_ticket",
        "reply_to_customer", "escalate_to_human", "close_ticket",
        "delete_ticket", "send_marketing_email",
    )
}


class Sandbox:
    """Replay a trace's events through the simulated tool registry."""

    def __init__(self, tools=None):
        self.tools = dict(SIMULATED_TOOLS if tools is None else tools)

    def replay(self, trace):
        """Return (called_tools_in_order, ledger, unknown_tools)."""
        ledger = {"calls": [], "amounts": []}
        unknown = []
        for event in trace.get("events") or []:
            tool = event.get("tool")
            fn = self.tools.get(tool)
            if fn is None:
                unknown.append(tool)
                ledger["calls"].append(tool)
                continue
            fn(ledger, tool, event)
        return ledger["calls"], ledger, unknown
