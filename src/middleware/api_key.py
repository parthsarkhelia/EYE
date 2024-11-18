from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.models.common import ErrorResponse


class APIKeyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, api_key: str):
        super().__init__(app)
        self.api_key = api_key

    async def dispatch(self, request: Request, call_next):
        try:
            if request.headers.get("X-API-KEY") != self.api_key:
                raise HTTPException(status_code=401, detail="Unauthorized")
            return await call_next(request)
        except HTTPException as e:
            return JSONResponse(
                status_code=e.status_code,
                content=ErrorResponse(detail=e.detail).dict(),
            )
        except Exception:
            return JSONResponse(
                status_code=500,
                content=ErrorResponse(detail="Internal server error").dict(),
            )
