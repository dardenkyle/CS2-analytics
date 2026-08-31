-- Fact: player performance at the player-map grain.
--
-- Grain: one row per player per map, keyed by (map_id, player_id).
-- Built directly on the int_match_player_stats intermediate model, which
-- already carries the reusable staging join, so this mart is a clean
-- analytics-facing projection of that enriched player-map dataset.
--
-- Intended consumers: player performance lookups, player map splits, and
-- rating/ADR trend analysis (including the API read paths).
--
-- Materialization: incremental on the (map_id, player_id) grain with a
-- delete+insert strategy, filtered on source_updated_at with a lookback
-- window that absorbs late-arriving updates. Run with --full-refresh after
-- logic changes to this model or its upstream, or for backfills; see
-- docs/dbt_models.md (Materialization Strategy).

{{
    config(
        materialized='incremental',
        unique_key=['map_id', 'player_id'],
        incremental_strategy='delete+insert',
        on_schema_change='append_new_columns'
    )
}}

{#-
    The watermark filter only applies when the existing target already has
    source_updated_at. A target built before this column existed (the first
    incremental run over a table created as a plain table) falls back to a
    full reprocess, and on_schema_change adds the column - no manual
    --full-refresh is needed for that transition.
-#}
{% set target_has_watermark = false %}
{% if is_incremental() %}
    {% set target_columns = adapter.get_columns_in_relation(this) | map(attribute='name') | map('lower') | list %}
    {% set target_has_watermark = 'source_updated_at' in target_columns %}
{% endif %}

with enriched as (

    select * from {{ ref('int_match_player_stats') }}

    {% if target_has_watermark %}
    where source_updated_at >= (
        select coalesce(max(source_updated_at), '1970-01-01'::timestamptz)
        from {{ this }}
    ) - interval '3 days'
    {% endif %}

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
        round_swing,

        -- incremental watermark
        source_updated_at

    from enriched

)

select * from final
