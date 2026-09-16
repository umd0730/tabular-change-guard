# Tabular Change Guard

Check what an AI agent or cleanup script changed in a CSV **before accepting the result**.
An offline Python CLI and library with no runtime dependencies. MIT licensed.

[日本語の説明](README.ja.md) · [Contributing](CONTRIBUTING.md) · [Roadmap](ROADMAP.md)

## The problem

You ask an agent to trim department names. It also turns `001` into `1`, drops a
record, or rounds a quantity. A line diff is noisy when rows are reordered;
checking only the final file misses whether original values were preserved.

Tabular Change Guard compares original and edited records by an explicit key.
Only named columns may change. It flags added/deleted rows, schema changes,
changes to protected cells, missing required values, invalid decimals, changed
totals, and formula-like text. Reports contain row positions and column names,
not cell values or input paths.

This is a small before/after guard, not a replacement for a general data-quality
framework. It does not clean, repair, rewrite, or upload your files.

## Run the examples

Python 3.10 or later. From the repository root, no install is needed:

```sh
python -m tabular_change_guard examples/before.csv examples/after-good.csv --key id --allow team --sum quantity --format text
```

Expected: `PASS`, `Records: 3 -> 3`, exit status `0`. Trimming `team` and reordering
records are allowed; quantities and IDs remain exact.

```sh
python -m tabular_change_guard examples/before.csv examples/after-bad.csv --key id --allow team --sum quantity --format text
```

Expected: `FAIL`, `Records: 3 -> 2`, and:

```text
formula_like_value: 1
protected_value_changed: 2
row_added: 1
row_removed: 2
total_changed: 1
```

Exit status is `1`: the malformed result is detected, not accepted as a success.

To install a command from a local checkout into your chosen Python environment:

```sh
python -m pip install .
tabular-change-guard --version
```

This project has not been published to PyPI. Do not install an unrelated package
with a similar name. Package building uses setuptools; execution itself only uses
the Python standard library.

## Contract and exit codes

| Option | Meaning |
| --- | --- |
| `--key id` | Required stable key; repeat for composite keys. Exact strings, including leading zeros. |
| `--allow team` | Only these columns may change. Key columns cannot be editable. |
| `--required team` | Output must be nonblank. Repeat for multiple columns. |
| `--decimal quantity` | Output must use finite ASCII decimal notation. No exponent, NaN, comma grouping or surrounding spaces. |
| `--sum quantity` | Exact decimal totals must match; validates the column in both inputs. |
| `--before-encoding cp932` | Explicit baseline encoding. Defaults to UTF-8 with optional BOM. |
| `--after-encoding utf-8-sig` | Explicit edited-file encoding. No silent guessing or replacement characters. |
| `--delimiter tab` | TSV; otherwise pass one character, e.g. `;`. Same delimiter for both files. |
| `--format json` | Default: machine-readable JSON. `text` prints a compact summary. |
| `--allow-formulas` | Explicitly disable the formula-like value check. |

- `0`: the supplied contract passed.
- `1`: valid inputs, but a contract violation was found.
- `2`: unusable input or configuration; **not** a successful comparison.

Keys must be nonblank and unique in both files. Duplicate IDs require a genuine
composite key; this tool never silently picks the first record. Header names are
exact and unique. Row and column reordering is allowed, but adding/removing columns
fails without attempting a cell comparison. `comparison_performed` distinguishes
that case in JSON. Header-only files are valid empty datasets; blank physical
records are rejected as width mismatches. Multiline quoted fields are supported.

Record positions are 1-based data records, excluding the header, not physical line
numbers. Reports include input SHA-256 hashes and complete issue counts. At most
1,000 issue details are retained; `issues_truncated` indicates omitted details.
Never redirect stdout onto an input file: the shell would truncate it before this
program starts. Keep an immutable copy of the baseline.

## Reuse reviewed rules

Keep the rules in version control and run the same check locally and in CI:

```sh
python -m tabular_change_guard examples/before.csv examples/after-good.csv --contract examples/contract.json --format text
```

The version 1 contract is a UTF-8 JSON object:

```json
{"schema_version": 1, "keys": ["id"], "allow": ["team"], "required": ["team"], "sums": ["quantity"]}
```

`schema_version` and `keys` are required. Optional arrays are `allow`, `required`,
`decimals` and `sums`. Optional strings are `before_encoding`, `after_encoding`
and `delimiter` (use `"\t"` for TSV, not `"tab"`). `check_formulas` accepts a JSON
boolean and defaults to `true`. Other defaults match the inline CLI rules.
Unknown properties, duplicate properties, invalid types and contracts over
64 KiB are rejected with exit `2`. Invalid column choices are also rejected
when the check runs. Contract schema and report schema are versioned separately.

`--contract` cannot be mixed with any inline rule flag; this prevents accidental
overrides of reviewed rules. `--format` may still select text or JSON output.
Keep the contract and baseline outside the editing agent's writable area.

## Python API

```python
from tabular_change_guard import InputError, check

try:
    report = check("original.csv", "edited.csv", keys=["order_id", "line_id"],
                   allow=["team"], required=["team"], sums=["quantity"])
except InputError:
    # Stop: the inputs could not be compared reliably.
    raise
if not report["ok"]:
    raise SystemExit(1)
```

To reuse a file from Python, use `check("original.csv", "edited.csv",
**load_contract("rules.json"))` after importing `load_contract` from
`tabular_change_guard`. The loader checks structure; `check()` also validates
the rules against the input columns.

## Use with an agent or CI

Ask the agent to write a separate output file and run the command above. Give it
only the minimum report needed for the repair. No provider account, API key,
network call, telemetry, or paid model is needed by this tool.

In CI, run the same command after generating the edited CSV. Exit `1` or `2`
must fail the job. See [the agent workflow](docs/agent-workflow.md). CI for this
project tests Python 3.10, 3.12 and 3.14 on Linux, macOS and Windows.

## Limits

CSV/TSV only; no XLSX formulas, workbook formatting, fuzzy joins, automatic key
normalization or automatic correction. Files are limited to 10 MiB each by
default and held in memory. The Python CSV parser also has a field-size limit.
The API accepts `max_bytes` and `max_issues` overrides for trusted workloads.

Formula detection is a conservative warning: leading whitespace followed by
`=`, `+`, `-` or `@`, except plain signed decimals. It flags existing formulas too.
It is **not** a spreadsheet security guarantee or a complete injection detector.
Totals do not establish business correctness; retained per-cell protection is
stronger. Opting a column into `--allow` permits any change in it unless an
additional check constrains it. No check proves that an AI's edits are correct.

Reports still reveal column names, record positions, hashes and counts. Check
those before sharing a report. No report should be assumed fully anonymous.

## Development and project status

```sh
python -m unittest discover -s tests -v
```

Initial release candidate: 0.1.0. Created with AI assistance; changes and tests
are open for review. All example data is synthetic. There are no claims of
production adoption, independent audits, customers or sponsorships. See
[validation notes](docs/validation.md) for checks actually executed and boundaries.
