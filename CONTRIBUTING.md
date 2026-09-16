# Contributing

Small, reproducible fixes and documentation improvements are welcome. Start with
an issue for changes to key matching or the contract; silent normalization can
hide data loss. Use synthetic examples only. Do not post customer CSVs or secrets.

1. Fork the repository and create a focused branch.
2. Reproduce the problem in a small test in `tests/test_guard.py`.
3. Implement the fix and run `python -m unittest discover -s tests -v`.
4. Explain expected behavior, observed behavior, compatibility and test results.

Runtime dependencies must remain empty for the current scope. Keep the CLI exit
codes stable. JSON field changes need a schema-version decision. Input files
must remain read-only, and reports must not expose cell values or paths.

By submitting a contribution, you agree it is available under this project's MIT
license and that you have the right to contribute it. Disclose relevant AI
assistance in your PR so reviewers know what validation remains. Human review is
required before merging. Do not manufacture contributions, popularity or usage
statistics to qualify for a sponsorship program.

Maintainer: `umd0730`. This is a new volunteer project; there is no support SLA.
