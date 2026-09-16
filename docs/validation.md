# Validation record

2026-09-17 contract feature, local Windows / Python 3.12.14:

- 40 unittest cases passed, including the existing 31 and nine contract tests.
- Compared file-based and inline rule reports; checked rejection of duplicate
  and unknown properties, incorrect types, excessive size, malformed UTF-8/JSON,
  missing rules and attempts to override file rules from the CLI.
- Tested CP932 inputs with UTF-8 BOM contracts, TSV, formula opt-out and unchanged
  baseline bytes. Synthetic data only; no independent usage claim.
- This change is prepared for review; the v0.1.0 release does not include it.

2026-09-16 initial implementation. Local Windows / Python 3.12.14:

- 31 unittest cases passed, including real CLI subprocess exit statuses 0/1/2.
- Covered exact IDs, row/column reorder, protected cells, schema changes, missing
  and added rows, duplicate/blank keys, composite keys, blank requirements,
  exact decimal totals beyond 28 digits, malformed CSV, CP932 and UTF-8 BOM,
  TSV, multiline quoted fields, size limits, bounded reports and read-only inputs.
- Reports tested to exclude original cell values and absolute input paths.
- Built the 0.1.0 wheel using setuptools 84.0.0 without downloading dependencies.
  Installed that wheel into a new isolated virtual environment using `--no-index`
  and ran its installed console command successfully against the good example.
- The bad example produced exit 1 and seven findings across five categories,
  matching the documented output.

GitHub Actions defines a 3 OS x 3 Python matrix. A workflow file alone is not proof
that those jobs passed; inspect the Actions results for the published commit.
No live customer datasets or external security audit have been used.
