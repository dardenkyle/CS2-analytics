-- Staging model for the parsed players source table.
--
-- Grain: one row per player per map, keyed by (map_id, player_id). Thin by
-- design: select, rename, and light casting only. No joins and no business
-- logic. The parsed map_name context column is passed through as-is; downstream
-- models should prefer stg_maps.map_name when a canonical map name is needed.

with source as (

    select * from {{ source('ingestion', 'players') }}

),

renamed as (

    select
        map_id,
        player_id,
        player_name,
        player_url,
        map_name,
        team_name,
        kills,
        headshots,
        assists,
        flash_assists,
        deaths,
        traded_deaths,
        opening_kills,
        opening_deaths,
        multi_kills,
        clutches_won,
        kast,
        kd_diff,
        adr,
        fk_diff,
        round_swing,
        rating,
        last_inserted_at as inserted_at,
        last_scraped_at,
        last_updated_at,
        data_complete

    from source

)

select * from renamed
