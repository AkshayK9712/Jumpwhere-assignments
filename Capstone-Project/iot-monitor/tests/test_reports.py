import csv
import io
from datetime import datetime, timedelta, timezone

from pypdf import PdfReader
from sqlalchemy import select

from app.core.config import settings
from app.models import Report

BASE = "/api/v1"
NOW = datetime.now(timezone.utc)


def ago(**kw):
    return NOW - timedelta(**kw)


def body(**overrides):
    data = {"name": "Plant report", "format": "csv", "query_params": {"template": "summary"}}
    data.update(overrides)
    return data


def create(client, headers, expect=202, **overrides):
    r = client.post(f"{BASE}/reports", json=body(**overrides), headers=headers)
    assert r.status_code == expect, r.text
    return r.json()


def csv_rows(response):
    return list(csv.reader(io.StringIO(response.content.decode("utf-8-sig"))))


# ---------- create + download ----------
def test_csv_summary_report_is_generated_and_downloadable(client, make_user, make_sensor, bearer):
    user = make_user("user")
    make_sensor(user, "Boiler", meta={"unit": "C"}, readings=[(ago(hours=2), 10.0), (ago(hours=1), 30.0)])
    h = bearer(user)

    created = create(client, h)
    assert created["status"] in ("pending", "ready") and created["scheduled"] is False and created["expires_at"]
    got = client.get(f"{BASE}/reports/{created['id']}", headers=h).json()
    assert got["status"] == "ready"  # the background job has finished

    r = client.get(f"{BASE}/reports/{created['id']}/download", headers=h)
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    assert "attachment" in r.headers["content-disposition"] and ".csv" in r.headers["content-disposition"]
    rows = csv_rows(r)
    assert rows[0][:3] == ["sensor_id", "title", "category"]
    assert rows[1][1] == "Boiler" and rows[1][5] == "2" and rows[1][6] == "10" and rows[1][8] == "30"


def test_pdf_detailed_report(client, make_user, make_sensor, bearer):
    user = make_user("user")
    make_sensor(user, "Press", readings=[(ago(hours=1), 4.0)])
    h = bearer(user)
    created = create(client, h, name="Press PDF", format="pdf", query_params={"template": "detailed"})
    r = client.get(f"{BASE}/reports/{created['id']}/download", headers=h)
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")
    text = "\n".join(p.extract_text() for p in PdfReader(io.BytesIO(r.content)).pages)
    assert "Press PDF" in text and "Press" in text and "Detailed report" in text


def test_alerts_template_lists_only_threshold_violations(client, make_user, make_sensor, bearer):
    user = make_user("user")
    make_sensor(user, "Boiler", meta={"thresholds": {"min": 60, "max": 90}},
                readings=[(ago(hours=3), 75.0), (ago(hours=2), 95.0), (ago(hours=1), 50.0)])
    h = bearer(user)
    created = create(client, h, format="csv", query_params={"template": "alerts"})
    rows = csv_rows(client.get(f"{BASE}/reports/{created['id']}/download", headers=h))
    assert [r[6] for r in rows[1:]] == ["below", "above"] or sorted(r[6] for r in rows[1:]) == ["above", "below"]
    assert len(rows) == 3


def test_report_filters_by_sensor_ids_and_category(client, make_user, make_sensor, bearer):
    user = make_user("user")
    a = make_sensor(user, "Alpha", "temperature", readings=[(ago(hours=1), 1.0)])
    make_sensor(user, "Beta", "pressure", readings=[(ago(hours=1), 2.0)])
    h = bearer(user)

    by_id = create(client, h, query_params={"template": "summary", "sensor_ids": [a.id]})
    assert [r[1] for r in csv_rows(client.get(f"{BASE}/reports/{by_id['id']}/download", headers=h))[1:]] == ["Alpha"]

    by_cat = create(client, h, query_params={"template": "summary", "category": "pressure"})
    assert [r[1] for r in csv_rows(client.get(f"{BASE}/reports/{by_cat['id']}/download", headers=h))[1:]] == ["Beta"]


def test_report_only_contains_sensors_the_owner_may_see(client, make_user, make_sensor, bearer):
    mine, theirs = make_user("user"), make_user("user")
    make_sensor(mine, "Mine")
    make_sensor(theirs, "Secret")
    h = bearer(mine)
    created = create(client, h)
    titles = [r[1] for r in csv_rows(client.get(f"{BASE}/reports/{created['id']}/download", headers=h))[1:]]
    assert titles == ["Mine"]


def test_report_respects_custom_range(client, make_user, make_sensor, bearer):
    user = make_user("user")
    make_sensor(user, "S", readings=[(ago(days=5), 1.0), (ago(hours=1), 2.0)])
    h = bearer(user)
    created = create(client, h, query_params={"template": "summary", "from": ago(days=7).isoformat(), "to": NOW.isoformat()})
    rows = csv_rows(client.get(f"{BASE}/reports/{created['id']}/download", headers=h))
    assert rows[1][5] == "2"  # both readings are inside the 7-day range


# ---------- permissions ----------
def test_visibility_and_roles(client, make_user, make_sensor, bearer):
    owner, other, admin, guest = make_user("user"), make_user("user"), make_user("admin"), make_user("guest")
    created = create(client, bearer(owner))
    rid = created["id"]

    assert client.get(f"{BASE}/reports/{rid}", headers=bearer(other)).status_code == 404
    assert client.get(f"{BASE}/reports/{rid}/download", headers=bearer(other)).status_code == 404
    assert client.get(f"{BASE}/reports", headers=bearer(other)).json()["total"] == 0
    assert client.get(f"{BASE}/reports/{rid}/download", headers=bearer(admin)).status_code == 200
    assert client.get(f"{BASE}/reports/{rid}/download", headers=bearer(guest)).status_code == 200   # guests may view and download
    assert client.post(f"{BASE}/reports", json=body(), headers=bearer(guest)).status_code == 403
    assert client.delete(f"{BASE}/reports/{rid}", headers=bearer(guest)).status_code == 403
    assert client.delete(f"{BASE}/reports/{rid}", headers=bearer(other)).status_code == 404
    assert client.get(f"{BASE}/reports").status_code == 401


def test_delete_removes_the_file(client, make_user, bearer):
    user = make_user("user")
    h = bearer(user)
    created = create(client, h)
    folder = settings.REPORTS_DIR
    from pathlib import Path
    assert len(list(Path(folder).glob("*.csv"))) == 1
    assert client.delete(f"{BASE}/reports/{created['id']}", headers=h).status_code == 204
    assert list(Path(folder).glob("*.csv")) == []
    assert client.get(f"{BASE}/reports/{created['id']}", headers=h).status_code == 404


# ---------- validation ----------
def test_validation(client, make_user, bearer):
    h = bearer(make_user("user"))
    post = lambda **kw: client.post(f"{BASE}/reports", json=body(**kw), headers=h).status_code
    assert post(name="") == 422
    assert post(format="docx") == 422
    assert post(query_params={"template": "weird"}) == 422
    assert post(query_params={"from": NOW.isoformat(), "to": ago(hours=1).isoformat()}) == 422        # from after to
    assert post(query_params={"from": ago(days=400).isoformat(), "to": NOW.isoformat()}) == 422        # longer than 366 days
    assert post(scheduled=True) == 422                                                                  # schedule missing
    assert post(schedule={"frequency": "daily"}) == 422                                                 # schedule without scheduled
    assert post(scheduled=True, schedule={"frequency": "hourly"}) == 422
    assert post(scheduled=True, schedule={"frequency": "daily"}, query_params={"from": ago(days=1).isoformat()}) == 422


def test_report_name_is_sanitized(client, make_user, bearer):
    h = bearer(make_user("user"))
    created = create(client, h, name="<b>Weekly</b>  report")
    assert created["name"] == "Weekly report"


# ---------- download edge cases ----------
def test_download_not_ready_or_missing_file(client, make_user, bearer, db_session):
    user = make_user("user")
    h = bearer(user)
    rid = create(client, h)["id"]

    report = db_session.get(Report, rid)
    report.status = "pending"
    db_session.commit()
    assert client.get(f"{BASE}/reports/{rid}/download", headers=h).status_code == 409

    report.status = "ready"
    report.file_path = "does-not-exist.csv"
    db_session.commit()
    assert client.get(f"{BASE}/reports/{rid}/download", headers=h).status_code == 404


def test_download_cannot_escape_the_reports_folder(client, make_user, bearer, db_session, tmp_path):
    user = make_user("user")
    h = bearer(user)
    rid = create(client, h)["id"]
    (tmp_path / "secret.txt").write_text("top secret")
    report = db_session.get(Report, rid)
    report.file_path = "../secret.txt"
    db_session.commit()
    assert client.get(f"{BASE}/reports/{rid}/download", headers=h).status_code == 404


# ---------- scheduling ----------
def test_scheduled_report_creates_a_definition_and_a_first_run(client, make_user, make_sensor, bearer):
    user = make_user("user")
    make_sensor(user, "S", readings=[(ago(hours=1), 1.0)])
    h = bearer(user)

    definition = create(client, h, name="Daily", scheduled=True, schedule={"frequency": "daily", "email": False})
    assert definition["scheduled"] is True and definition["next_run_at"] and definition["query_params"]["window_hours"] == 24
    assert definition["query_params"]["schedule"]["frequency"] == "daily"

    runs = client.get(f"{BASE}/reports", params={"scheduled": "false"}, headers=h).json()
    assert runs["total"] == 1
    run = runs["items"][0]
    assert run["source_id"] == definition["id"] and run["status"] == "ready" and run["name"].startswith("Daily - ")
    assert client.get(f"{BASE}/reports/{run['id']}/download", headers=h).status_code == 200

    defs = client.get(f"{BASE}/reports", params={"scheduled": "true"}, headers=h).json()
    assert [d["id"] for d in defs["items"]] == [definition["id"]]


def test_schedule_definition_has_no_file(client, make_user, bearer):
    h = bearer(make_user("user"))
    definition = create(client, h, scheduled=True, schedule={"frequency": "weekly"})
    assert client.get(f"{BASE}/reports/{definition['id']}/download", headers=h).status_code == 409
    assert definition["query_params"]["window_hours"] == 168


def test_reports_are_audited(client, make_user, bearer, db_session):
    from app.models import ActivityLog

    h = bearer(make_user("user"))
    rid = create(client, h)["id"]
    client.delete(f"{BASE}/reports/{rid}", headers=h)
    actions = set(db_session.scalars(select(ActivityLog.action)))
    assert {"report.create", "report.delete"} <= actions
