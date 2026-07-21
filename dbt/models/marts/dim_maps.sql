-- Dimension: unique map catalog.
--
-- Grain: one row per distinct map name. Sourced from the map names present in
-- stg_maps. Additional map attributes (active-pool flag, map group) are
-- deferred until they are derivable.
--
-- Intended consumers: map-based filtering and analytics.

with maps as (

    select * from {{ ref('stg_maps') }}

),

final as (

    select distinct
        map_name

    from maps
    where map_name is not null

)

select * from final
