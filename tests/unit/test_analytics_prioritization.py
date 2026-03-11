from datetime import datetime, timedelta, timezone

from src.db.enums import ProcessSignalSeverity, ProcessSignalStatus, ProcessSignalType
from src.db.models import ProcessSignal
from src.services.analytics_service import prioritize_signals


def _make_signal(
    *,
    idx: int,
    type_: ProcessSignalType,
    severity: ProcessSignalSeverity,
    last_detected_offset_hours: int,
    direct_mention: bool = False,
) -> ProcessSignal:
    now = datetime.now(tz=timezone.utc)
    last_detected_at = now - timedelta(hours=last_detected_offset_hours)
    signal = ProcessSignal(
        id=idx,
        thread_id=1,
        chat_id=1,
        owner_id=1,
        type=type_,
        severity=severity,
        status=ProcessSignalStatus.ACTIVE,
        first_detected_at=last_detected_at,
        last_detected_at=last_detected_at,
        evidence={},
        metadata={"direct_mention": direct_mention} if direct_mention else {},
    )
    return signal


def test_prioritize_signals_orders_by_severity_then_type_then_age_and_direct_mention() -> None:
    signals = [
        # lower severity unresolved
        _make_signal(
            idx=1,
            type_=ProcessSignalType.UNRESOLVED_THREAD,
            severity=ProcessSignalSeverity.MEDIUM,
            last_detected_offset_hours=1,
        ),
        # high severity missing owner (should come first)
        _make_signal(
            idx=2,
            type_=ProcessSignalType.MISSING_OWNER,
            severity=ProcessSignalSeverity.HIGH,
            last_detected_offset_hours=5,
        ),
        # high severity missing deadline, but more recent than missing owner
        _make_signal(
            idx=3,
            type_=ProcessSignalType.MISSING_DEADLINE,
            severity=ProcessSignalSeverity.HIGH,
            last_detected_offset_hours=2,
        ),
        # medium severity slow mention with direct mention flag
        _make_signal(
            idx=4,
            type_=ProcessSignalType.SLOW_MENTION_RESPONSE,
            severity=ProcessSignalSeverity.MEDIUM,
            last_detected_offset_hours=3,
            direct_mention=True,
        ),
    ]

    ordered = prioritize_signals(signals)

    # Expect high severity ownership-related first, then other high severity,
    # then direct-mention slow response, then unresolved medium.
    ordered_ids = [s.id for s in ordered]
    assert ordered_ids == [2, 3, 4, 1]

