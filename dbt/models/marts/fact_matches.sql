-- Fact: clean match-level facts.
--
-- Grain: one row per match, keyed by match_id. Built from stg_matches, with
-- map_count derived from stg_maps and losing_team derived from the winner and
-- the two team names. losing_team is null when the winner is null or does not
-- match either team name, rather than guessing a loser.
--
-- Intended consumers: recent match listings, event-level match analysis, and
-- team performance analysis.

with matches as (

    select * from {{ ref('stg_matches') }}

),

map_counts as (

    select
        match_id,
        count(*) as map_count

    from {{ ref('stg_maps') }}
    group by match_id

),

final as (

    select
        matches.match_id,
        matches.event,
        matches.team1,
        matches.team2,
        matches.score1,
        matches.score2,
        matches.match_winner as winning_team,
        case
            when matches.match_winner = matches.team1 then matches.team2
            when matches.match_winner = matches.team2 then matches.team1
        end as losing_team,
        matches.match_type,
        matches.date as match_date,
        matches.forfeit,
        coalesce(map_counts.map_count, 0) as map_count,
        matches.data_complete

    from matches
    left join map_counts
        on matches.match_id = map_counts.match_id

)

select * from final
