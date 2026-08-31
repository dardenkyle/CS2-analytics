-- Row-coverage check for fact_player_map_stats (#148): the fact is built
-- from stg_players through inner joins to maps and matches plus an
-- incremental watermark filter, so rows can only ever be lost silently -
-- a null join key, or a watermark bug that skips source rows. Warn when
-- the fact holds fewer than 95% of the source player rows; the tolerance
-- absorbs the normal in-flight window where players land before their
-- parent rows finish processing. Warn severity per the distribution-test
-- policy in docs/dbt_models.md.

{{ config(severity='warn') }}

with counts as (

    select
        (select count(*) from {{ ref('fact_player_map_stats') }}) as fact_rows,
        (select count(*) from {{ ref('stg_players') }}) as source_rows

)

select
    fact_rows,
    source_rows
from counts
where fact_rows < 0.95 * source_rows
