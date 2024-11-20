from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response
import logging
from src.controller import email_analysis
from src.decorator import api
from src.models.email_analysis import (
    EmailAnalysisRequest,
    PaginationParams,
    ResumeAnalysisRequest,
    StoredEmailAnalysisRequest,
)
from src.utils import constant

router = APIRouter(redirect_slashes=False)


# API Routes
@router.post("/analyze/stored")
@api("Start Email Analysis from Stored Emails")
async def analyze_stored_emails(
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    analysis_request: StoredEmailAnalysisRequest,
):
    context = request.state.context
    status_code, resp = await email_analysis.create_analysis_from_stored_emails(
        context, analysis_request
    )
    response.status_code = status_code
    return resp


@router.post("/analyze")
@api("Start Email Analysis from Request")
async def analyze_emails(
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    analysis_request: EmailAnalysisRequest,
):
    context = request.state.context
    status_code, resp = await email_analysis.create_analysis_from_request(
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
    resume_request: ResumeAnalysisRequest,
):
    context = request.state.context
    status_code, resp = await email_analysis.resume_analysis(
        context, analysis_id, resume_request.access_token
    )
    response.status_code = status_code
    return resp


@router.get("/{analysis_id}/status")
@api("Get Analysis Status")
async def get_analysis_status(
    request: Request,
    response: Response,
    analysis_id: str,
):
    context = request.state.context
    status_code, resp = await email_analysis.get_analysis_status(context, analysis_id)
    response.status_code = status_code
    return resp


@router.get("/{analysis_id}/results")
@api("Get Analysis Results")
async def get_analysis_results(
    request: Request,
    response: Response,
    analysis_id: str,
):
    context = request.state.context
    status_code, resp = await email_analysis.get_analysis_results(context, analysis_id)
    response.status_code = status_code
    return resp


@router.get("/user/{user_id}/analyses")
@api("Get User Analyses")
async def get_user_analyses(
    request: Request,
    response: Response,
    user_id: str,
    pagination: PaginationParams = Depends(),
):
    context = request.state.context
    status_code, resp = await email_analysis.get_user_analyses(
        context, user_id, pagination.page, pagination.limit
    )
    response.status_code = status_code
    return resp


@router.delete("/{analysis_id}")
@api("Delete Analysis")
async def delete_analysis(
    request: Request,
    response: Response,
    analysis_id: str,
):
    context = request.state.context
    status_code, resp = await email_analysis.delete_analysis(context, analysis_id)
    response.status_code = status_code
    return resp

@router.get("/get-all-details")
@api("Get all details")
async def get_all_details(request: Request, response: Response):
    context = request.state.context
    logging.info("in get all details")
    logging.info(context)
    status_code, resp = await email_analysis.get_all_details(context)
    if not resp:
        status_code = 404
        resp = {"message": constant.RECORD_NOT_FOUND}
    response.status_code = status_code
    return resp