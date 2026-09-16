# Roadmap driven by real use

The first version targets before/after checks for small CSV cleanup tasks. It
will not become a general spreadsheet editor.

## Implemented for review

- Add a versioned JSON contract file so CI and agents use the same reviewed rules.
  The development branch supports `--contract` and rejects inline overrides.
  This is a maintainer-proposed improvement, not evidence of external demand.

## Next candidates (not implemented)

- Test a broader synthetic CP932/UTF-8 corpus, including difficult quoted records.
- Design per-column normalization rules that display exactly what was accepted.
- Add an optional Markdown report without leaking cell values or raw paths.

Before prioritizing, collect reproducible feedback from actual users. A useful
early result is one independent user running it on their workflow and reporting
where the checks help or fail. Download counts, stars and external contributions
must be measured, never inferred from releases or self-authored PRs.

Review support-program eligibility only when the project has meaningful new
evidence. Publishing this project does not establish popularity or adoption.
