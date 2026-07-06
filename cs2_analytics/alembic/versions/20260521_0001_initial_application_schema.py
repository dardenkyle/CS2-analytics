"""Create initial application source schema.

Revision ID: 20260521_0001
Revises:
Create Date: 2026-05-21
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260521_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "teams",
        sa.Column("team_id", sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column("team_name", sa.Text(), nullable=False),
        sa.Column("team_url", sa.Text(), nullable=False),
        sa.Column("region", sa.Text()),
        sa.Column(
            "created_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column("last_scraped_at", sa.TIMESTAMP()),
        sa.Column("last_updated_at", sa.TIMESTAMP()),
        sa.Column("data_complete", sa.Boolean()),
    )
    op.create_table(
        "player_info",
        sa.Column("player_id", sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column("player_name", sa.Text(), nullable=False),
        sa.Column("player_url", sa.Text(), nullable=False),
        sa.Column(
            "team_id", sa.Integer(), sa.ForeignKey("teams.team_id", ondelete="SET NULL")
        ),
        sa.Column("active", sa.Boolean(), server_default=sa.text("TRUE")),
        sa.Column(
            "created_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column("last_scraped_at", sa.TIMESTAMP()),
        sa.Column("last_updated_at", sa.TIMESTAMP()),
        sa.Column("data_complete", sa.Boolean()),
    )
    op.create_table(
        "matches",
        sa.Column("match_id", sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column("match_url", sa.Text(), nullable=False, unique=True),
        sa.Column("map_links", sa.Text()),
        sa.Column("demo_links", sa.Text()),
        sa.Column("team1", sa.Text(), nullable=False),
        sa.Column("team2", sa.Text(), nullable=False),
        sa.Column("score1", sa.Integer()),
        sa.Column("score2", sa.Integer()),
        sa.Column("winner", sa.Text(), nullable=False),
        sa.Column("event", sa.Text()),
        sa.Column("match_type", sa.Text()),
        sa.Column("forfeit", sa.Boolean(), server_default=sa.text("FALSE")),
        sa.Column("date", sa.TIMESTAMP(), nullable=False),
        sa.Column(
            "last_inserted_at",
            sa.TIMESTAMP(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("last_scraped_at", sa.TIMESTAMP()),
        sa.Column("last_updated_at", sa.TIMESTAMP()),
        sa.Column("data_complete", sa.Boolean()),
        sa.CheckConstraint("score1 >= 0"),
        sa.CheckConstraint("score2 >= 0"),
        sa.CheckConstraint("winner = team1 OR winner = team2"),
    )
    op.create_table(
        "maps",
        sa.Column("map_id", sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column(
            "match_id",
            sa.Integer(),
            sa.ForeignKey("matches.match_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("map_url", sa.Text(), nullable=False, unique=True),
        sa.Column("map_order", sa.Integer(), nullable=False),
        sa.Column("map_name", sa.Text(), nullable=False),
        sa.Column("team1_score", sa.Integer(), nullable=False),
        sa.Column("team2_score", sa.Integer(), nullable=False),
        sa.Column("map_winner", sa.Text(), nullable=False),
        sa.Column("date", sa.TIMESTAMP(), nullable=False),
        sa.Column(
            "inserted_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("last_scraped_at", sa.TIMESTAMP(timezone=True)),
        sa.Column("last_updated_at", sa.TIMESTAMP(timezone=True)),
        sa.Column(
            "data_complete",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
        sa.CheckConstraint("map_order BETWEEN 1 AND 5"),
        sa.CheckConstraint("team1_score >= 0"),
        sa.CheckConstraint("team2_score >= 0"),
        sa.UniqueConstraint("match_id", "map_order"),
    )
    op.create_table(
        "players",
        sa.Column(
            "map_id",
            sa.Integer(),
            sa.ForeignKey("maps.map_id", ondelete="CASCADE"),
            primary_key=True,
            autoincrement=False,
        ),
        sa.Column("player_id", sa.Integer(), primary_key=True),
        sa.Column("player_name", sa.Text(), nullable=False),
        sa.Column("player_url", sa.Text()),
        sa.Column("map_name", sa.Text(), nullable=False),
        sa.Column("team_name", sa.Text()),
        sa.Column("kills", sa.Integer()),
        sa.Column("headshots", sa.Integer()),
        sa.Column("assists", sa.Integer()),
        sa.Column("flash_assists", sa.Integer()),
        sa.Column("deaths", sa.Integer()),
        sa.Column("traded_deaths", sa.Integer()),
        sa.Column("opening_kills", sa.Integer()),
        sa.Column("opening_deaths", sa.Integer()),
        sa.Column("multi_kills", sa.Integer()),
        sa.Column("clutches_won", sa.Integer()),
        sa.Column("kast", sa.Float()),
        sa.Column("kd_diff", sa.Integer()),
        sa.Column("adr", sa.Float()),
        sa.Column("fk_diff", sa.Integer()),
        sa.Column("round_swing", sa.Float()),
        sa.Column("rating", sa.Float()),
        sa.Column(
            "last_inserted_at",
            sa.TIMESTAMP(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("last_scraped_at", sa.TIMESTAMP()),
        sa.Column("last_updated_at", sa.TIMESTAMP()),
        sa.Column("data_complete", sa.Boolean(), server_default=sa.text("TRUE")),
    )
    op.create_table(
        "player_team_history",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "player_id",
            sa.Integer(),
            sa.ForeignKey("player_info.player_id", ondelete="CASCADE"),
        ),
        sa.Column("player_name", sa.Text(), nullable=False),
        sa.Column(
            "team_id", sa.Integer(), sa.ForeignKey("teams.team_id", ondelete="SET NULL")
        ),
        sa.Column("team_name", sa.Text(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date()),
        sa.Column(
            "last_inserted_at",
            sa.TIMESTAMP(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint("player_id", "team_id", "start_date"),
    )
    op.create_table(
        "player_aliases",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "player_id",
            sa.Integer(),
            sa.ForeignKey("player_info.player_id", ondelete="CASCADE"),
        ),
        sa.Column("alias", sa.Text(), nullable=False),
        sa.Column(
            "changed_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP")
        ),
    )
    op.create_table(
        "player_transfers",
        sa.Column("transfer_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "player_id",
            sa.Integer(),
            sa.ForeignKey("player_info.player_id", ondelete="CASCADE"),
        ),
        sa.Column("player_name", sa.Text(), nullable=False),
        sa.Column(
            "old_team_id",
            sa.Integer(),
            sa.ForeignKey("teams.team_id", ondelete="SET NULL"),
        ),
        sa.Column("old_team_name", sa.Text(), nullable=False),
        sa.Column(
            "new_team_id",
            sa.Integer(),
            sa.ForeignKey("teams.team_id", ondelete="SET NULL"),
        ),
        sa.Column("new_team_name", sa.Text(), nullable=False),
        sa.Column("transfer_date", sa.Date(), nullable=False),
    )
    op.create_table(
        "match_ingestion_state",
        sa.Column("match_id", sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column("match_url", sa.Text(), nullable=False),
        sa.Column(
            "status", sa.Text(), nullable=False, server_default=sa.text("'pending'")
        ),
        sa.Column(
            "first_seen_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column(
            "last_seen_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column("last_attempted_at", sa.TIMESTAMP()),
        sa.Column("last_processed_at", sa.TIMESTAMP()),
        sa.Column("last_failed_at", sa.TIMESTAMP()),
        sa.Column(
            "failure_count", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("last_error_message", sa.Text()),
        sa.Column("source", sa.Text()),
        sa.Column("priority", sa.Integer(), server_default=sa.text("0")),
        sa.Column(
            "last_updated_at",
            sa.TIMESTAMP(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'processed', 'failed', 'skipped')"
        ),
    )
    op.create_table(
        "map_ingestion_state",
        sa.Column("map_id", sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column("map_url", sa.Text(), nullable=False),
        sa.Column(
            "match_id",
            sa.Integer(),
            sa.ForeignKey("matches.match_id", ondelete="CASCADE"),
        ),
        sa.Column("map_order", sa.Integer()),
        sa.Column(
            "status", sa.Text(), nullable=False, server_default=sa.text("'pending'")
        ),
        sa.Column(
            "first_seen_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column(
            "last_seen_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column("last_attempted_at", sa.TIMESTAMP()),
        sa.Column("last_processed_at", sa.TIMESTAMP()),
        sa.Column("last_failed_at", sa.TIMESTAMP()),
        sa.Column(
            "failure_count", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("last_error_message", sa.Text()),
        sa.Column("source", sa.Text()),
        sa.Column("priority", sa.Integer(), server_default=sa.text("0")),
        sa.Column(
            "last_updated_at",
            sa.TIMESTAMP(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint("map_order BETWEEN 1 AND 5"),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'processed', 'failed', 'skipped')"
        ),
    )
    op.create_table(
        "demo_ingestion_state",
        sa.Column("demo_id", sa.Text(), primary_key=True),
        sa.Column("demo_url", sa.Text(), nullable=False),
        sa.Column(
            "status", sa.Text(), nullable=False, server_default=sa.text("'pending'")
        ),
        sa.Column(
            "first_seen_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column(
            "last_seen_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column("last_attempted_at", sa.TIMESTAMP()),
        sa.Column("last_processed_at", sa.TIMESTAMP()),
        sa.Column("last_failed_at", sa.TIMESTAMP()),
        sa.Column(
            "failure_count", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("last_error_message", sa.Text()),
        sa.Column("source", sa.Text()),
        sa.Column("priority", sa.Integer(), server_default=sa.text("0")),
        sa.Column(
            "last_updated_at",
            sa.TIMESTAMP(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'processed', 'failed', 'skipped')"
        ),
    )
    op.create_table(
        "demo_files",
        sa.Column(
            "map_id",
            sa.Integer(),
            sa.ForeignKey("maps.map_id", ondelete="CASCADE"),
            primary_key=True,
            autoincrement=False,
        ),
        sa.Column("demo_url", sa.Text(), nullable=False),
        sa.Column("local_path", sa.Text()),
        sa.Column("parsed", sa.Boolean(), server_default=sa.text("FALSE")),
        sa.Column("heatmap_done", sa.Boolean(), server_default=sa.text("FALSE")),
        sa.Column(
            "grenade_analysis_done", sa.Boolean(), server_default=sa.text("FALSE")
        ),
        sa.Column(
            "last_inserted_at",
            sa.TIMESTAMP(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("last_processed_at", sa.TIMESTAMP()),
    )
    op.create_table(
        "scrape_runs",
        sa.Column("run_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "started_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP")
        ),
        sa.Column("ended_at", sa.TIMESTAMP()),
        sa.Column("total_matches", sa.Integer()),
        sa.Column("matches_success", sa.Integer()),
        sa.Column("matches_failed", sa.Integer()),
        sa.Column("notes", sa.Text()),
    )
    op.create_table(
        "player_metrics",
        sa.Column("player_id", sa.Integer(), primary_key=True),
        sa.Column("map_name", sa.Text(), primary_key=True),
        sa.Column("average_kills", sa.Float()),
        sa.Column("entry_rating", sa.Float()),
        sa.Column("clutch_success_rate", sa.Float()),
        sa.Column("matches_played", sa.Integer()),
        sa.Column("last_updated_at", sa.TIMESTAMP()),
    )

    op.create_index("idx_matches_date", "matches", ["date"])
    op.create_index("idx_maps_match_id", "maps", ["match_id"])
    op.create_index("idx_players_map_id", "players", ["map_id"])
    op.create_index("idx_players_player_id", "players", ["player_id"])
    op.create_index("idx_players_team_name", "players", ["team_name"])
    op.create_index("idx_player_stats", "players", ["player_id", "map_id"])
    op.create_index("idx_player_info_team_id", "player_info", ["team_id"])
    op.create_index("idx_player_transfers_player_id", "player_transfers", ["player_id"])
    op.create_index(
        "idx_player_team_history_player_id", "player_team_history", ["player_id"]
    )
    op.execute(
        "CREATE INDEX idx_match_ingestion_state_pending "
        "ON match_ingestion_state (status, priority DESC, first_seen_at)"
    )
    op.execute(
        "CREATE INDEX idx_map_ingestion_state_pending "
        "ON map_ingestion_state (status, priority DESC, first_seen_at)"
    )
    op.execute(
        "CREATE INDEX idx_demo_ingestion_state_pending "
        "ON demo_ingestion_state (status, priority DESC, first_seen_at)"
    )


def downgrade() -> None:
    for index_name in (
        "idx_demo_ingestion_state_pending",
        "idx_map_ingestion_state_pending",
        "idx_match_ingestion_state_pending",
        "idx_player_team_history_player_id",
        "idx_player_transfers_player_id",
        "idx_player_info_team_id",
        "idx_player_stats",
        "idx_players_team_name",
        "idx_players_player_id",
        "idx_players_map_id",
        "idx_maps_match_id",
        "idx_matches_date",
    ):
        op.drop_index(index_name)

    for table_name in (
        "player_metrics",
        "scrape_runs",
        "demo_files",
        "demo_ingestion_state",
        "map_ingestion_state",
        "match_ingestion_state",
        "player_transfers",
        "player_aliases",
        "player_team_history",
        "players",
        "maps",
        "matches",
        "player_info",
        "teams",
    ):
        op.drop_table(table_name)
