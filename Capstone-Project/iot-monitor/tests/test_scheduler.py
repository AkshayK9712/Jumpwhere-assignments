from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select

from app.core.config import settings
from app.models import Report, ReportFormat, ReportStatus
from app.services import email, report_service

BASE = "/api/v1"


def make_schedule(client, headers, frequency="daily", send_email=True):
    r = client.post(f"{BASE}/reports", headers=headers, json={
        "name": "Nightly", "format": "csv", "query_params": {"template": "summary"},
        "scheduled": True, "schedule": {"frequency": frequency, "email": send_email}})
    assert r.status_code == 202, r.text
    return r.json()["id"]


def make_due(db_session, report_id):
    db_session.expire_all()
    report = db_session.get(Report, report_id)
    report.next_run_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    db_session.commit()


def runs(db_session, definition_id):
    db_session.expire_all()
    return db_session.scalars(select(Report).where(Report.source_id == definition_id)).all()


def test_due_schedule_creates_and_generates_a_new_run(client, make_user, make_sensor, bearer, db_session, session_factory):
    user = make_user("user")
    make_sensor(user, "S")
    sid = make_schedule(client, bearer(user))
    assert len(runs(db_session, sid)) == 1          # the first run made at creation

    make_due(db_session, sid)
    new_ids = report_service.run_due_reports(session_factory)
    assert len(new_ids) == 1
    all_runs = runs(db_session, sid)
    assert len(all_runs) == 2 and all(r.status == ReportStatus.ready for r in all_runs)
    assert all(report_service.file_for(r).is_file() for r in all_runs)

    definition = db_session.get(Report, sid)
    assert definition.last_run_at is not None
    next_run = definition.next_run_at if definition.next_run_at.tzinfo else definition.next_run_at.replace(tzinfo=timezone.utc)
    assert next_run > datetime.now(timezone.utc) + timedelta(hours=23)  # moved a day ahead


def test_not_yet_due_schedule_is_left_alone(client, make_user, bearer, db_session, session_factory):
    sid = make_schedule(client, bearer(make_user("user")))
    assert report_service.run_due_reports(session_factory) == []
    assert len(runs(db_session, sid)) == 1


def test_running_twice_does_not_duplicate(client, make_user, bearer, db_session, session_factory):
    sid = make_schedule(client, bearer(make_user("user")))
    make_due(db_session, sid)
    assert len(report_service.run_due_reports(session_factory)) == 1
    assert report_service.run_due_reports(session_factory) == []   # next_run_at already moved on
    assert len(runs(db_session, sid)) == 2


def test_disabled_owner_gets_no_run_but_schedule_advances(client, make_user, bearer, db_session, session_factory):
    from app.models import User

    user = make_user("user")
    sid = make_schedule(client, bearer(user))
    db_session.get(User, user.id).is_active = False
    db_session.commit()
    make_due(db_session, sid)
    assert report_service.run_due_reports(session_factory) == []
    assert len(runs(db_session, sid)) == 1


def test_email_is_sent_when_requested(client, make_user, bearer, db_session, session_factory):
    user = make_user("user", email="boss@example.com")
    sid = make_schedule(client, bearer(user), send_email=True)
    email.OUTBOX.clear()
    make_due(db_session, sid)
    report_service.run_due_reports(session_factory)
    assert len(email.OUTBOX) == 1
    assert email.OUTBOX[0]["to"] == "boss@example.com" and "Nightly" in email.OUTBOX[0]["subject"]
    assert "/ui/#/reports" in email.OUTBOX[0]["body"]


def test_no_email_when_not_requested(client, make_user, bearer, db_session, session_factory):
    sid = make_schedule(client, bearer(make_user("user")), send_email=False)
    email.OUTBOX.clear()
    make_due(db_session, sid)
    report_service.run_due_reports(session_factory)
    assert email.OUTBOX == []


def test_cleanup_removes_expired_reports_and_files_but_keeps_schedules(client, make_user, bearer, db_session, session_factory):
    h = bearer(make_user("user"))
    one_off = client.post(f"{BASE}/reports", json={"name": "Old", "format": "csv"}, headers=h).json()["id"]
    sid = make_schedule(client, h)

    db_session.expire_all()
    old = db_session.get(Report, one_off)
    path = report_service.file_for(old)
    assert path.is_file()
    old.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    db_session.get(Report, sid).expires_at = datetime.now(timezone.utc) - timedelta(days=1)  # must be ignored: it is a definition
    db_session.commit()

    assert report_service.cleanup_expired(session_factory) == 1
    db_session.expire_all()
    assert db_session.get(Report, one_off) is None
    assert not path.exists()
    assert db_session.get(Report, sid) is not None


def test_failed_generation_marks_the_report_failed(client, make_user, bearer, db_session, session_factory, monkeypatch):
    h = bearer(make_user("user"))
    rid = client.post(f"{BASE}/reports", json={"name": "Boom", "format": "csv"}, headers=h).json()["id"]
    report = db_session.get(Report, rid)
    report.status = ReportStatus.pending
    report.file_path = None
    db_session.commit()

    def explode(*args, **kwargs):
        raise RuntimeError("disk on fire")

    monkeypatch.setattr(report_service, "render_csv", explode)
    assert report_service.generate_report(session_factory, rid) is False
    db_session.expire_all()
    assert db_session.get(Report, rid).status == ReportStatus.failed
    assert client.get(f"{BASE}/reports/{rid}/download", headers=h).status_code == 409


def test_production_config_refuses_weak_secrets():
    import pytest
    from pydantic import ValidationError

    from app.core.config import Settings

    with pytest.raises(ValidationError):
        Settings(ENVIRONMENT="production", JWT_SECRET="short")
    assert Settings(ENVIRONMENT="production", JWT_SECRET="x" * 40).ENVIRONMENT == "production"
    assert Settings(ENVIRONMENT="development", JWT_SECRET="short").JWT_SECRET == "short"
