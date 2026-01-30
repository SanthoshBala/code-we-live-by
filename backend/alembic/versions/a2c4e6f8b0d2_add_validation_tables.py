"""Add validation tables for Task 1.11

Revision ID: a2c4e6f8b0d2
Revises: b151e1b05c53
Create Date: 2026-01-29 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a2c4e6f8b0d2"
down_revision: str = "b151e1b05c53"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add validation tables for ingestion validation system."""
    # Create enums
    parsing_mode = sa.Enum(
        "HUMAN_PLUS_LLM", "LLM", "REGEX", name="parsing_mode", create_type=False
    )
    parsing_mode.create(op.get_bind(), checkfirst=True)

    parsing_session_status = sa.Enum(
        "IN_PROGRESS",
        "COMPLETED",
        "FAILED",
        "ESCALATED",
        name="parsing_session_status",
        create_type=False,
    )
    parsing_session_status.create(op.get_bind(), checkfirst=True)

    span_type = sa.Enum(
        "CLAIMED",
        "UNCLAIMED_FLAGGED",
        "UNCLAIMED_IGNORED",
        name="span_type",
        create_type=False,
    )
    span_type.create(op.get_bind(), checkfirst=True)

    amendment_review_status = sa.Enum(
        "PENDING",
        "APPROVED",
        "REJECTED",
        "CORRECTED",
        name="amendment_review_status",
        create_type=False,
    )
    amendment_review_status.create(op.get_bind(), checkfirst=True)

    pattern_discovery_status = sa.Enum(
        "NEW",
        "UNDER_REVIEW",
        "PROMOTED",
        "REJECTED",
        name="pattern_discovery_status",
        create_type=False,
    )
    pattern_discovery_status.create(op.get_bind(), checkfirst=True)

    # Create parsing_session table
    op.create_table(
        "parsing_session",
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("law_id", sa.Integer(), nullable=False),
        sa.Column("mode", parsing_mode, nullable=False),
        sa.Column("status", parsing_session_status, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("parent_session_id", sa.Integer(), nullable=True),
        sa.Column("escalation_reason", sa.Text(), nullable=True),
        sa.Column("escalated_by", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["law_id"],
            ["public_law.law_id"],
            name=op.f("fk_parsing_session_law_id_public_law"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["parent_session_id"],
            ["parsing_session.session_id"],
            name=op.f("fk_parsing_session_parent_session_id_parsing_session"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("session_id", name=op.f("pk_parsing_session")),
    )
    op.create_index("idx_parsing_session_law", "parsing_session", ["law_id"])
    op.create_index("idx_parsing_session_mode", "parsing_session", ["mode"])
    op.create_index("idx_parsing_session_status", "parsing_session", ["status"])
    op.create_index("idx_parsing_session_started", "parsing_session", ["started_at"])

    # Create parsed_amendment_record table (before text_span for FK)
    op.create_table(
        "parsed_amendment_record",
        sa.Column("record_id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("pattern_name", sa.String(length=100), nullable=False),
        sa.Column("pattern_type", sa.String(length=50), nullable=False),
        sa.Column(
            "change_type",
            sa.Enum(
                "ADD",
                "DELETE",
                "MODIFY",
                "REPEAL",
                "REDESIGNATE",
                "TRANSFER",
                name="change_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("target_title", sa.Integer(), nullable=True),
        sa.Column("target_section", sa.String(length=50), nullable=True),
        sa.Column("target_subsection_path", sa.String(length=100), nullable=True),
        sa.Column("old_text", sa.Text(), nullable=True),
        sa.Column("new_text", sa.Text(), nullable=True),
        sa.Column("start_pos", sa.Integer(), nullable=False),
        sa.Column("end_pos", sa.Integer(), nullable=False),
        sa.Column("full_match_text", sa.Text(), nullable=False),
        sa.Column("context_text", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("needs_review", sa.Boolean(), nullable=False),
        sa.Column("review_status", amendment_review_status, nullable=False),
        sa.Column("reviewed_by", sa.String(length=100), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("corrected_pattern_name", sa.String(length=100), nullable=True),
        sa.Column("corrected_section", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name=op.f("ck_parsed_amendment_record_confidence_range"),
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["parsing_session.session_id"],
            name=op.f("fk_parsed_amendment_record_session_id_parsing_session"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("record_id", name=op.f("pk_parsed_amendment_record")),
    )
    op.create_index(
        "idx_parsed_amendment_session", "parsed_amendment_record", ["session_id"]
    )
    op.create_index(
        "idx_parsed_amendment_pattern", "parsed_amendment_record", ["pattern_name"]
    )
    op.create_index(
        "idx_parsed_amendment_review", "parsed_amendment_record", ["review_status"]
    )
    op.create_index(
        "idx_parsed_amendment_needs_review", "parsed_amendment_record", ["needs_review"]
    )
    op.create_index(
        "idx_parsed_amendment_target",
        "parsed_amendment_record",
        ["target_title", "target_section"],
    )

    # Create text_span table
    op.create_table(
        "text_span",
        sa.Column("span_id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("start_pos", sa.Integer(), nullable=False),
        sa.Column("end_pos", sa.Integer(), nullable=False),
        sa.Column("span_type", span_type, nullable=False),
        sa.Column("amendment_record_id", sa.Integer(), nullable=True),
        sa.Column("pattern_name", sa.String(length=100), nullable=True),
        sa.Column("detected_keywords", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "end_pos > start_pos",
            name=op.f("ck_text_span_valid_range"),
        ),
        sa.CheckConstraint(
            "(span_type = 'CLAIMED' AND pattern_name IS NOT NULL) OR "
            "(span_type != 'CLAIMED')",
            name=op.f("ck_text_span_claimed_has_pattern"),
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["parsing_session.session_id"],
            name=op.f("fk_text_span_session_id_parsing_session"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["amendment_record_id"],
            ["parsed_amendment_record.record_id"],
            name=op.f("fk_text_span_amendment_record_id_parsed_amendment_record"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("span_id", name=op.f("pk_text_span")),
    )
    op.create_index("idx_text_span_session", "text_span", ["session_id"])
    op.create_index("idx_text_span_type", "text_span", ["span_type"])
    op.create_index(
        "idx_text_span_positions",
        "text_span",
        ["session_id", "start_pos", "end_pos"],
    )

    # Create ingestion_report table
    op.create_table(
        "ingestion_report",
        sa.Column("report_id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("law_id", sa.Integer(), nullable=False),
        sa.Column("total_text_length", sa.Integer(), nullable=False),
        sa.Column("claimed_text_length", sa.Integer(), nullable=False),
        sa.Column("coverage_percentage", sa.Float(), nullable=False),
        sa.Column("unclaimed_flagged_count", sa.Integer(), nullable=False),
        sa.Column("unclaimed_ignored_count", sa.Integer(), nullable=False),
        sa.Column("total_amendments", sa.Integer(), nullable=False),
        sa.Column("high_confidence_count", sa.Integer(), nullable=False),
        sa.Column("needs_review_count", sa.Integer(), nullable=False),
        sa.Column("avg_confidence", sa.Float(), nullable=False),
        sa.Column("amendments_by_type", JSONB, nullable=True),
        sa.Column("amendments_by_pattern", JSONB, nullable=True),
        sa.Column("auto_approve_eligible", sa.Boolean(), nullable=False),
        sa.Column("escalation_recommended", sa.Boolean(), nullable=False),
        sa.Column("escalation_reason", sa.Text(), nullable=True),
        sa.Column("govinfo_amendment_count", sa.Integer(), nullable=True),
        sa.Column("amendment_count_mismatch", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "coverage_percentage >= 0 AND coverage_percentage <= 100",
            name=op.f("ck_ingestion_report_coverage_range"),
        ),
        sa.CheckConstraint(
            "avg_confidence >= 0 AND avg_confidence <= 1",
            name=op.f("ck_ingestion_report_confidence_range"),
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["parsing_session.session_id"],
            name=op.f("fk_ingestion_report_session_id_parsing_session"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["law_id"],
            ["public_law.law_id"],
            name=op.f("fk_ingestion_report_law_id_public_law"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("report_id", name=op.f("pk_ingestion_report")),
        sa.UniqueConstraint("session_id", name=op.f("uq_ingestion_report_session_id")),
    )
    op.create_index("idx_ingestion_report_law", "ingestion_report", ["law_id"])
    op.create_index(
        "idx_ingestion_report_coverage", "ingestion_report", ["coverage_percentage"]
    )
    op.create_index(
        "idx_ingestion_report_eligible", "ingestion_report", ["auto_approve_eligible"]
    )

    # Create pattern_discovery table
    op.create_table(
        "pattern_discovery",
        sa.Column("discovery_id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("unmatched_text", sa.Text(), nullable=False),
        sa.Column("detected_keywords", sa.Text(), nullable=True),
        sa.Column("context_text", sa.Text(), nullable=True),
        sa.Column("start_pos", sa.Integer(), nullable=False),
        sa.Column("end_pos", sa.Integer(), nullable=False),
        sa.Column("suggested_pattern_name", sa.String(length=100), nullable=True),
        sa.Column("suggested_pattern_regex", sa.Text(), nullable=True),
        sa.Column("suggested_pattern_type", sa.String(length=50), nullable=True),
        sa.Column("status", pattern_discovery_status, nullable=False),
        sa.Column("reviewed_by", sa.String(length=100), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("promoted_pattern_name", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["parsing_session.session_id"],
            name=op.f("fk_pattern_discovery_session_id_parsing_session"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("discovery_id", name=op.f("pk_pattern_discovery")),
    )
    op.create_index(
        "idx_pattern_discovery_session", "pattern_discovery", ["session_id"]
    )
    op.create_index("idx_pattern_discovery_status", "pattern_discovery", ["status"])

    # Create verification enums
    verification_method = sa.Enum(
        "MANUAL_REVIEW",
        "AUTOMATED_COMPARISON",
        "THIRD_PARTY_AUDIT",
        name="verification_method",
        create_type=False,
    )
    verification_method.create(op.get_bind(), checkfirst=True)

    verification_result = sa.Enum(
        "PASSED",
        "FAILED",
        "PASSED_WITH_ISSUES",
        name="verification_result",
        create_type=False,
    )
    verification_result.create(op.get_bind(), checkfirst=True)

    # Create parsing_verification table
    op.create_table(
        "parsing_verification",
        sa.Column("verification_id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("verified_by", sa.String(length=100), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("method", verification_method, nullable=False),
        sa.Column("result", verification_result, nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("issues_found", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["parsing_session.session_id"],
            name=op.f("fk_parsing_verification_session_id_parsing_session"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "verification_id", name=op.f("pk_parsing_verification")
        ),
    )
    op.create_index(
        "idx_parsing_verification_session", "parsing_verification", ["session_id"]
    )
    op.create_index(
        "idx_parsing_verification_result", "parsing_verification", ["result"]
    )
    op.create_index(
        "idx_parsing_verification_verified_at", "parsing_verification", ["verified_at"]
    )


def downgrade() -> None:
    """Remove validation tables."""
    op.drop_index(
        "idx_parsing_verification_verified_at", table_name="parsing_verification"
    )
    op.drop_index("idx_parsing_verification_result", table_name="parsing_verification")
    op.drop_index("idx_parsing_verification_session", table_name="parsing_verification")
    op.drop_table("parsing_verification")

    # Drop verification enums
    sa.Enum(name="verification_result").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="verification_method").drop(op.get_bind(), checkfirst=True)

    op.drop_index("idx_pattern_discovery_status", table_name="pattern_discovery")
    op.drop_index("idx_pattern_discovery_session", table_name="pattern_discovery")
    op.drop_table("pattern_discovery")

    op.drop_index("idx_ingestion_report_eligible", table_name="ingestion_report")
    op.drop_index("idx_ingestion_report_coverage", table_name="ingestion_report")
    op.drop_index("idx_ingestion_report_law", table_name="ingestion_report")
    op.drop_table("ingestion_report")

    op.drop_index("idx_text_span_positions", table_name="text_span")
    op.drop_index("idx_text_span_type", table_name="text_span")
    op.drop_index("idx_text_span_session", table_name="text_span")
    op.drop_table("text_span")

    op.drop_index("idx_parsed_amendment_target", table_name="parsed_amendment_record")
    op.drop_index(
        "idx_parsed_amendment_needs_review", table_name="parsed_amendment_record"
    )
    op.drop_index("idx_parsed_amendment_review", table_name="parsed_amendment_record")
    op.drop_index("idx_parsed_amendment_pattern", table_name="parsed_amendment_record")
    op.drop_index("idx_parsed_amendment_session", table_name="parsed_amendment_record")
    op.drop_table("parsed_amendment_record")

    op.drop_index("idx_parsing_session_started", table_name="parsing_session")
    op.drop_index("idx_parsing_session_status", table_name="parsing_session")
    op.drop_index("idx_parsing_session_mode", table_name="parsing_session")
    op.drop_index("idx_parsing_session_law", table_name="parsing_session")
    op.drop_table("parsing_session")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS pattern_discovery_status")
    op.execute("DROP TYPE IF EXISTS amendment_review_status")
    op.execute("DROP TYPE IF EXISTS span_type")
    op.execute("DROP TYPE IF EXISTS parsing_session_status")
    op.execute("DROP TYPE IF EXISTS parsing_mode")
