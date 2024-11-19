from fastapi import APIRouter, Request, Response

from src.controller import email_analysis
from src.decorator import api
from src.models.email_analysis import EmailAnalysisRequest
from src.utils import constant

router = APIRouter(redirect_slashes=False)


@router.post("/analyze")
@api("Analyze Emails")
async def analyze_emails(
    request: Request,
    response: Response,
    analysis_request: EmailAnalysisRequest,
):
    context = request.state.context
    email_analyzer = request.app.state.email_analyzer

    status_code, resp = email_analysis.analyze_emails(
        context, email_analyzer, analysis_request
    )

    if not resp:
        status_code = 404
        resp = {"message": constant.RECORD_NOT_FOUND}

    response.status_code = status_code
    return resp


@router.get("/categories")
@api("Get Email Categories")
async def get_categories(request: Request, response: Response):
    context = request.state.context
    email_analyzer = request.app.state.email_analyzer

    status_code, resp = email_analysis.get_categories(context, email_analyzer)

    if not resp:
        status_code = 404
        resp = {"message": constant.RECORD_NOT_FOUND}

    response.status_code = status_code
    return resp


@router.post("/refresh-analysis")
@api("Refresh Email Analysis")
async def refresh_analysis(
    request: Request,
    response: Response,
    username: str,
):
    context = request.state.context
    email_analyzer = request.app.state.email_analyzer

    status_code, resp = email_analysis.refresh_analysis(
        context, email_analyzer, username
    )

    if not resp:
        status_code = 404
        resp = {"message": constant.RECORD_NOT_FOUND}

    response.status_code = status_code
    return resp
