from fastapi import APIRouter, Request, Response

from src.controller import email_analysis
from src.decorator import api
from src.models.email_analysis import EmailAnalysisRequest

router = APIRouter(redirect_slashes=False)


@router.post("/analyze")
@api("Analyze Emails")
async def analyze_emails(
    request: Request, response: Response, analysis_request: EmailAnalysisRequest
):
    context = request.state.context
    email_analyzer = request.app.state.email_analyzer
    status_code, resp = email_analysis.analyze_emails(
        context, email_analyzer, analysis_request
    )
    response.status_code = status_code
    return resp


@router.get("/categories")
@api("Get Email Categories")
async def get_categories(request: Request, response: Response):
    context = request.state.context
    email_analyzer = request.app.state.email_analyzer
    status_code, resp = email_analysis.get_categories(context, email_analyzer)
    response.status_code = status_code
    return resp


@router.get("/user/{username}/analyses")
@api("Get User's Analysis History")
async def get_user_analyses(request: Request, response: Response, username: str):
    context = request.state.context
    status_code, resp = email_analysis.get_user_analyses(context, username)
    response.status_code = status_code
    return resp


@router.get("/analysis/{analysis_id}")
@api("Get Analysis by ID")
async def get_analysis_by_id(request: Request, response: Response, analysis_id: str):
    context = request.state.context
    status_code, resp = email_analysis.get_analysis_by_id(context, analysis_id)
    response.status_code = status_code
    return resp


@router.get("/user/{username}/latest")
@api("Get Latest Analysis")
async def get_latest_analysis(request: Request, response: Response, username: str):
    context = request.state.context
    status_code, resp = email_analysis.get_latest_analysis(context, username)
    response.status_code = status_code
    return resp


@router.get("/user/{username}/summary")
@api("Get Analysis Summary")
async def get_analysis_summary(request: Request, response: Response, username: str):
    context = request.state.context
    status_code, resp = email_analysis.get_analysis_summary(context, username)
    response.status_code = status_code
    return resp
