import logging
import re
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import HTTPException, Request, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.timeutil import as_utc, utcnow
from app.models import Report, ReportFormat, ReportStatus, Sensor, SensorReading, User, UserRole
from app.schemas.common import PageParams, paginate
from app.schemas.report import ReportCreate, ReportQuery
from app.services.activity import log_activity
from app.services.analytics import downsample, summarize, violation
from app.services.email import send_report_ready_email
from app.services.report_render import ReadingRow, ReportData, SensorStat, render_csv, render_pdf
from app.services.schedule import default_window_hours, next_run, period
from app.services.sensor_service import visible_sensors

logger = logging.getLogger(__name__)

MAX_DETAIL_ROWS = 50_000


# ---------------------------------------------------------------- files
def reports_dir() -> Path:
    path = Path(settings.REPORTS_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


def file_for(report: Report) -> Path | None:
    """The report's file, or None. Refuses anything that would point outside the reports folder."""
    if not report.file_path or Path(report.file_path).name != report.file_path:
        return None
    base = reports_dir().resolve()
    path = (base / report.file_path).resolve()
    return path if base in path.parents else None


def _remove_file(report: Report) -> None:
    path = file_for(report)
    if path is not None:
        path.unlink(missing_ok=True)


def download_name(report: Report) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", report.name).strip("-")[:60] or "report"
    return f"{slug}-{report.created_at:%Y%m%d}.{report.format.value}"


# ---------------------------------------------------------------- read
def get_visible_report(db: Session, user: User, report_id: int) -> Report:
    report = db.get(Report, report_id)
    if report is None or (user.role == UserRole.user and report.user_id != user.id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    return report


def list_reports(db: Session, user: User, params: PageParams, scheduled: bool | None) -> dict:
    stmt = select(Report)
    if user.role == UserRole.user:
        stmt = stmt.where(Report.user_id == user.id)
    if scheduled is not None:
        stmt = stmt.where(Report.scheduled.is_(scheduled))
    return paginate(db, stmt.order_by(Report.id.desc()), params)


# ---------------------------------------------------------------- create / delete
def _new_run(db: Session, template: Report, now: datetime) -> Report:
    params = {k: v for k, v in template.query_params.items() if k != "schedule"}
    run = Report(
        user_id=template.user_id,
        name=f"{template.name} - {now:%Y-%m-%d %H:%M}",
        query_params=params,
        format=template.format,
        status=ReportStatus.pending,
        scheduled=False,
        source_id=template.id,
        expires_at=now + timedelta(days=settings.REPORTS_RETENTION_DAYS),
    )
    db.add(run)
    db.flush()
    return run


def create_report(db: Session, user: User, data: ReportCreate, request: Request | None = None) -> tuple[Report, list[int]]:
    """Returns (report, ids of reports that still have to be generated in the background)."""
    now = utcnow()
    params = data.query_params.model_dump(by_alias=True, mode="json", exclude_none=True)

    if data.scheduled:
        frequency = data.schedule.frequency
        params.setdefault("window_hours", default_window_hours(frequency))
        params["schedule"] = data.schedule.model_dump(mode="json")
        definition = Report(user_id=user.id, name=data.name, query_params=params, format=data.format,
                            status=ReportStatus.ready, scheduled=True, next_run_at=next_run(now, frequency))
        db.add(definition)
        db.flush()
        first_run = _new_run(db, definition, now)  # so the user sees a result straight away
        db.commit()
        db.refresh(definition)
        log_activity(db, "report.schedule", user_id=user.id, entity_type="report", entity_id=definition.id,
                     details={"frequency": frequency}, request=request)
        return definition, [first_run.id]

    report = Report(user_id=user.id, name=data.name, query_params=params, format=data.format, status=ReportStatus.pending,
                    scheduled=False, expires_at=now + timedelta(days=settings.REPORTS_RETENTION_DAYS))
    db.add(report)
    db.commit()
    db.refresh(report)
    log_activity(db, "report.create", user_id=user.id, entity_type="report", entity_id=report.id,
                 details={"format": data.format.value, "template": data.query_params.template}, request=request)
    return report, [report.id]


def delete_report(db: Session, user: User, report: Report, request: Request | None = None) -> None:
    _remove_file(report)
    report_id = report.id
    db.delete(report)
    db.commit()
    log_activity(db, "report.delete", user_id=user.id, entity_type="report", entity_id=report_id, request=request)


# ---------------------------------------------------------------- build the data
def collect_data(db: Session, user: User, name: str, query: ReportQuery, now: datetime) -> ReportData:
    end = as_utc(query.to) if query.to else now
    start = as_utc(query.from_) if query.from_ else end - timedelta(hours=query.window_hours or 24)

    stmt = visible_sensors(user)  # a report never contains sensors its owner may not see
    filters: list[str] = []
    if query.sensor_ids:
        stmt = stmt.where(Sensor.id.in_(query.sensor_ids))
        filters.append(f"{len(query.sensor_ids)} sensor(s) selected")
    if query.category:
        stmt = stmt.where(Sensor.category == query.category)
        filters.append(f"Category: {query.category.value}")
    sensors = list(db.scalars(stmt.order_by(Sensor.title, Sensor.id).limit(settings.MAX_REPORT_SENSORS + 1)))
    truncated = len(sensors) > settings.MAX_REPORT_SENSORS
    sensors = sensors[: settings.MAX_REPORT_SENSORS]

    by_sensor: dict[int, list[tuple[datetime, float]]] = defaultdict(list)
    if sensors:
        rows = db.execute(
            select(SensorReading.sensor_id, SensorReading.recorded_at, SensorReading.value)
            .where(SensorReading.sensor_id.in_([s.id for s in sensors]),
                   SensorReading.recorded_at >= start, SensorReading.recorded_at <= end)
            .order_by(SensorReading.sensor_id, SensorReading.recorded_at)
            .limit(settings.MAX_REPORT_READINGS + 1)
        ).all()
        if len(rows) > settings.MAX_REPORT_READINGS:
            truncated = True
            rows = rows[: settings.MAX_REPORT_READINGS]
        for sensor_id, ts, value in rows:
            by_sensor[sensor_id].append((as_utc(ts), value))

    stats: list[SensorStat] = []
    detail: list[ReadingRow] = []
    for sensor in sensors:
        meta = sensor.meta or {}
        unit, thresholds = meta.get("unit") or "", meta.get("thresholds")
        readings = by_sensor.get(sensor.id, [])
        values = [v for _, v in readings]
        summary = summarize(values)
        alerts = 0
        for ts, value in readings:
            flag = violation(value, thresholds)
            alerts += flag is not None
            if query.template == "detailed" or (query.template == "alerts" and flag):
                if len(detail) < MAX_DETAIL_ROWS:
                    detail.append(ReadingRow(sensor.id, sensor.title, sensor.category.value, unit, ts, value, flag))
                else:
                    truncated = True
        stats.append(SensorStat(
            sensor_id=sensor.id, title=sensor.title, category=sensor.category.value, status=sensor.status.value, unit=unit,
            count=len(values), minimum=summary["min"] if summary else None, mean=summary["mean"] if summary else None,
            maximum=summary["max"] if summary else None, last=summary["last"] if summary else None,
            alerts=alerts, trend=downsample(values),
        ))

    return ReportData(name=name, template=query.template, generated_at=now, range_from=start, range_to=end,
                      filters=filters, sensors=stats, rows=detail, truncated=truncated)


# ---------------------------------------------------------------- generate (runs in the background)
def generate_report(session_factory, report_id: int) -> bool:
    """Build the file for a pending report. Opens its own DB session. Returns True on success."""
    with session_factory() as db:
        report = db.get(Report, report_id)
        if report is None or report.status != ReportStatus.pending:
            return False
        try:
            owner = db.get(User, report.user_id)
            query = ReportQuery.model_validate(report.query_params)
            data = collect_data(db, owner, report.name, query, utcnow())
            ext = report.format.value
            content = render_pdf(data) if report.format == ReportFormat.pdf else render_csv(data)
            filename = f"{report.id}-{uuid.uuid4().hex[:8]}.{ext}"
            (reports_dir() / filename).write_bytes(content)
            report.file_path = filename
            report.status = ReportStatus.ready
            db.commit()
            return True
        except Exception:
            logger.exception("Report %s failed", report_id)
            db.rollback()
            report = db.get(Report, report_id)
            report.status = ReportStatus.failed
            db.commit()
            return False


# ---------------------------------------------------------------- scheduler jobs
def run_due_reports(session_factory, now: datetime | None = None) -> list[int]:
    """Create and generate a run for every schedule that is due. Returns the new run ids."""
    now = now or utcnow()
    pending: list[tuple[int, str, str, str, bool]] = []  # run id, owner email, owner name, report name, send email?

    with session_factory() as db:
        due = db.scalars(select(Report).where(Report.scheduled.is_(True), Report.next_run_at <= now)).all()
        for template in due:
            schedule = (template.query_params or {}).get("schedule") or {}
            claim = db.execute(
                update(Report)
                .where(Report.id == template.id, Report.next_run_at == template.next_run_at)  # claim: only one worker wins
                .values(next_run_at=next_run(now, schedule.get("frequency", "daily")), last_run_at=now)
            )
            if claim.rowcount != 1:
                db.rollback()
                continue
            owner = db.get(User, template.user_id)
            if owner is None or not owner.is_active:
                db.commit()
                continue
            run = _new_run(db, template, now)
            pending.append((run.id, owner.email, owner.name, template.name, bool(schedule.get("email", True))))
            db.commit()

    for run_id, email, owner_name, name, notify in pending:
        if generate_report(session_factory, run_id) and notify:
            send_report_ready_email(email, owner_name, name)
    return [p[0] for p in pending]


def cleanup_expired(session_factory, now: datetime | None = None) -> int:
    """Delete expired reports (and their files). Schedule definitions never expire."""
    now = now or utcnow()
    with session_factory() as db:
        expired = db.scalars(select(Report).where(Report.expires_at.is_not(None), Report.expires_at < now,
                                                  Report.scheduled.is_(False))).all()
        for report in expired:
            _remove_file(report)
            db.delete(report)
        db.commit()
        return len(expired)


def tick(session_factory) -> None:
    run_due_reports(session_factory)
    cleanup_expired(session_factory)
