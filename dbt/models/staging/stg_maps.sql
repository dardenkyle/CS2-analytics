-- Staging model for the parsed maps source table.
--
-- Grain: one row per map played within a match, keyed by map_id, with a
-- foreign key to matches and a per-match map_order. Thin by design: select,
-- rename, and light casting only. No joins and no business logic.

with source as (

    select * from {{ source('ingestion', 'maps') }}

),

renamed as (

    select
        map_id,
        match_id,
        map_url,
        map_order,
        map_name,
        team1_score,
        team2_score,
        map_winner,
        date,
        inserted_at,
        last_scraped_at,
        last_updated_at,
        data_complete

    from source

)

select * from renamed
