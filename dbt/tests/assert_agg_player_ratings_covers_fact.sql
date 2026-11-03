-- Coverage check for agg_player_ratings (#245): every fact row belongs to
-- exactly one player row, so maps_played summed over the aggregate must
-- equal the fact's row count. A shortfall means players were dropped (for
-- example by the join to dim_players); an excess means a player was
-- counted twice. Error severity: the leaderboard reads this model directly.

with counts as (

    select
        (select coalesce(sum(maps_played), 0) from {{ ref('agg_player_ratings') }})
            as aggregated_maps,
        (select count(*) from {{ ref('fact_player_map_stats') }}) as fact_rows

)

select
    aggregated_maps,
    fact_rows
from counts
where aggregated_maps <> fact_rows
