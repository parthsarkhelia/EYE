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

async def verify_api_version(
    x_bureau_api_version: Optional[str] = Header(None, alias="x-bureau-api-version")
) -> str:
    if not x_bureau_api_version:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Missing required header: x-bureau-api-version",
                "code": "MISSING_HEADER",
                "requestId": str(uuid.uuid4())
            }
        )
    return x_bureau_api_version

# async def verify_client_ip(
#     x_bureau_client_ip: Optional[str] = Header(None, alias="x-bureau-client-ip")
# ) -> str:
#     if not x_bureau_client_ip:
#         raise HTTPException(
#             status_code=400,
#             detail={
#                 "error": "Missing required header: x-bureau-client-ip",
#                 "code": "MISSING_HEADER",
#                 "requestId": str(uuid.uuid4())
#             }
#         )
#     return x_bureau_client_ip

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
    request_body: SubmitRequestBody,
    api_version: str = Depends(verify_api_version),
    auth_credential: str = Depends(verify_auth_credential)
):
    context = request.state.context
    logging.Info("Router me aa gaye oye: " + request_body)
    return await device_data.bureau_eye_submit(
        context,
        device_data=request_body,
        api_version=api_version,
        auth_credential=auth_credential
    )