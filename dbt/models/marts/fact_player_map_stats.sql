-- Fact: player performance at the player-map grain.
--
-- Grain: one row per player per map, keyed by (map_id, player_id).
-- Built directly on the int_match_player_stats intermediate model, which
-- already carries the reusable staging join, so this mart is a clean
-- analytics-facing projection of that enriched player-map dataset.
--
-- Intended consumers: player performance lookups, player map splits, and
-- rating/ADR trend analysis (including the API read paths).

with enriched as (

    select * from {{ ref('int_match_player_stats') }}

),

final as (

    select
        -- keys
        match_id,
        map_id,
        player_id,

        -- identity / context
        player_name,
        team_name,
        event,
        match_date,
        match_winner,
        map_name,
        map_order,
        map_date,
        map_winner,
        map_team1_score,
        map_team2_score,

        -- performance
        kills,
        deaths,
        assists,
        flash_assists,
        headshots,
        opening_kills,
        opening_deaths,
        traded_deaths,
        multi_kills,
        clutches_won,
        kast,
        adr,
        rating,
        kd_diff,
        fk_diff,
        round_swing

    from enriched

)

select * from final
