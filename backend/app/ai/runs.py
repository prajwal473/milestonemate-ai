import logging
from datetime import datetime, timezone, timedelta

from app.ai.evaluator import evaluate_deliverable
from app.ai.extraction import extract_text
from app.core.config import settings
from app.db.session import SessionLocal
from app.models import (
    Deliverable,
    Evaluation,
    EvaluationRun,
    Milestone,
    Notification,
    Project,
)
from app.services import audit, notifications

logger = logging.getLogger(__name__)


def _resolve_notification_user_id(
    db, deliverable=None, milestone=None
) -> int | None:
    """Resolve the target user ID for evaluation notifications (client first, then submitter)."""
    try:
        if milestone is not None:
            project = getattr(milestone, "project", None)
            if project is None and getattr(milestone, "project_id", None):
                project = db.get(Project, milestone.project_id)
            if project is not None:
                client_id = getattr(project, "client_id", None)
                if isinstance(client_id, int) and client_id > 0:
                    return client_id
    except Exception:
        pass

    try:
        if deliverable is not None:
            sub_id = getattr(deliverable, "submitted_by_id", None)
            if isinstance(sub_id, int) and sub_id > 0:
                return sub_id
    except Exception:
        pass

    return None


def _notification_already_sent(
    db, user_id: int, event_type: str, deliverable_id: int
) -> bool:
    """Check if an identical notification has already been sent to avoid duplicates on retry."""
    try:
        sent = (
            db.query(Notification)
            .filter(
                Notification.user_id == user_id,
                Notification.event_type == event_type,
            )
            .all()
        )
        for item in sent:
            payload = getattr(item, "payload", None) or {}
            if payload.get("deliverable_id") == deliverable_id:
                return True
    except Exception:
        pass
    return False


def run_evaluation(run_id: int):
    logger.info("run_evaluation started for run_id=%d", run_id)

    db = SessionLocal()

    try:
        run = db.get(EvaluationRun, run_id)

        if run is None:
            logger.warning("EvaluationRun %d not found, aborting.", run_id)
            return

        if run.status in ("COMPLETED", "FAILED"):
            logger.info(
                "EvaluationRun %d already terminal (status=%s), skipping.",
                run_id,
                run.status,
            )
            return

        # ── Atomic claim: only proceed if status is PENDING ──
        # This prevents duplicate or concurrent processing.
        if run.status != "PENDING":
            logger.warning(
                "EvaluationRun %d has unexpected status=%s, skipping.",
                run_id,
                run.status,
            )
            return

        run.status = "RUNNING"
        run.started_at = datetime.now(timezone.utc)
        run.completed_at = None
        run.error_code = None
        db.commit()
        logger.info("EvaluationRun %d claimed, status set to RUNNING.", run_id)

        deliverable = None
        milestone = None

        try:
            deliverable = db.get(Deliverable, run.deliverable_id)

            if deliverable is None:
                raise ValueError("Deliverable not found.")

            milestone = db.get(Milestone, deliverable.milestone_id)

            if milestone is None:
                raise ValueError("Milestone not found.")

            existing = (
                db.query(Evaluation)
                .filter(Evaluation.deliverable_id == deliverable.id)
                .first()
            )

            if existing is not None:
                logger.info(
                    "Evaluation already exists for deliverable %d, "
                    "marking run %d as COMPLETED.",
                    deliverable.id,
                    run_id,
                )
                run.status = "COMPLETED"
                run.completed_at = datetime.now(timezone.utc)
                db.commit()
                return

            # ── Extract file content from deliverable ──
            source_texts = {}
            image_paths = []

            for file_url in deliverable.file_urls or []:
                try:
                    extraction = extract_text(file_url)

                    if not extraction.get("supported"):
                        logger.warning(
                            "Unsupported or failed file extraction: %s — %s",
                            file_url,
                            extraction.get("error", "unsupported format"),
                        )
                        continue

                    if extraction.get("file_type") == "image":
                        image_paths.append(file_url)
                    elif extraction.get("text"):
                        source_texts[extraction["filename"]] = (
                            extraction["text"]
                        )

                except Exception as extract_exc:
                    logger.warning(
                        "Failed to extract text from %s: %s",
                        file_url,
                        extract_exc,
                    )

            logger.info(
                "EvaluationRun %d: extracted %d text sources, "
                "%d images from %d file_urls.",
                run_id,
                len(source_texts),
                len(image_paths),
                len(deliverable.file_urls or []),
            )

            # ── Call the AI evaluator ──
            result = evaluate_deliverable(
                milestone_title=milestone.title,
                milestone_description=milestone.description,
                acceptance_criteria=milestone.acceptance_criteria,
                deliverable_description=deliverable.description,
                source_texts=source_texts,
                image_paths=image_paths,
            )

            evaluation = Evaluation(
                deliverable_id=deliverable.id,
                model_name=(
                    "mock"
                    if settings.ai_mode.lower() == "mock"
                    else settings.gemini_model
                ),
                score=None,
                findings=result,
                recommendation=result["recommendation"],
                human_decision=None,
            )

            db.add(evaluation)

            run.status = "COMPLETED"
            run.completed_at = datetime.now(timezone.utc)
            db.commit()

            logger.info(
                "EvaluationRun %d COMPLETED successfully.", run_id
            )

            # ── Record audit log for successful evaluation ──
            try:
                if (
                    deliverable is not None
                    and isinstance(deliverable.id, int)
                    and deliverable.id > 0
                ):
                    audit.record(
                        db=db,
                        actor_id=None,
                        action="DELIVERABLE_EVALUATED",
                        entity_type="deliverable",
                        entity_id=deliverable.id,
                        details={
                            "run_id": run.id,
                            "evaluation_id": getattr(evaluation, "id", None),
                            "recommendation": result.get("recommendation"),
                            "model_name": getattr(evaluation, "model_name", None),
                        },
                    )
                    db.commit()
            except Exception as audit_exc:
                logger.warning(
                    "EvaluationRun %d: failed to record audit log on success: %s",
                    run_id,
                    audit_exc,
                )
                try:
                    db.rollback()
                except Exception:
                    pass

            # ── Send notification for successful evaluation ──
            try:
                user_id = _resolve_notification_user_id(
                    db, deliverable, milestone
                )
                deliv_id = getattr(deliverable, "id", None)
                if user_id and deliv_id:
                    if not _notification_already_sent(
                        db, user_id, "evaluation.completed", deliv_id
                    ):
                        notifications.notify(
                            db=db,
                            user_id=user_id,
                            event_type="evaluation.completed",
                            payload={
                                "deliverable_id": deliv_id,
                                "run_id": run.id,
                                "status": "COMPLETED",
                                "recommendation": result.get("recommendation"),
                            },
                        )
                        db.commit()
                    else:
                        logger.info(
                            "EvaluationRun %d: skipped duplicate notification for user %d, deliverable %d.",
                            run_id,
                            user_id,
                            deliv_id,
                        )
            except Exception as notify_exc:
                logger.warning(
                    "EvaluationRun %d: failed to send notification on success: %s",
                    run_id,
                    notify_exc,
                )
                try:
                    db.rollback()
                except Exception:
                    pass

        except Exception as exc:
            db.rollback()

            underlying_exc = getattr(exc, "__cause__", None) or exc
            logger.error(
                "EvaluationRun %d failed with %s: %s (underlying %s: %s)",
                run_id,
                type(exc).__name__,
                exc,
                type(underlying_exc).__name__,
                underlying_exc,
                exc_info=True,
            )

            # Re-read the run after rollback to get clean state.
            run = db.get(EvaluationRun, run_id)

            if run is None:
                logger.error(
                    "EvaluationRun %d disappeared after error.", run_id
                )
                return

            run.retry_count += 1
            run.status = "FAILED"
            run.error_code = type(underlying_exc).__name__
            run.completed_at = datetime.now(timezone.utc)
            db.commit()

            logger.info(
                "EvaluationRun %d marked FAILED (retry_count=%d, "
                "error_code=%s).",
                run_id,
                run.retry_count,
                run.error_code,
            )

            # ── Record audit log for failed evaluation ──
            try:
                deliv_id = getattr(run, "deliverable_id", None)
                if deliv_id and isinstance(deliv_id, int) and deliv_id > 0:
                    audit.record(
                        db=db,
                        actor_id=None,
                        action="DELIVERABLE_EVALUATION_FAILED",
                        entity_type="deliverable",
                        entity_id=deliv_id,
                        details={
                            "run_id": run.id,
                            "error_code": run.error_code,
                            "retry_count": run.retry_count,
                        },
                    )
                    db.commit()
            except Exception as audit_exc:
                logger.warning(
                    "EvaluationRun %d: failed to record audit log on failure: %s",
                    run_id,
                    audit_exc,
                )
                try:
                    db.rollback()
                except Exception:
                    pass

            # ── Send notification for failed evaluation ──
            try:
                deliv_id = getattr(run, "deliverable_id", None)
                if deliverable is None and deliv_id:
                    try:
                        deliverable = db.get(Deliverable, deliv_id)
                    except Exception:
                        pass
                user_id = _resolve_notification_user_id(
                    db, deliverable, milestone
                )
                if user_id and deliv_id:
                    if not _notification_already_sent(
                        db, user_id, "evaluation.failed", deliv_id
                    ):
                        notifications.notify(
                            db=db,
                            user_id=user_id,
                            event_type="evaluation.failed",
                            payload={
                                "deliverable_id": deliv_id,
                                "run_id": run.id,
                                "status": "FAILED",
                                "error_code": run.error_code,
                                "message": (
                                    "AI deliverable evaluation could not be "
                                    "completed. You may retry."
                                ),
                            },
                        )
                        db.commit()
                    else:
                        logger.info(
                            "EvaluationRun %d: skipped duplicate failure notification for user %d, deliverable %d.",
                            run_id,
                            user_id,
                            deliv_id,
                        )
            except Exception as notify_exc:
                logger.warning(
                    "EvaluationRun %d: failed to send notification on failure: %s",
                    run_id,
                    notify_exc,
                )
                try:
                    db.rollback()
                except Exception:
                    pass

    except Exception as outer_exc:
        # Last-resort safety: if anything goes wrong outside the
        # inner try/except (e.g. DB errors during the claim phase),
        # make sure we don't leave the run in an unknown state.
        underlying_outer = getattr(outer_exc, "__cause__", None) or outer_exc
        logger.critical(
            "Unexpected error in run_evaluation for run_id=%d: %s: %s",
            run_id,
            type(underlying_outer).__name__,
            underlying_outer,
            exc_info=True,
        )

        try:
            db.rollback()
            run = db.get(EvaluationRun, run_id)

            if run is not None and run.status == "RUNNING":
                run.status = "FAILED"
                run.error_code = type(underlying_outer).__name__
                run.completed_at = datetime.now(timezone.utc)
                db.commit()
                logger.info(
                    "EvaluationRun %d force-marked FAILED after "
                    "outer exception.",
                    run_id,
                )

        except Exception:
            logger.critical(
                "Could not mark run_id=%d as FAILED after outer "
                "exception; reaper will clean it up.",
                run_id,
            )

    finally:
        db.close()


def reap_stuck_runs():
    db = SessionLocal()

    try:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=3)

        stuck_runs = (
            db.query(EvaluationRun)
            .filter(
                EvaluationRun.status == "RUNNING",
                EvaluationRun.started_at < cutoff,
            )
            .all()
        )

        for run in stuck_runs:
            run.status = "FAILED"
            run.error_code = "AI_TIMEOUT"
            run.completed_at = datetime.now(timezone.utc)
            logger.warning(
                "Reaper: marked EvaluationRun %d as FAILED (AI_TIMEOUT).",
                run.id,
            )

        db.commit()

        return len(stuck_runs)

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()
