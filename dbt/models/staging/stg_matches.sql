-- Staging model for the parsed matches source table.
--
-- Grain: one row per professional match, keyed by match_id.
-- Thin by design: select, rename, and light casting only. No joins and no
-- business logic. The stringified trace/debug columns map_links and demo_links
-- are intentionally dropped; relationship-ready downstream models use
-- stg_maps.match_id rather than parsing those source fields.

with source as (

    select * from {{ source('ingestion', 'matches') }}

),

renamed as (

    select
        match_id,
        match_url,
        team1,
        team2,
        score1,
        score2,
        winner as match_winner,
        event,
        match_type,
        forfeit,
        date,
        last_inserted_at as inserted_at,
        last_scraped_at,
        last_updated_at,
        data_complete

    from source

)

select * from renamed
