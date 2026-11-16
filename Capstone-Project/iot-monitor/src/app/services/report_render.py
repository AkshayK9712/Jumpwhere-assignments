"""Turn report data into CSV or PDF bytes. Pure: no database, no web framework."""
import csv
import io
from dataclasses import dataclass, field
from datetime import datetime, timezone
from xml.sax.saxutils import escape

from reportlab.graphics.shapes import Drawing, PolyLine
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

PDF_MAX_DETAIL_ROWS = 300


@dataclass
class SensorStat:
    sensor_id: int
    title: str
    category: str
    status: str
    unit: str = ""
    count: int = 0
    minimum: float | None = None
    mean: float | None = None
    maximum: float | None = None
    last: float | None = None
    alerts: int = 0
    trend: list[float] = field(default_factory=list)


@dataclass
class ReadingRow:
    sensor_id: int
    title: str
    category: str
    unit: str
    recorded_at: datetime
    value: float
    violation: str | None = None


@dataclass
class ReportData:
    name: str
    template: str  # summary | detailed | alerts
    generated_at: datetime
    range_from: datetime
    range_to: datetime
    filters: list[str] = field(default_factory=list)
    sensors: list[SensorStat] = field(default_factory=list)
    rows: list[ReadingRow] = field(default_factory=list)
    truncated: bool = False


# ---------------------------------------------------------------- CSV
def csv_safe(value) -> str:
    """Stop spreadsheet formula injection: text starting with = + - @ is prefixed with an apostrophe."""
    text = "" if value is None else str(value)
    if text and text[0] in "=+-@\t\r":
        return "'" + text
    return text


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _num(value: float | None) -> str:
    return "" if value is None else f"{value:.4f}".rstrip("0").rstrip(".")


def render_csv(data: ReportData) -> bytes:
    """UTF-8 with a BOM so Excel shows characters like the degree sign correctly."""
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\r\n")
    if data.template == "summary":
        writer.writerow(["sensor_id", "title", "category", "status", "unit", "readings", "min", "avg", "max", "last", "alerts"])
        for s in data.sensors:
            writer.writerow([s.sensor_id, csv_safe(s.title), s.category, s.status, csv_safe(s.unit), s.count,
                             _num(s.minimum), _num(s.mean), _num(s.maximum), _num(s.last), s.alerts])
    else:  # detailed and alerts list individual readings
        writer.writerow(["sensor_id", "title", "category", "unit", "recorded_at", "value", "violation"])
        for r in data.rows:
            writer.writerow([r.sensor_id, csv_safe(r.title), r.category, csv_safe(r.unit), _iso(r.recorded_at), _num(r.value), r.violation or ""])
    return buf.getvalue().encode("utf-8-sig")


# ---------------------------------------------------------------- PDF
def _p(text, style) -> Paragraph:
    return Paragraph(escape(str(text)), style)  # escape: user text must not be read as markup


def _sparkline(values: list[float], width: float = 60, height: float = 14) -> Drawing:
    d = Drawing(width, height)
    if len(values) >= 2:
        lo, hi = min(values), max(values)
        span = (hi - lo) or 1.0
        pts = []
        for i, v in enumerate(values):
            pts += [1 + i * (width - 2) / (len(values) - 1), 1 + (v - lo) / span * (height - 2)]
        d.add(PolyLine(pts, strokeColor=colors.HexColor("#1d6fd1"), strokeWidth=1))
    return d


def _fmt(value: float | None, unit: str = "") -> str:
    if value is None:
        return "-"
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return f"{text} {unit}".strip()


def _table(rows, col_widths, header_bg="#1f2933"):
    table = Table(rows, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(header_bg)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f5f8")]),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#c9d2db")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return table


def render_pdf(data: ReportData) -> bytes:
    styles = getSampleStyleSheet()
    small = ParagraphStyle("small", parent=styles["Normal"], fontSize=8, leading=10)
    cell = ParagraphStyle("cell", parent=small, leading=9)
    head = ParagraphStyle("head", parent=small, textColor=colors.white, fontName="Helvetica-Bold")
    note = ParagraphStyle("note", parent=small, textColor=colors.HexColor("#62707f"))

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=15 * mm, bottomMargin=18 * mm,
                            title=data.name, author="IoT Monitor")

    def footer(canvas, document):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#62707f"))
        canvas.drawString(15 * mm, 10 * mm, "IoT Monitor")
        canvas.drawRightString(A4[0] - 15 * mm, 10 * mm, f"Page {document.page}")
        canvas.restoreState()

    total_readings = sum(s.count for s in data.sensors)
    total_alerts = sum(s.alerts for s in data.sensors)
    story = [
        _p(data.name, styles["Title"]),
        _p(f"{data.template.capitalize()} report", styles["Heading3"]),
        Spacer(1, 4),
        _table([
            [_p("Generated", head), _p("Period (UTC)", head), _p("Sensors", head), _p("Readings", head), _p("Alerts", head)],
            [_p(_iso(data.generated_at), cell), _p(f"{_iso(data.range_from)} to {_iso(data.range_to)}", cell),
             _p(len(data.sensors), cell), _p(total_readings, cell), _p(total_alerts, cell)],
        ], [38 * mm, 68 * mm, 20 * mm, 25 * mm, 25 * mm]),
    ]
    if data.filters:
        story += [Spacer(1, 4), _p("Filters: " + "; ".join(data.filters), note)]
    if data.truncated:
        story += [Spacer(1, 4), _p("Note: the data was truncated to keep the report a manageable size. Narrow the period for complete results.", note)]
    story += [Spacer(1, 10), _p("Sensor summary", styles["Heading2"])]

    if not data.sensors:
        story.append(_p("No sensors matched the selected filters.", styles["Normal"]))
    else:
        rows = [[_p(h, head) for h in ["Sensor", "Category", "Status", "Readings", "Min", "Avg", "Max", "Alerts", "Trend"]]]
        for s in data.sensors:
            rows.append([_p(s.title, cell), _p(s.category, cell), _p(s.status, cell), _p(s.count, cell),
                         _p(_fmt(s.minimum, s.unit), cell), _p(_fmt(s.mean, s.unit), cell), _p(_fmt(s.maximum, s.unit), cell),
                         _p(s.alerts, cell), _sparkline(s.trend)])
        story.append(_table(rows, [35 * mm, 20 * mm, 15 * mm, 18 * mm, 18 * mm, 18 * mm, 18 * mm, 14 * mm, 24 * mm]))

    if data.template in ("detailed", "alerts"):
        title = "Readings outside thresholds" if data.template == "alerts" else "Readings"
        story += [Spacer(1, 12), _p(title, styles["Heading2"])]
        if not data.rows:
            story.append(_p("No readings to list.", styles["Normal"]))
        else:
            shown = data.rows[:PDF_MAX_DETAIL_ROWS]
            rows = [[_p(h, head) for h in ["Time (UTC)", "Sensor", "Value", "Violation"]]]
            for r in shown:
                rows.append([_p(_iso(r.recorded_at), cell), _p(r.title, cell), _p(_fmt(r.value, r.unit), cell), _p(r.violation or "", cell)])
            story.append(_table(rows, [42 * mm, 80 * mm, 32 * mm, 26 * mm]))
            if len(data.rows) > len(shown):
                story += [Spacer(1, 4), _p(f"Showing the first {len(shown)} of {len(data.rows)} rows. Export CSV for the full list.", note)]

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buf.getvalue()
