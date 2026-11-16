from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_writer
from app.db.session import get_db, get_session_factory
from app.models import ReportFormat, ReportStatus, User
from app.schemas.common import PageParams
from app.schemas.report import ReportCreate, ReportOut, ReportPage
from app.services import report_service

router = APIRouter()

MEDIA_TYPES = {ReportFormat.pdf: "application/pdf", ReportFormat.csv: "text/csv; charset=utf-8"}


@router.get("", response_model=ReportPage, operation_id="list_reports", summary="List reports")
def list_reports(
    params: PageParams = Depends(),
    scheduled: bool | None = Query(None, description="true = schedule definitions, false = generated reports"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return report_service.list_reports(db, user, params, scheduled)


@router.post("", response_model=ReportOut, status_code=status.HTTP_202_ACCEPTED, operation_id="create_report",
             summary="Generate or schedule a report")
def create_report(
    payload: ReportCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    user: User = Depends(require_writer),
    db: Session = Depends(get_db),
    session_factory=Depends(get_session_factory),
):
    """The file is built in the background: poll `GET /reports/{id}` until `status` is `ready`."""
    report, to_generate = report_service.create_report(db, user, payload, request)
    for report_id in to_generate:
        background_tasks.add_task(report_service.generate_report, session_factory, report_id)
    return report


@router.get("/{report_id}", response_model=ReportOut, operation_id="get_report", summary="Get report metadata")
def get_report(report_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return report_service.get_visible_report(db, user, report_id)


@router.get("/{report_id}/download", operation_id="download_report", summary="Download the report file")
def download_report(report_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    report = report_service.get_visible_report(db, user, report_id)
    if report.scheduled:
        raise HTTPException(status.HTTP_409_CONFLICT, "This is a schedule, not a file. Download one of its generated reports.")
    if report.status != ReportStatus.ready:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Report is {report.status.value}, not ready to download")
    path = report_service.file_for(report)
    if path is None or not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "The report file is no longer available")
    return FileResponse(path, media_type=MEDIA_TYPES[report.format], filename=report_service.download_name(report))


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT, operation_id="delete_report",
               summary="Delete a report (or stop a schedule)", response_class=Response)
def delete_report(report_id: int, request: Request, user: User = Depends(require_writer), db: Session = Depends(get_db)):
    report = report_service.get_visible_report(db, user, report_id)
    report_service.delete_report(db, user, report, request)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
