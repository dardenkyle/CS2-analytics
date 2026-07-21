-- Intermediate model: each player's current team as observed in match data.
--
-- Grain: one row per player, keyed by player_id. The ingestion pipeline does
-- not populate a roster table; the only roster signal is the team a player
-- represented on each map. This model derives "current team" as the team_name
-- from the player's most recent map that recorded a team, so it is the
-- deterministic source relation for the player_roster_history_snapshot SCD2
-- snapshot.
--
-- Determinism: rows persisted in the same batch can share a map_date, so
-- map_id breaks ties. The output depends only on ingested rows, never on
-- run order, so re-running against unchanged sources yields identical rows
-- and cannot corrupt recorded snapshot history.
--
-- Rows with a null player_id or null team_name are excluded: a membership
-- observation needs both sides of the player-team pair.

with player_maps as (

    select * from {{ ref('int_match_player_stats') }}

),

ranked as (

    select
        player_id,
        team_name,
        map_date,
        row_number() over (
            partition by player_id
            order by map_date desc, map_id desc
        ) as recency_rank

    from player_maps
    where player_id is not null
      and team_name is not null

),

final as (

    select
        player_id,
        team_name,
        map_date as observed_map_date

    from ranked
    where recency_rank = 1

)

select * from final
