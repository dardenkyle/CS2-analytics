-- Intermediate model: per-map player stats enriched with map and match context.
--
-- Grain: one row per player per map, keyed by (map_id, player_id) - the same
-- grain as stg_players. This factors the players -> maps -> matches join into
-- one reusable place so downstream marts do not repeat it. Joins and context
-- attachment only; no aggregation and no presentation-shaping.
--
-- The canonical map_name comes from stg_maps; the parsed stg_players.map_name
-- context column is intentionally not carried through (see
-- docs/schema_target_pre_dbt.md).

with players as (

    select * from {{ ref('stg_players') }}

),

maps as (

    select * from {{ ref('stg_maps') }}

),

matches as (

    select * from {{ ref('stg_matches') }}

),

joined as (

    select
        -- keys / grain
        players.map_id,
        players.player_id,
        maps.match_id,

        -- match context
        matches.team1,
        matches.team2,
        matches.match_winner,
        matches.event,
        matches.match_type,
        matches.date as match_date,

        -- map context
        maps.map_order,
        maps.map_name,
        maps.map_winner,
        maps.team1_score as map_team1_score,
        maps.team2_score as map_team2_score,
        maps.date as map_date,

        -- player identity
        players.player_name,
        players.player_url,
        players.team_name,

        -- player performance
        players.kills,
        players.headshots,
        players.assists,
        players.flash_assists,
        players.deaths,
        players.traded_deaths,
        players.opening_kills,
        players.opening_deaths,
        players.multi_kills,
        players.clutches_won,
        players.kast,
        players.kd_diff,
        players.adr,
        players.fk_diff,
        players.round_swing,
        players.rating

    from players
    inner join maps
        on players.map_id = maps.map_id
    inner join matches
        on maps.match_id = matches.match_id

)

select * from joined
