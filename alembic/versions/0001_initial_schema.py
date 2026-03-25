"""Initial schema with all tables and source seed data

Revision ID: 0001
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.Text(), nullable=False, unique=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # --- sources ---
    op.create_table(
        "sources",
        sa.Column("id", sa.SmallInteger(), primary_key=True, autoincrement=True),
        sa.Column("slug", sa.Text(), nullable=False, unique=True),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
    )

    # Seed sources
    op.execute(
        "INSERT INTO sources (slug, display_name, base_url, is_active) VALUES "
        "('otomoto', 'OTOMOTO', 'https://www.otomoto.pl', TRUE)"
    )

    # --- listings ---
    op.create_table(
        "listings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("source_id", sa.SmallInteger(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False, unique=True),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="PLN"),
        sa.Column("location", sa.Text(), nullable=True),
        sa.Column("mileage_km", sa.Integer(), nullable=True),
        sa.Column("year", sa.SmallInteger(), nullable=True),
        sa.Column("fuel_type", sa.String(20), nullable=True),
        sa.Column("brand", sa.String(100), nullable=True),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("raw_data", postgresql.JSONB(), nullable=True),
        sa.Column("first_seen_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("last_seen_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
    )
    op.create_index("ix_listings_source_id", "listings", ["source_id"])
    op.create_index("ix_listings_content_hash", "listings", ["content_hash"])
    op.create_index("ix_listings_brand_model", "listings", ["brand", "model"])
    op.create_index("ix_listings_price", "listings", ["price"])
    op.create_index("ix_listings_year", "listings", ["year"])
    op.create_index("ix_listings_fuel_type", "listings", ["fuel_type"])
    op.create_index("ix_listings_first_seen", "listings", ["first_seen_at"])

    # --- filters ---
    op.create_table(
        "filters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column("brand", sa.String(100), nullable=True),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("price_min", sa.Numeric(12, 2), nullable=True),
        sa.Column("price_max", sa.Numeric(12, 2), nullable=True),
        sa.Column("year_min", sa.SmallInteger(), nullable=True),
        sa.Column("year_max", sa.SmallInteger(), nullable=True),
        sa.Column("mileage_max_km", sa.Integer(), nullable=True),
        sa.Column("fuel_types", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("sources", postgresql.ARRAY(sa.SmallInteger()), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_filters_user_id", "filters", ["user_id"])
    op.create_index(
        "ix_filters_active", "filters", ["is_active"],
        postgresql_where=sa.text("is_active = TRUE")
    )

    # --- notification_log ---
    op.create_table(
        "notification_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("filter_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("listing_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sent_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("status", sa.String(20), nullable=False, server_default="sent"),
        sa.Column("error_msg", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["filter_id"], ["filters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("filter_id", "listing_id", name="uq_notification_log_filter_listing"),
    )
    op.create_index("ix_notification_log_filter_id", "notification_log", ["filter_id"])
    op.create_index("ix_notification_log_listing_id", "notification_log", ["listing_id"])

    # --- scrape_runs ---
    op.create_table(
        "scrape_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("source_id", sa.SmallInteger(), nullable=False),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("finished_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="running"),
        sa.Column("listings_found", sa.Integer(), nullable=True),
        sa.Column("listings_new", sa.Integer(), nullable=True),
        sa.Column("error_msg", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"]),
    )
    op.create_index("ix_scrape_runs_source_id", "scrape_runs", ["source_id"])
    op.create_index("ix_scrape_runs_started", "scrape_runs", ["started_at"])


def downgrade() -> None:
    op.drop_table("scrape_runs")
    op.drop_table("notification_log")
    op.drop_table("filters")
    op.drop_table("listings")
    op.drop_table("sources")
    op.drop_table("users")
