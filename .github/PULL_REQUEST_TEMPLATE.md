## Summary

<!-- Briefly describe what changed and why. -->

## Related Issue

Closes #

## Scope

<!-- List the files, modules, docs, or behavior intentionally changed. -->

## Out of Scope

<!-- List related work intentionally excluded from this PR. -->

## Risk Level

Select exactly one:

- [ ] Low
- [ ] Medium
- [ ] High

Reason:

<!-- Explain why this risk level fits. -->

## Architecture And Roadmap Check

- [ ] Controllers still own batch coordination, retry policy, scraper reset/rotation, summaries, and retry exhaustion.
- [ ] Stage services still own per-item fetch, parse, persist, and lifecycle outcomes.
- [ ] Scrapers fetch only.
- [ ] Parsers parse only.
- [ ] Storage modules centralize relational writes.
- [ ] Pipelines remain thin.
- [ ] No ingestion responsibilities moved into dbt.
- [ ] No dbt, Airflow, CT/T splits, eco-adjusted stats, or demo expansion added unless explicitly requested.
- [ ] Schema changes, if any, follow the current schema ownership rule for this phase.

## Documentation Check

- [ ] Docs updated
- [ ] Docs not needed

Reason:

<!-- If docs were not needed, explain why. -->

## Verification

Commands run:

<!-- List commands or manual checks performed. -->

Results:

<!-- Summarize the result of each command or check. -->

## Review Notes

<!-- Call out reviewer focus areas, decisions, or known follow-ups. -->
