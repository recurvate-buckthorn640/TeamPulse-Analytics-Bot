from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict

from celery import shared_task
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.app.container import get_db_session
from src.db.enums import (
    LLMRunStage,
    LLMRunStatus,
    ReportPeriodType,
    ReportStatus,
)
from src.db.models import LLMRun, Owner, OwnerSettings, Report
from src.llm.analyst import run_analyst
from src.llm.client import LLMClient
from src.llm.finalizer import run_finalizer
from src.llm.schemas import (
    FinalizerInput,
    VerifierFacts,
)
from src.llm.verifier import run_verifier
from src.reporting.assembler import build_analyst_input
from src.reporting.delivery import deliver_report
from src.reporting.audit import write_audit_log
from src.services.report_service import ReportService


@shared_task(name="reporting.build_report", autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def build_report_task(owner_id: int, period_type: str, period_start: str, period_end: str) -> int:
    db: Session = get_db_session()
    try:
        service = ReportService(db)
        report = service.build_report(
            owner_id=owner_id,
            period_type=ReportPeriodType(period_type),
            period_start=date.fromisoformat(period_start),
            period_end=date.fromisoformat(period_end),
        )
        db.commit()
        return report.id
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@shared_task(name="reporting.schedule_reports", autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def schedule_reports() -> None:
    """
    Iterate over owners with settings and enqueue daily and weekly reports.

    This task is intended to be triggered by Celery beat once per day.
    """
    db: Session = get_db_session()
    try:
        today = date.today()
        settings_rows = list(db.execute(select(OwnerSettings)).scalars())
        for owner_settings in settings_rows:
            owner = db.get(Owner, owner_settings.owner_id)
            if owner is None or not owner.is_active:
                continue
            for period_type in (ReportPeriodType.DAILY, ReportPeriodType.WEEKLY):
                build_report_task.delay(
                    owner_id=owner.id,
                    period_type=period_type.value,
                    period_start=today.isoformat(),
                    period_end=today.isoformat(),
                )
    finally:
        db.close()


def _create_llm_run(
    db: Session,
    *,
    report_id: int,
    stage: LLMRunStage,
    status: LLMRunStatus,
    request_payload: Dict[str, Any],
    response_payload: Dict[str, Any] | None = None,
    error_message: str | None = None,
) -> LLMRun:
    from datetime import datetime
    import uuid

    now = datetime.utcnow()
    run = LLMRun(
        report_id=report_id,
        stage=stage,
        status=status,
        request_payload=request_payload,
        response_payload=response_payload,
        error_message=error_message,
        created_at=now,
        updated_at=now,
        correlation_id=str(uuid.uuid4()),
    )
    db.add(run)
    db.flush()
    return run


@shared_task(name="reporting.run_llm_analyst", autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def run_llm_analyst_task(report_id: int) -> None:
    db: Session = get_db_session()
    client = LLMClient()
    try:
        report = db.get(Report, report_id)
        if report is None:
            return
        payload = build_analyst_input(db, report)
        request_dict = payload.model_dump()
        try:
            output = run_analyst(client, payload)
            _create_llm_run(
                db,
                report_id=report.id,
                stage=LLMRunStage.ANALYST,
                status=LLMRunStatus.SUCCESS,
                request_payload=request_dict,
                response_payload=output.model_dump(),
            )
            report.status = ReportStatus.AWAITING_VERIFICATION
        except Exception as exc:  # noqa: BLE001
            _create_llm_run(
                db,
                report_id=report.id,
                stage=LLMRunStage.ANALYST,
                status=LLMRunStatus.FAILED,
                request_payload=request_dict,
                error_message=str(exc),
            )
            report.status = ReportStatus.FAILED
            write_audit_log(
                db,
                event_type="llm_analyst_failed",
                actor_type="system",
                actor_id=None,
                context={"report_id": report.id},
                message="LLM analyst stage failed",
            )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@shared_task(name="reporting.run_llm_verifier", autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def run_llm_verifier_task(report_id: int) -> None:
    db: Session = get_db_session()
    client = LLMClient()
    try:
        report = db.get(Report, report_id)
        if report is None:
            return

        # load the last analyst run
        stmt = (
            select(LLMRun)
            .where(LLMRun.report_id == report.id, LLMRun.stage == LLMRunStage.ANALYST)
            .order_by(LLMRun.id.desc())
        )
        analyst_run = db.execute(stmt).scalar_one_or_none()
        if analyst_run is None or analyst_run.response_payload is None:
            return

        from src.db.models import ProcessSignal

        signals = list(
            db.execute(
                select(ProcessSignal).where(ProcessSignal.owner_id == report.owner_id)
            ).scalars()
        )
        facts = VerifierFacts(
            signals=[
                {
                    "id": str(s.id),
                    "type": s.type.value,
                    "chat_id": str(s.chat_id),
                    "thread_id": str(s.thread_id),
                    "severity": s.severity.value,
                    "evidence": s.evidence or {},
                }
                for s in signals
            ]
        )

        from src.llm.schemas import AnalystOutput

        analyst_output = AnalystOutput.model_validate(analyst_run.response_payload)
        request_payload = {
            "facts": facts.model_dump(),
            "analyst_output": analyst_output.model_dump(),
        }
        try:
            verifier_output = run_verifier(client, facts, analyst_output)
            _create_llm_run(
                db,
                report_id=report.id,
                stage=LLMRunStage.VERIFIER,
                status=LLMRunStatus.SUCCESS,
                request_payload=request_payload,
                response_payload=verifier_output.model_dump(),
            )
            if verifier_output.overall_supported:
                report.status = ReportStatus.VERIFIED
            else:
                report.status = ReportStatus.REJECTED
                report.rejection_reason = (
                    "Verifier marked report as unsupported or inconsistent"
                )
        except Exception as exc:  # noqa: BLE001
            _create_llm_run(
                db,
                report_id=report.id,
                stage=LLMRunStage.VERIFIER,
                status=LLMRunStatus.FAILED,
                request_payload=request_payload,
                error_message=str(exc),
            )
            report.status = ReportStatus.FAILED
            write_audit_log(
                db,
                event_type="llm_verifier_failed",
                actor_type="system",
                actor_id=None,
                context={"report_id": report.id},
                message="LLM verifier stage failed",
            )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@shared_task(name="reporting.run_llm_finalizer", autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def run_llm_finalizer_task(report_id: int) -> None:
    db: Session = get_db_session()
    client = LLMClient()
    try:
        report = db.get(Report, report_id)
        if report is None or report.status != ReportStatus.VERIFIED:
            return

        # load last verifier run
        stmt = (
            select(LLMRun)
            .where(LLMRun.report_id == report.id, LLMRun.stage == LLMRunStage.VERIFIER)
            .order_by(LLMRun.id.desc())
        )
        verifier_run = db.execute(stmt).scalar_one_or_none()
        if verifier_run is None or verifier_run.response_payload is None:
            return

        from src.llm.schemas import VerifierOutput, FinalizerOwner, FinalizerPeriod, FinalizerInput

        verifier_output = VerifierOutput.model_validate(verifier_run.response_payload)
        supported_claim_ids = {
            v.claim_id for v in verifier_output.claims if v.supported
        }

        # load analyst claims to extract supported ones
        analyst_stmt = (
            select(LLMRun)
            .where(LLMRun.report_id == report.id, LLMRun.stage == LLMRunStage.ANALYST)
            .order_by(LLMRun.id.desc())
        )
        analyst_run = db.execute(analyst_stmt).scalar_one_or_none()
        if analyst_run is None or analyst_run.response_payload is None:
            return

        from src.llm.schemas import AnalystOutput, FinalizerSupportedClaim
        from src.db.models import Owner

        analyst_output = AnalystOutput.model_validate(analyst_run.response_payload)
        claims = []
        for c in analyst_output.claims:
            if c.id in supported_claim_ids:
                claims.append(
                    FinalizerSupportedClaim(
                        id=c.id, text=c.text, signal_ids=c.signal_ids
                    )
                )

        owner = db.get(Owner, report.owner_id)
        if owner is None:
            return

        period = FinalizerPeriod(
            type=report.period_type,
            label=f"{report.period_type.value.capitalize()} report",
        )
        fin_input = FinalizerInput(
            report_id=str(report.id),
            owner=FinalizerOwner(display_name=owner.display_name or ""),
            period=period,
            supported_claims=claims,
        )
        request_payload = fin_input.model_dump()
        try:
            fin_output = run_finalizer(client, fin_input)
            _create_llm_run(
                db,
                report_id=report.id,
                stage=LLMRunStage.FINALIZER,
                status=LLMRunStatus.SUCCESS,
                request_payload=request_payload,
                response_payload=fin_output.model_dump(),
            )
        except Exception as exc:  # noqa: BLE001
            _create_llm_run(
                db,
                report_id=report.id,
                stage=LLMRunStage.FINALIZER,
                status=LLMRunStatus.FAILED,
                request_payload=request_payload,
                error_message=str(exc),
            )
            report.status = ReportStatus.FAILED
            write_audit_log(
                db,
                event_type="llm_finalizer_failed",
                actor_type="system",
                actor_id=None,
                context={"report_id": report.id},
                message="LLM finalizer stage failed",
            )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@shared_task(name="reporting.deliver_report", autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def deliver_report_task(report_id: int) -> None:
    db: Session = get_db_session()
    try:
        report = db.get(Report, report_id)
        if report is None:
            return

        if report.status != ReportStatus.VERIFIED:
            # do not deliver rejected or failed reports
            return

        # load finalizer output
        stmt = (
            select(LLMRun)
            .where(LLMRun.report_id == report.id, LLMRun.stage == LLMRunStage.FINALIZER)
            .order_by(LLMRun.id.desc())
        )
        finalizer_run = db.execute(stmt).scalar_one_or_none()
        if finalizer_run is None or finalizer_run.response_payload is None:
            return

        from src.llm.schemas import FinalizerOutput
        from src.db.models import Owner

        final_output = FinalizerOutput.model_validate(finalizer_run.response_payload)
        owner = db.get(Owner, report.owner_id)
        if owner is None:
            return

        deliver_report(db, report=report, owner=owner, text=final_output.text)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

