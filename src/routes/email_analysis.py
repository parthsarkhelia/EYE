from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Request, Response

from src.controller import email_analysis
from src.decorator import api
from src.models.email_analysis import EmailAnalysisRequest

router = APIRouter(redirect_slashes=False)


@router.post("/analyze")
@api("Start Email Analysis")
async def analyze_emails(
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    analysis_request: EmailAnalysisRequest,
):
    context = request.state.context
    status_code, resp = await email_analysis.create_analysis_session(
        context, analysis_request
    )
    response.status_code = status_code
    return resp


@router.post("/{analysis_id}/resume")
@api("Resume Email Analysis")
async def resume_analysis(
    request: Request,
    response: Response,
    analysis_id: str,
    access_token: Optional[str] = None,
):
    context = request.state.context
    status_code, resp = await email_analysis.resume_analysis(
        context, analysis_id, access_token
    )
    response.status_code = status_code
    return resp


@router.get("/{analysis_id}/status")
@api("Get Analysis Status")
async def get_analysis_status(request: Request, response: Response, analysis_id: str):
    context = request.state.context
    status_code, resp = await email_analysis.get_analysis_status(context, analysis_id)
    response.status_code = status_code
    return resp


@router.get("/{analysis_id}/results")
@api("Get Analysis Results")
async def get_analysis_results(request: Request, response: Response, analysis_id: str):
    context = request.state.context
    status_code, resp = await email_analysis.get_analysis_results(context, analysis_id)
    response.status_code = status_code
    return resp


@router.get("/user/{user_id}/analyses")
@api("Get User Analyses")
async def get_user_analyses(
    request: Request, response: Response, user_id: str, page: int = 1, limit: int = 10
):
    context = request.state.context
    status_code, resp = await email_analysis.get_user_analyses(
        context, user_id, page, limit
    )
    response.status_code = status_code
    return resp


@router.delete("/{analysis_id}")
@api("Delete Analysis")
async def delete_analysis(request: Request, response: Response, analysis_id: str):
    context = request.state.context
    status_code, resp = await email_analysis.delete_analysis(context, analysis_id)
    response.status_code = status_code
    return resp
