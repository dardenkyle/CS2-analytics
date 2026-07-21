-- Dimension: SCD2 player-to-team roster membership history.
--
-- Grain: one row per player-team membership interval, keyed by
-- (player_id, valid_from) with roster_history_key as the surrogate key for
-- downstream joins. Presentation shaping over the
-- player_roster_history_snapshot SCD2 snapshot only: rename the dbt-managed
-- validity columns, add the surrogate key, and flag the current interval.
-- Player identity fields stay in dim_players; consumers join on player_id
-- rather than duplicating them here.
--
-- Point-in-time usage (roster as-of a date): filter
-- valid_from <= :as_of and (valid_to > :as_of or valid_to is null).

with roster_history as (

    select * from {{ ref('player_roster_history_snapshot') }}

),

final as (

    select
        {{ dbt_utils.generate_surrogate_key(['player_id', 'dbt_valid_from']) }}
            as roster_history_key,
        player_id,
        team_name,
        observed_map_date,
        dbt_valid_from as valid_from,
        dbt_valid_to as valid_to,
        dbt_valid_to is null as is_current

    from roster_history

)

select * from final
