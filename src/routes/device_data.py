import logging
from pydantic import BaseModel, Field
from http.client import HTTPException
import uuid
from fastapi import APIRouter, Header, Depends, Request, Response
from typing import Optional
from src.controller import device_data
from src.decorator import api
from src.models.device import SubmitRequestBody

router = APIRouter(redirect_slashes=False)


async def verify_auth_credential(
    x_bureau_auth_credential_id: Optional[str] = Header(None, alias="X-Bureau-Auth-Credential-ID")
) -> str:
    if not x_bureau_auth_credential_id:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "Missing required header: X-Bureau-Auth-Credential-ID",
                "code": "UNAUTHORIZED",
                "requestId": str(uuid.uuid4())
            }
        )
    return x_bureau_auth_credential_id

@router.post("/bureau-eye-submit")
@api("Bureau Eye Submit")
async def process_device_data(
    request: Request,
    response: Response,
    auth_credential: str = Depends(verify_auth_credential)
):
    context = request.state.context
    request_body = await request.json()
    return await device_data.handle_bureau_eye_submit(
        context,
        device_data=request_body,
        auth_credential=auth_credential
    )