import logging
from fastapi import APIRouter, Request, Response

from src.controller import google_auth, google_email
from src.decorator import api
from src.utils import constant

router = APIRouter(redirect_slashes=False)


@router.get("/login")
@api("Google Login")
async def google_login(request: Request, response: Response):
    context = request.state.context
    status_code, resp = google_auth.get_google_auth_url(context)
    if not resp:
        status_code = 404
        resp = {"message": constant.RECORD_NOT_FOUND}
    response.status_code = status_code
    return resp


@router.get("/callback")
@api("Google Login Callback")
async def google_login_callback(request: Request, response: Response):
    logging.info("in callback")
    context = request.state.context
    code = request.query_params.get("code")
    status_code, resp = google_auth.authenticate_google_user(context, code)
    if not resp:
        status_code = 404
        resp = {"message": constant.RECORD_NOT_FOUND}
    response.status_code = status_code
    return resp

@router.get("/getEmail")
@api("Google email list")
async def google_get_emails(request:Request, response: Response):
    context = request.state.context
    code = request.query_params.get("token")
    status_code, resp = google_email.get_email(context,code)
    if not resp:
        status_code = 404
        resp = {"message": constant.RECORD_NOT_FOUND}
    response.status_code = status_code
    return resp