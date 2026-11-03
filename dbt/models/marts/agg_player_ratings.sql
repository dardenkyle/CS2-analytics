-- Aggregate: career rating summary per player.
--
-- Grain: one row per player with at least one row in fact_player_map_stats,
-- keyed by player_id. maps_played counts the player's map rows and
-- avg_rating is the unrounded mean of their per-map rating, so consumers
-- apply their own minimum-maps floor and rounding.
--
-- Intended consumers: the API's top-players leaderboard, which filters on
-- maps_played and orders by avg_rating, maps_played, then player_id. The
-- aggregate runs once per build instead of once per request.

with player_maps as (

    select
        player_id,
        count(*) as maps_played,
        avg(rating) as avg_rating

    from {{ ref('fact_player_map_stats') }}
    group by player_id

),

final as (

    select
        player_maps.player_id,
        dim_players.player_name,
        player_maps.maps_played,
        player_maps.avg_rating

    from player_maps
    inner join {{ ref('dim_players') }} as dim_players
        on dim_players.player_id = player_maps.player_id

)

select * from final
