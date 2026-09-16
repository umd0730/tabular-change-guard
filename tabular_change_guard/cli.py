"""CLI reports go to stdout; input/configuration failures go to stderr."""

import argparse
import json
import sys

from . import __version__
from .core import InputError, check
from .contract import load_contract


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check unintended changes in CSV edits offline.")
    parser.add_argument("before", help="Original CSV (read only)")
    parser.add_argument("after", help="Edited CSV (read only)")
    parser.add_argument("--contract", help="Versioned JSON rules; cannot be combined with inline rules")
    parser.add_argument("--key", action="append", help="Key column; repeat for composite keys")
    parser.add_argument("--allow", action="append", help="Editable column; repeat as needed")
    parser.add_argument("--required", action="append", help="Nonblank output column")
    parser.add_argument("--decimal", action="append", help="Plain decimal output column")
    parser.add_argument("--sum", action="append", help="Column whose exact total must be preserved")
    parser.add_argument("--before-encoding")
    parser.add_argument("--after-encoding")
    parser.add_argument("--delimiter", help="One character; use 'tab' for TSV")
    parser.add_argument("--format", choices=["json", "text"], default="json")
    parser.add_argument("--allow-formulas", action="store_true", default=None, help="Disable formula-like text detection")
    parser.add_argument("--version", action="version", version=__version__)
    args = parser.parse_args(argv)
    try:
        options = {"keys": args.key, "allow": args.allow, "required": args.required,
                   "decimals": args.decimal, "sums": args.sum,
                   "before_encoding": args.before_encoding, "after_encoding": args.after_encoding,
                   "delimiter": "\t" if args.delimiter == "tab" else args.delimiter,
                   "check_formulas": None if args.allow_formulas is None else False}
        options = {name: value for name, value in options.items() if value is not None}
        if args.contract is not None:
            if options:
                raise InputError("--contract cannot be combined with inline rule options")
            options = load_contract(args.contract)
        if "keys" not in options:
            raise InputError("provide --key or a --contract containing keys")
        result = check(args.before, args.after, **options)
    except InputError as exc:
        print(json.dumps({"error": "invalid_input", "message": str(exc)}), file=sys.stderr)
        return 2
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=True, indent=2))
    else:
        print("PASS" if result["ok"] else "FAIL")
        print("Records: {} -> {}".format(result["before"]["records"], result["after"]["records"]))
        for code, count in result["counts"].items():
            print("{}: {}".format(code, count))
    return 0 if result["ok"] else 1
