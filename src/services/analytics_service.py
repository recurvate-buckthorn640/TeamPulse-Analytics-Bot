from datetime import datetime, timezone
from typing import Iterable, List, Sequence

import logging
from sqlalchemy import select
from sqlalchemy.orm import Session
from src.analytics.rules_deadlines import find_missing_deadline_threads
from src.analytics.rules_open_loops import find_open_loops
from src.analytics.rules_ownership import find_missing_owner_threads
from src.analytics.rules_unresolved import find_unresolved_threads
from src.analytics.threading import ThreadSummary
from src.analytics.rules_mentions import find_slow_mentions, MentionEvent
from src.app.config import settings
from src.db.enums import ProcessSignalSeverity, ProcessSignalStatus, ProcessSignalType
from src.db.models import Chat, Message, Mention, Owner, OwnerSettings, ProcessSignal, Thread


logger = logging.getLogger(__name__)


def prioritize_signals(signals: Sequence[ProcessSignal]) -> list[ProcessSignal]:
    """
    Deterministically prioritize process signals for reporting.

    Criteria (in order):
    - Severity (HIGH > MEDIUM > LOW)
    - Type importance (missing owner/deadline, slow mentions, unresolved, open loops, thematic)
    - Direct mention impact (signals linked to direct mentions first, if available)
    - Age / staleness (older last_detected_at first)
    - Stable tie-breaker by id to keep ordering deterministic
    """

    severity_weight = {
        ProcessSignalSeverity.HIGH: 3,
        ProcessSignalSeverity.MEDIUM: 2,
        ProcessSignalSeverity.LOW: 1,
    }

    type_weight = {
        ProcessSignalType.MISSING_OWNER: 5,
        ProcessSignalType.MISSING_DEADLINE: 4,
        ProcessSignalType.SLOW_MENTION_RESPONSE: 3,
        ProcessSignalType.UNRESOLVED_THREAD: 2,
        ProcessSignalType.OPEN_LOOP: 1,
        ProcessSignalType.THEME_PATTERN: 0,
    }

    def sort_key(signal: ProcessSignal) -> tuple:
        sev = severity_weight.get(signal.severity, 0)
        t_weight = type_weight.get(signal.type, 0)

        metadata = signal.metadata or {}
        direct_mention = 1 if metadata.get("direct_mention") else 0

        last_seen_ts = signal.last_detected_at.timestamp()

        return (
            -sev,
            -t_weight,
            -direct_mention,
            -last_seen_ts,
            signal.id or 0,
        )

    return sorted(signals, key=sort_key)


class AnalyticsService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _get_owner_for_chat(self, chat: Chat) -> Owner | None:
        if chat.owner_id is None:
            return None
        return self.db.get(Owner, chat.owner_id)

    def _get_owner_settings(self, owner: Owner) -> OwnerSettings | None:
        stmt = select(OwnerSettings).where(OwnerSettings.owner_id == owner.id)
        return self.db.execute(stmt).scalar_one_or_none()

    def run_for_chat(self, chat_id: int) -> None:
        """
        Run all deterministic analytics for a single chat.
        """

        chat = self.db.get(Chat, chat_id)
        if chat is None:
            return

        owner = self._get_owner_for_chat(chat)
        if owner is None:
            return

        owner_settings = self._get_owner_settings(owner)

        open_loop_threshold_hours = (
            owner_settings.open_loop_threshold_hours if owner_settings else settings.open_loop_threshold_hours
        )
        slow_response_threshold_hours = (
            owner_settings.slow_response_threshold_hours if owner_settings else settings.slow_response_threshold_hours
        )
        min_thread_length_for_unresolved = (
            owner_settings.min_thread_length_for_unresolved if owner_settings else 5
        )
        min_thread_duration_minutes_for_unresolved = (
            owner_settings.min_thread_duration_minutes_for_unresolved if owner_settings else 30
        )

        now = datetime.now(tz=timezone.utc)

        # Load threads for this chat
        threads: list[Thread] = list(
            self.db.execute(select(Thread).where(Thread.chat_id == chat.id)).scalars()
        )

        summaries: list[ThreadSummary] = [
            ThreadSummary(
                root_message_id=t.root_message_id,
                chat_id=t.chat_id,
                started_at=t.started_at,
                last_activity_at=t.last_activity_at,
                message_count=t.message_count,
            )
            for t in threads
        ]

        # Open loops & unresolved
        open_loops = find_open_loops(
            summaries,
            now=now,
            threshold_hours=open_loop_threshold_hours,
        )
        unresolved = find_unresolved_threads(
            summaries,
            min_length=min_thread_length_for_unresolved,
            min_duration_minutes=min_thread_duration_minutes_for_unresolved,
        )

        missing_owner = find_missing_owner_threads(threads)
        missing_deadline = find_missing_deadline_threads(threads, now=now)

        # Mentions: derive simple events from messages and mentions within this chat
        mention_events = self._build_mention_events(chat.id)
        slow_mentions = find_slow_mentions(
            mention_events,
            threshold_hours=slow_response_threshold_hours,
            now=now,
        )

        # Upsert signals
        for s in open_loops:
            thread = self._find_thread_by_root_id(threads, s.root_message_id)
            if thread:
                self._upsert_signal(
                    thread=thread,
                    owner=owner,
                    type_=ProcessSignalType.OPEN_LOOP,
                    severity=ProcessSignalSeverity.MEDIUM,
                    now=now,
                )

        for s in unresolved:
            thread = self._find_thread_by_root_id(threads, s.root_message_id)
            if thread:
                self._upsert_signal(
                    thread=thread,
                    owner=owner,
                    type_=ProcessSignalType.UNRESOLVED_THREAD,
                    severity=ProcessSignalSeverity.MEDIUM,
                    now=now,
                )

        for t in missing_owner:
            self._upsert_signal(
                thread=t,
                owner=owner,
                type_=ProcessSignalType.MISSING_OWNER,
                severity=ProcessSignalSeverity.HIGH,
                now=now,
            )

        for t in missing_deadline:
            self._upsert_signal(
                thread=t,
                owner=owner,
                type_=ProcessSignalType.MISSING_DEADLINE,
                severity=ProcessSignalSeverity.HIGH,
                now=now,
            )

        for ev in slow_mentions:
            thread = self._find_thread_for_mention(threads, ev.chat_id, ev.mention_at)
            if thread:
                self._upsert_signal(
                    thread=thread,
                    owner=owner,
                    type_=ProcessSignalType.SLOW_MENTION_RESPONSE,
                    severity=ProcessSignalSeverity.MEDIUM,
                    now=now,
                )

        logger.info(
            "Analytics run completed",
            extra={
                "chat_id": chat.id,
                "owner_id": owner.id,
                "open_loops": len(open_loops),
                "unresolved": len(unresolved),
                "missing_owner": len(missing_owner),
                "missing_deadline": len(missing_deadline),
                "slow_mentions": len(slow_mentions),
            },
        )

    def _build_mention_events(self, chat_id: int) -> List[MentionEvent]:
        stmt = (
            select(Message, Mention)
            .join(Mention, Mention.message_id == Message.id)
            .where(Message.chat_id == chat_id)
        )
        rows = list(self.db.execute(stmt).all())
        events: list[MentionEvent] = []
        for message, mention in rows:
            events.append(
                MentionEvent(
                    chat_id=chat_id,
                    mentioned_user_id=mention.mentioned_user_id,
                    mention_at=message.sent_at,
                    reply_at=None,
                )
            )
        return events

    def _find_thread_by_root_id(self, threads: Iterable[Thread], root_message_id: int) -> Thread | None:
        for t in threads:
            if t.root_message_id == root_message_id:
                return t
        return None

    def _find_thread_for_mention(
        self,
        threads: Iterable[Thread],
        chat_id: int,
        mention_at: datetime,
    ) -> Thread | None:
        # simple heuristic: thread in same chat where window covers mention time
        candidates: list[Thread] = []
        for t in threads:
            if t.chat_id != chat_id:
                continue
            if t.started_at <= mention_at <= t.last_activity_at:
                candidates.append(t)
        if not candidates:
            return None
        # choose the one with smallest distance to mention_at
        candidates.sort(key=lambda t: abs((t.last_activity_at - mention_at).total_seconds()))
        return candidates[0]

    def _upsert_signal(
        self,
        *,
        thread: Thread,
        owner: Owner,
        type_: ProcessSignalType,
        severity: ProcessSignalSeverity,
        now: datetime,
    ) -> ProcessSignal:
        stmt = select(ProcessSignal).where(
            ProcessSignal.thread_id == thread.id,
            ProcessSignal.type == type_,
        )
        signal = self.db.execute(stmt).scalar_one_or_none()
        if signal is None:
            signal = ProcessSignal(
                thread_id=thread.id,
                chat_id=thread.chat_id,
                owner_id=owner.id,
                type=type_,
                severity=severity,
                status=ProcessSignalStatus.ACTIVE,
                first_detected_at=now,
                last_detected_at=now,
                evidence={},
                metadata={},
            )
            self.db.add(signal)
        else:
            signal.last_detected_at = now
            signal.severity = severity
            signal.status = ProcessSignalStatus.ACTIVE
        self.db.flush()
        return signal

