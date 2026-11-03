-- Aggregate: career rating summary per player.
--
-- Grain: one row per player with at least one row in fact_player_map_stats,
-- keyed by player_id. maps_played counts the player's map rows,
-- rated_maps counts the rows with a non-null rating, and avg_rating is the
-- unrounded mean over the rated rows, so consumers apply their own
-- minimum-maps floor (on rated_maps, the maps the average is built from)
-- and rounding. The mean is taken over numeric rather than float so it is
-- exact and does not depend on summation order; equal averages then stay
-- equal across rebuilds and the tie-breaks apply.
--
-- Intended consumers: the API's top-players leaderboard, which filters on
-- rated_maps and orders by avg_rating, maps_played, then player_id. The
-- aggregate runs once per build instead of once per request.

with player_maps as (

    select
        player_id,
        count(*) as maps_played,
        count(rating) as rated_maps,
        avg(rating::numeric) as avg_rating

    from {{ ref('fact_player_map_stats') }}
    group by player_id

),

final as (

    select
        player_maps.player_id,
        dim_players.player_name,
        player_maps.maps_played,
        player_maps.rated_maps,
        player_maps.avg_rating

    from player_maps
    inner join {{ ref('dim_players') }} as dim_players
        on dim_players.player_id = player_maps.player_id

)

select * from final
