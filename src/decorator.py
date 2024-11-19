import logging
from functools import wraps

from fastapi import HTTPException, Request, Response
from fastapi.responses import RedirectResponse

from src.utils.formatter import get_request_body


def api(description=""):
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, response: Response, *args, **kwargs):
            context = request.state.context
            context["description"] = description

            content_type = request.headers.get("content-type")
            request_body = await get_request_body(request)
            logging.info(
                {
                    **context,
                    "event": "API Request received",
                    "content": content_type,
                    "request_body": request_body,
                }
            )

            resp = None
            try:
                resp = await func(request, response, *args, **kwargs)
            except Exception:
                logging.exception({**context, "event": "Processing Error"})

            if resp is None:
                logging.info(
                    {**context, "event": "API Request completed", "response_body": None}
                )
                response.status_code = 500
                return {"message": "Internal Server Error"}

            logging.info(
                {
                    **context,
                    "event": "API Request completed",
                    "response_body": resp,
                    "status_code": response.status_code,
                }
            )

            if response.status_code == 302:
                return RedirectResponse(url=resp.get("location"))

            return resp

        return wrapper

    return decorator
