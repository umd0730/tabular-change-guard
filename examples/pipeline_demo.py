"""Exercise installed csvkit and petl with synthetic, temporary CSVs.

Run from a checkout: python -m examples.pipeline_demo
Optional demo dependencies: csvkit and petl. The guard itself needs neither.
"""

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from tabular_change_guard import check


def main():
    try:
        import petl
        import csvkit  # noqa: F401 - check the optional dependency before writing
    except ImportError:
        raise SystemExit("This demo needs the optional csvkit and petl packages.") from None

    source = b"id,team,quantity\n001, West ,0.10\n002,East,0.20\n003,West,0.30\n"
    results = []
    with tempfile.TemporaryDirectory(prefix="tabular-guard-demo-") as directory:
        root = Path(directory)
        before = root / "before.csv"
        before.write_bytes(source)

        for infer in (False, True):
            after = root / "sorted.csv"
            command = [sys.executable, "-m", "csvkit.utilities.csvsort", "-c", "team"]
            if not infer:
                command.append("--no-inference")
            command.append(str(before))
            run = subprocess.run(command, capture_output=True, check=True)
            after.write_bytes(run.stdout)
            report = check(before, after, keys=["id"], sums=["quantity"])
            if report["ok"] == infer:
                raise AssertionError("Unexpected csvkit inference result")
            if infer and report["counts"].get("row_removed") != 3:
                raise AssertionError("Expected to detect all three changed identifiers")
            results.append({"case": "csvkit-inference" if infer else "csvkit-exact",
                            "ok": report["ok"], "counts": report["counts"]})

        for change_ids in (False, True):
            after = root / "cleaned.csv"
            table = petl.fromcsv(str(before)).convert("team", str.strip)
            if change_ids:
                table = table.convert("id", int)
            petl.tocsv(table, str(after), encoding="utf-8")
            report = check(before, after, keys=["id"], allow=["team"], sums=["quantity"])
            if report["ok"] == change_ids:
                raise AssertionError("Unexpected petl conversion result")
            if change_ids and report["counts"].get("row_added") != 3:
                raise AssertionError("Expected to detect all three changed identifiers")
            results.append({"case": "petl-id-conversion" if change_ids else "petl-trim",
                            "ok": report["ok"], "counts": report["counts"]})

        if hashlib.sha256(before.read_bytes()).digest() != hashlib.sha256(source).digest():
            raise AssertionError("The baseline was modified")
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
