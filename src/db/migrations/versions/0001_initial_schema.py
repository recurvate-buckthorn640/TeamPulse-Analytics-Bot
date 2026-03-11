from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from src.db.enums import (
    ThreadStatus,
    ProcessSignalType,
    ProcessSignalSeverity,
    ProcessSignalStatus,
    ReportStatus,
    ReportPeriodType,
    LLMRunStage,
    LLMRunStatus,
)

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "owners",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("telegram_user_id", sa.BigInteger, nullable=False, unique=True),
        sa.Column("display_name", sa.Text),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )

    op.create_table(
        "chats",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("telegram_chat_id", sa.BigInteger, nullable=False, unique=True),
        sa.Column("title", sa.Text),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("owner_id", sa.Integer, sa.ForeignKey("owners.id")),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("telegram_user_id", sa.BigInteger, nullable=False, unique=True),
        sa.Column("username", sa.Text),
        sa.Column("display_name", sa.Text),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )

    op.create_table(
        "messages",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("telegram_message_id", sa.BigInteger, nullable=False),
        sa.Column("chat_id", sa.Integer, sa.ForeignKey("chats.id"), nullable=False),
        sa.Column("sender_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("sent_at", sa.DateTime, nullable=False),
        sa.Column("edited_at", sa.DateTime),
        sa.Column("text", sa.Text),
        sa.Column("reply_to_message_id", sa.Integer, sa.ForeignKey("messages.id")),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("raw_payload", sa.JSON),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )
    op.create_unique_constraint("uq_messages_chat_msg", "messages", ["chat_id", "telegram_message_id"])
    op.create_unique_constraint("uq_messages_idempotency_key", "messages", ["idempotency_key"])

    op.create_table(
        "message_edits",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("message_id", sa.Integer, sa.ForeignKey("messages.id"), nullable=False),
        sa.Column("edited_at", sa.DateTime, nullable=False),
        sa.Column("text", sa.Text),
        sa.Column("raw_payload", sa.JSON),
    )

    op.create_table(
        "mentions",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("message_id", sa.Integer, sa.ForeignKey("messages.id"), nullable=False),
        sa.Column("mentioned_user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("offset", sa.Integer),
        sa.Column("length", sa.Integer),
    )

    op.create_table(
        "threads",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("chat_id", sa.Integer, sa.ForeignKey("chats.id"), nullable=False),
        sa.Column("root_message_id", sa.Integer, sa.ForeignKey("messages.id"), nullable=False),
        sa.Column("topic", sa.Text),
        sa.Column("started_at", sa.DateTime, nullable=False),
        sa.Column("last_activity_at", sa.DateTime, nullable=False),
        sa.Column("message_count", sa.Integer, nullable=False),
        sa.Column("status", sa.Enum(ThreadStatus), nullable=False),
        sa.Column("is_task_like", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("has_resolution_marker", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("owner_user_id", sa.Integer, sa.ForeignKey("users.id")),
        sa.Column("deadline_at", sa.DateTime),
    )

    op.create_table(
        "thread_participants",
        sa.Column("thread_id", sa.Integer, sa.ForeignKey("threads.id"), primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), primary_key=True),
    )
    op.create_unique_constraint("uq_thread_participant", "thread_participants", ["thread_id", "user_id"])

    op.create_table(
        "process_signals",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("thread_id", sa.Integer, sa.ForeignKey("threads.id"), nullable=False),
        sa.Column("chat_id", sa.Integer, sa.ForeignKey("chats.id"), nullable=False),
        sa.Column("owner_id", sa.Integer, sa.ForeignKey("owners.id"), nullable=False),
        sa.Column("type", sa.Enum(ProcessSignalType), nullable=False),
        sa.Column("severity", sa.Enum(ProcessSignalSeverity), nullable=False),
        sa.Column("status", sa.Enum(ProcessSignalStatus), nullable=False),
        sa.Column("first_detected_at", sa.DateTime, nullable=False),
        sa.Column("last_detected_at", sa.DateTime, nullable=False),
        sa.Column("evidence", sa.JSON, nullable=False),
        sa.Column("metadata", sa.JSON),
    )

    op.create_table(
        "reports",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("owner_id", sa.Integer, sa.ForeignKey("owners.id"), nullable=False),
        sa.Column("period_type", sa.Enum(ReportPeriodType), nullable=False),
        sa.Column("period_start", sa.Date, nullable=False),
        sa.Column("period_end", sa.Date, nullable=False),
        sa.Column("status", sa.Enum(ReportStatus), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.Column("delivered_at", sa.DateTime),
        sa.Column("rejection_reason", sa.Text),
    )
    op.create_unique_constraint(
        "uq_report_owner_period",
        "reports",
        ["owner_id", "period_type", "period_start", "period_end"],
    )

    op.create_table(
        "report_items",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("report_id", sa.Integer, sa.ForeignKey("reports.id"), nullable=False),
        sa.Column("process_signal_id", sa.Integer, sa.ForeignKey("process_signals.id"), nullable=False),
        sa.Column("chat_id", sa.Integer, sa.ForeignKey("chats.id"), nullable=False),
        sa.Column("position", sa.Integer, nullable=False),
        sa.Column("section", sa.String(length=32), nullable=False),
    )

    op.create_table(
        "llm_runs",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("report_id", sa.Integer, sa.ForeignKey("reports.id"), nullable=False),
        sa.Column("stage", sa.Enum(LLMRunStage), nullable=False),
        sa.Column("status", sa.Enum(LLMRunStatus), nullable=False),
        sa.Column("request_payload", sa.JSON, nullable=False),
        sa.Column("response_payload", sa.JSON),
        sa.Column("error_message", sa.Text),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.Column("correlation_id", sa.String(length=255), nullable=False, unique=True),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("actor_type", sa.String(length=32), nullable=False),
        sa.Column("actor_id", sa.Integer),
        sa.Column("context", sa.JSON),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )

    op.create_table(
        "owner_settings",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("owner_id", sa.Integer, sa.ForeignKey("owners.id"), nullable=False, unique=True),
        sa.Column("open_loop_threshold_hours", sa.Integer, nullable=False),
        sa.Column("slow_response_threshold_hours", sa.Integer, nullable=False),
        sa.Column("min_thread_length_for_unresolved", sa.Integer, nullable=False),
        sa.Column("min_thread_duration_minutes_for_unresolved", sa.Integer, nullable=False),
        sa.Column("retention_raw_messages_days", sa.Integer, nullable=False),
        sa.Column("retention_metrics_days", sa.Integer, nullable=False),
        sa.Column("time_zone", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("owner_settings")
    op.drop_table("audit_logs")
    op.drop_table("llm_runs")
    op.drop_table("report_items")
    op.drop_table("reports")
    op.drop_table("process_signals")
    op.drop_table("thread_participants")
    op.drop_table("threads")
    op.drop_table("mentions")
    op.drop_table("message_edits")
    op.drop_table("messages")
    op.drop_table("users")
    op.drop_table("chats")
    op.drop_table("owners")

