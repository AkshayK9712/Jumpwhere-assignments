import csv
import io
from datetime import datetime, timezone

from pypdf import PdfReader

from app.services.report_render import ReadingRow, ReportData, SensorStat, csv_safe, render_csv, render_pdf

NOW = datetime(2026, 11, 14, 10, 0, tzinfo=timezone.utc)


def sample(template="summary", title="Boiler Temperature"):
    sensors = [
        SensorStat(1, title, "temperature", "active", "°C", count=3, minimum=70.0, mean=75.5, maximum=95.0, last=95.0, alerts=1, trend=[70, 71, 95]),
        SensorStat(2, "Idle sensor", "pressure", "inactive", "bar"),  # no readings at all
    ]
    rows = [
        ReadingRow(1, title, "temperature", "°C", NOW, 95.0, "above"),
        ReadingRow(1, title, "temperature", "°C", NOW.replace(hour=9), 70.0, None),
    ]
    if template == "alerts":
        rows = [r for r in rows if r.violation]
    return ReportData(name="Daily plant report", template=template, generated_at=NOW,
                      range_from=NOW.replace(day=13), range_to=NOW, filters=["Category: temperature"], sensors=sensors, rows=rows)


def parse(content: bytes):
    return list(csv.reader(io.StringIO(content.decode("utf-8-sig"))))


# ---------- CSV ----------
def test_csv_summary_has_one_row_per_sensor():
    rows = parse(render_csv(sample("summary")))
    assert rows[0][:3] == ["sensor_id", "title", "category"]
    assert len(rows) == 3
    assert rows[1][1] == "Boiler Temperature" and rows[1][5] == "3" and rows[1][7] == "75.5" and rows[1][10] == "1"
    assert rows[2][5] == "0" and rows[2][6] == ""  # empty stats stay blank


def test_csv_detailed_lists_readings_with_iso_times():
    rows = parse(render_csv(sample("detailed")))
    assert rows[0] == ["sensor_id", "title", "category", "unit", "recorded_at", "value", "violation"]
    assert len(rows) == 3
    assert rows[1][4] == "2026-11-14T10:00:00Z" and rows[1][5] == "95" and rows[1][6] == "above"


def test_csv_alerts_only_contains_violations():
    rows = parse(render_csv(sample("alerts")))
    assert len(rows) == 2 and rows[1][6] == "above"


def test_csv_has_bom_for_excel():
    assert render_csv(sample()).startswith(b"\xef\xbb\xbf")


def test_csv_blocks_formula_injection():
    assert csv_safe("=1+1") == "'=1+1"
    assert csv_safe("@SUM(A1)") == "'@SUM(A1)"
    assert csv_safe("-2+3") == "'-2+3"
    assert csv_safe("+cmd") == "'+cmd"
    assert csv_safe("normal") == "normal" and csv_safe(None) == "" and csv_safe(5) == "5"
    rows = parse(render_csv(sample("summary", title='=HYPERLINK("http://evil")')))
    assert rows[1][1].startswith("'=")


def test_csv_quotes_commas_and_newlines():
    rows = parse(render_csv(sample("summary", title='Pump, "north"\nline 2')))
    assert rows[1][1] == 'Pump, "north"\nline 2'


# ---------- PDF ----------
def pdf_text(content: bytes) -> str:
    return "\n".join(page.extract_text() for page in PdfReader(io.BytesIO(content)).pages)


def test_pdf_is_a_valid_document_with_the_expected_content():
    content = render_pdf(sample("summary"))
    assert content.startswith(b"%PDF")
    reader = PdfReader(io.BytesIO(content))
    assert len(reader.pages) >= 1
    assert reader.metadata.title == "Daily plant report"
    text = pdf_text(content)
    for expected in ["Daily plant report", "Summary report", "Boiler Temperature", "Idle sensor", "75.5", "Category: temperature", "Page 1"]:
        assert expected in text, expected


def test_pdf_detailed_and_alerts_list_readings():
    assert "Readings" in pdf_text(render_pdf(sample("detailed")))
    text = pdf_text(render_pdf(sample("alerts")))
    assert "outside thresholds" in text and "above" in text


def test_pdf_escapes_markup_in_user_text():
    content = render_pdf(sample("summary", title="<b>Bold</b> & <script>x</script>"))
    assert "<b>Bold</b>" in pdf_text(content)  # shown literally, not interpreted


def test_pdf_with_no_sensors():
    data = sample()
    data.sensors, data.rows = [], []
    assert "No sensors matched" in pdf_text(render_pdf(data))


def test_pdf_with_many_rows_is_capped_and_says_so():
    data = sample("detailed")
    data.rows = [ReadingRow(1, "S", "temperature", "C", NOW, float(i)) for i in range(1000)]
    content = render_pdf(data)
    assert "Showing the first 300 of 1000 rows" in pdf_text(content)
    assert len(PdfReader(io.BytesIO(content)).pages) > 1
