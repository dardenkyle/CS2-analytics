-- Dimension: stable player identity.
--
-- Grain: one row per player, keyed by player_id. The parsed player rows repeat
-- identity fields across every map a player appears on, and a player_name can
-- change over time, so this dimension keeps the most recently persisted
-- identity per player_id (by inserted_at).
--
-- Intended consumers: filtering by player and joining player metadata onto the
-- fact tables.

with players as (

    select * from {{ ref('stg_players') }}

),

ranked as (

    select
        player_id,
        player_name,
        player_url,
        row_number() over (
            partition by player_id
            order by inserted_at desc nulls last
        ) as identity_rank

    from players
    where player_id is not null

),

final as (

    select
        player_id,
        player_name,
        player_url

    from ranked
    where identity_rank = 1

)

select * from final
