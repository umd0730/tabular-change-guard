# Validation record

2026-09-17 decimal-context fix, local Windows / Python 3.12.14:

- 35 unittest cases passed: the original 31 plus four tests (eight subcases)
  with constrained caller decimal contexts. Before the fix, these produced
  three assertion failures and four errors.
- Tested unequal large/tiny totals, exact cancellation, strict caller traps,
  and preservation of caller settings and signal flags.
- Summation now uses a private context instead of inheriting caller exponent
  limits. This fixes false acceptance and exceptions in embedded Python use.
- The normal standalone CLI was not affected under its default decimal context.
  This record describes the candidate fix, not a replacement of v0.1.0.

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
