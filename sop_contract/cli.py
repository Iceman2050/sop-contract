"""Command line interface: sop-contract.

  sop-contract validate <contract>
  sop-contract generate <contract> [--out FILE]
  sop-contract test <contract> --traces <dir|file> [--format json|text] [--out FILE]
  sop-contract report --input FILE [--format json|text]
  sop-contract doctor
"""

import argparse
import json
import sys
from pathlib import Path

from . import __version__, generate, report as report_mod, runner, spec

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def _load_or_die(path):
    try:
        contract = spec.load_contract(path)
    except Exception as exc:  # file/parse errors are user-facing here
        print(f"error: cannot load contract {path}: {exc}", file=sys.stderr)
        raise SystemExit(2)
    errors = spec.validate(contract)
    if errors:
        for err in errors:
            print(f"invalid contract: {err}", file=sys.stderr)
        raise SystemExit(1)
    return contract


def cmd_validate(args):
    contract = _load_or_die(args.contract)
    print(f"valid contract: {contract['workflow']}")
    return 0


def cmd_generate(args):
    contract = _load_or_die(args.contract)
    text = json.dumps(generate.generate_cases(contract), indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(text)
    return 0


def cmd_test(args):
    contract = _load_or_die(args.contract)
    cases = generate.generate_cases(contract)
    try:
        traces = runner.load_traces(args.traces)
    except Exception as exc:
        print(f"error: cannot load traces {args.traces}: {exc}", file=sys.stderr)
        return 2
    rep = runner.run_cases(contract, cases, traces)
    if args.out:
        Path(args.out).write_text(json.dumps(rep, indent=2) + "\n", encoding="utf-8")
    print(report_mod.render(rep, args.format))
    return 0 if all(c["verdict"] == runner.PASS for c in rep["cases"]) else 1


def cmd_report(args):
    rep = json.loads(Path(args.input).read_text(encoding="utf-8"))
    print(report_mod.render(rep, args.format))
    return 0


def cmd_doctor(args):
    problems = []
    if sys.version_info < (3, 10):
        problems.append(f"python >= 3.10 required, running {sys.version.split()[0]}")
    for name in ("refund-approval.contract.yaml", "support-triage.contract.yaml"):
        path = EXAMPLES / name
        if not path.exists():
            problems.append(f"bundled example missing: {name}")
            continue
        errs = spec.validate(spec.load_contract(path))
        if errs:
            problems.append(f"bundled example {name} invalid: {errs}")
    if problems:
        for p in problems:
            print(f"doctor: FAIL - {p}")
        return 1
    print(f"doctor: sop-contract {__version__} OK; python "
          f"{sys.version.split()[0]}; bundled examples valid")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="sop-contract", description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("validate", help="validate a contract file")
    p.add_argument("contract")
    p.set_defaults(fn=cmd_validate)

    p = sub.add_parser("generate", help="generate acceptance test cases")
    p.add_argument("contract")
    p.add_argument("--out")
    p.set_defaults(fn=cmd_generate)

    p = sub.add_parser("test", help="evaluate traces against a contract")
    p.add_argument("contract")
    p.add_argument("--traces", required=True, help="trace .json file or directory")
    p.add_argument("--format", choices=("text", "json"), default="text")
    p.add_argument("--out", help="also write the JSON report here")
    p.set_defaults(fn=cmd_test)

    p = sub.add_parser("report", help="re-render a saved JSON report")
    p.add_argument("--input", required=True)
    p.add_argument("--format", choices=("text", "json"), default="text")
    p.set_defaults(fn=cmd_report)

    p = sub.add_parser("doctor", help="self-check")
    p.set_defaults(fn=cmd_doctor)

    args = parser.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
