## Summary

-

## Related Issue

Closes #

## Scope

-

## Out of Scope

-

## Risk Level

- [ ] Low
- [ ] Medium
- [ ] High

Reason:

-

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

-

## Verification

Commands run:

-

Results:

-

## Review Notes

-
