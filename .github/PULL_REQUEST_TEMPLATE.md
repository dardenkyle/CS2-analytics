## Summary

-

## Related Issue

Closes #

## Scope

-

## Out of Scope

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
- [ ] Schema changes, if any, keep `cs2_analytics/storage/schema.sql` as the source of truth.

## Documentation Check

- [ ] Docs updated
- [ ] Docs not needed

Reason:

-

## Verification

-

## Review Notes

-
