from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from src.db.base import Base
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


class Chat(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, index=True)
    telegram_chat_id = Column(BigInteger, unique=True, nullable=False)
    title = Column(Text)
    type = Column(String(32), nullable=False)
    owner_id = Column(Integer, ForeignKey("owners.id"))
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    owner = relationship("Owner", back_populates="chats")
    messages = relationship("Message", back_populates="chat")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_user_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(Text, nullable=True)
    display_name = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class Owner(Base):
    __tablename__ = "owners"

    id = Column(Integer, primary_key=True, index=True)
    telegram_user_id = Column(BigInteger, unique=True, nullable=False)
    display_name = Column(Text)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    chats = relationship("Chat", back_populates="owner")


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("chat_id", "telegram_message_id", name="uq_messages_chat_msg"),
        UniqueConstraint("idempotency_key", name="uq_messages_idempotency_key"),
    )

    id = Column(Integer, primary_key=True, index=True)
    telegram_message_id = Column(BigInteger, nullable=False)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    sent_at = Column(DateTime, nullable=False)
    edited_at = Column(DateTime, nullable=True)
    text = Column(Text, nullable=True)
    reply_to_message_id = Column(Integer, ForeignKey("messages.id"), nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)
    idempotency_key = Column(String(255), nullable=False)
    raw_payload = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    chat = relationship("Chat", back_populates="messages", foreign_keys=[chat_id])
    sender = relationship("User", foreign_keys=[sender_id])
    reply_to_message = relationship("Message", remote_side=[id])


class MessageEdit(Base):
    __tablename__ = "message_edits"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False)
    edited_at = Column(DateTime, nullable=False)
    text = Column(Text, nullable=True)
    raw_payload = Column(JSON, nullable=True)


class Mention(Base):
    __tablename__ = "mentions"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False)
    mentioned_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    offset = Column(Integer, nullable=True)
    length = Column(Integer, nullable=True)


class Thread(Base):
    __tablename__ = "threads"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    root_message_id = Column(Integer, ForeignKey("messages.id"), nullable=False)
    topic = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=False)
    last_activity_at = Column(DateTime, nullable=False)
    message_count = Column(Integer, nullable=False)
    status = Column(Enum(ThreadStatus), nullable=False)
    is_task_like = Column(Boolean, default=False, nullable=False)
    has_resolution_marker = Column(Boolean, default=False, nullable=False)
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    deadline_at = Column(DateTime, nullable=True)


class ThreadParticipant(Base):
    __tablename__ = "thread_participants"
    __table_args__ = (
        UniqueConstraint("thread_id", "user_id", name="uq_thread_participant"),
    )

    thread_id = Column(Integer, ForeignKey("threads.id"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)


class ProcessSignal(Base):
    __tablename__ = "process_signals"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(Integer, ForeignKey("threads.id"), nullable=False)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    owner_id = Column(Integer, ForeignKey("owners.id"), nullable=False)
    type = Column(Enum(ProcessSignalType), nullable=False)
    severity = Column(Enum(ProcessSignalSeverity), nullable=False)
    status = Column(Enum(ProcessSignalStatus), nullable=False)
    first_detected_at = Column(DateTime, nullable=False)
    last_detected_at = Column(DateTime, nullable=False)
    evidence = Column(JSON, nullable=False)
    metadata = Column(JSON, nullable=True)


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (
        UniqueConstraint(
            "owner_id",
            "period_type",
            "period_start",
            "period_end",
            name="uq_report_owner_period",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("owners.id"), nullable=False)
    period_type = Column(Enum(ReportPeriodType), nullable=False)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    status = Column(Enum(ReportStatus), nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    delivered_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)


class ReportItem(Base):
    __tablename__ = "report_items"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False)
    process_signal_id = Column(Integer, ForeignKey("process_signals.id"), nullable=False)
    chat_id = Column(Integer, ForeignKey("chats.id"), nullable=False)
    position = Column(Integer, nullable=False)
    section = Column(String(32), nullable=False)


class LLMRun(Base):
    __tablename__ = "llm_runs"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False)
    stage = Column(Enum(LLMRunStage), nullable=False)
    status = Column(Enum(LLMRunStatus), nullable=False)
    request_payload = Column(JSON, nullable=False)
    response_payload = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    correlation_id = Column(String(255), unique=True, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(64), nullable=False)
    actor_type = Column(String(32), nullable=False)
    actor_id = Column(Integer, nullable=True)
    context = Column(JSON, nullable=True)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False)


class OwnerSettings(Base):
    __tablename__ = "owner_settings"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("owners.id"), unique=True, nullable=False)
    open_loop_threshold_hours = Column(Integer, nullable=False)
    slow_response_threshold_hours = Column(Integer, nullable=False)
    min_thread_length_for_unresolved = Column(Integer, nullable=False)
    min_thread_duration_minutes_for_unresolved = Column(Integer, nullable=False)
    retention_raw_messages_days = Column(Integer, nullable=False)
    retention_metrics_days = Column(Integer, nullable=False)
    time_zone = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

