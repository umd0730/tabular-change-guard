# Check real csvkit and petl pipelines

The guard can check CSVs written by existing data tools. The optional demo
uses synthetic data in a temporary directory and verifies that the baseline
bytes remain unchanged. It makes no network calls and does not read your data.

From a checkout, in a separate environment with csvkit and petl installed:

```sh
python -m examples.pipeline_demo
```

If needed, install the optional demo dependencies into that environment with
`python -m pip install csvkit petl`. Neither package is a runtime dependency of
Tabular Change Guard. The demo is part of the repository, not the wheel.

Expected results:

| Pipeline | Result | Reason |
| --- | --- | --- |
| `csvsort -c team --no-inference` | Pass | Row reordering preserves exact identifiers and quantities. |
| `csvsort -c team` | Fail | Type inference changes identifiers `001`/`002`/`003` to `1`/`2`/`3`. |
| `petl.fromcsv(...).convert("team", str.strip)` | Pass | Only the allowed team column changes. |
| Add `.convert("id", int)` | Fail | Identifier conversion violates exact-key preservation. |

The two failing comparisons each report three removed and three added rows.
Those are expected detections: the demo exits `0` only when all four outcomes
match expectations. The guard's normal CLI still exits `1` on a failed check.
The example reports counts without including cell values or input paths.

## Use the checks in your workflow

For sorting, disable inference when all original values must remain exact:

```sh
csvsort -c team --no-inference original.csv > sorted.csv
python -m tabular_change_guard original.csv sorted.csv --key id --sum quantity
```

For trimming `team`, permit that column while preserving everything else:

```sh
python -m tabular_change_guard original.csv cleaned.csv --key id --allow team --required team --sum quantity
```

Output must be a new file. A passing report verifies these constraints, not
whether the transformation satisfies your business intent. `csvkit` inference
and `petl.convert(..., int)` are intentional features; the demo illustrates
when those choices conflict with an exact-ID contract, not bugs in either tool.

## Executed validation

2026-09-17, Windows / Python 3.12.14: all four cases ran with csvkit source based
on `ba8033d` plus the empty-input fix and petl source based on `9a0b844`.
This is a maintainer-run interoperability check, not third-party adoption,
endorsement or a production usage claim. The script asserts the outcomes again
when you run it against your installed versions.
