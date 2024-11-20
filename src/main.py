import logging
import traceback

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.lib.email_classifier import EmailAnalyzer
from src.middleware import LoggingMiddleware, RequestIDMiddleware
from src.routes import device_data, email_analysis, google_auth
from src.secrets import secrets
from src.utils.init_models import ModelSetup

app = FastAPI(
    title="Bureau EYE API",
    description="Bureau EYE api",
    redirect_slashes=False,
    openapi_url="/service/api/v1/openapi.json",
    docs_url="/service/docs",
    redoc_url="/service/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(LoggingMiddleware)


@app.get("/")
async def root():
    return {"Hello": "World"}


@app.get("/health")
async def healthroot():
    return {"status": "OK"}


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    try:
        exc_errors = exc.errors()
        errors = []
        for err in exc_errors:
            errors.append(f"{err.get('loc')[0]}: {err.get('loc')[1]} {err.get('msg')}")
        return JSONResponse(
            status_code=400,
            content={"message": "Bad Request", "description": errors},
        )
    except Exception as e:
        print(traceback.format_tb(e.__traceback__))
        return JSONResponse(
            status_code=400,
            content={"message": "Bad Request", "detail": exc.errors()},
        )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail, "path": request.url.path},
    )


@app.exception_handler(Exception)
async def exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=400,
        content={"message": str(exc)},
    )


@app.on_event("startup")
async def startup_event():
    logging.info({"action": "server_startup", "status": "initializing_models"})
    try:
        setup = ModelSetup()
        setup.setup()
        app.state.email_analyzer = EmailAnalyzer()
        logging.info({"action": "server_startup", "status": "initialization_complete"})
    except Exception as e:
        logging.error(
            {
                "action": "server_startup",
                "status": "initialization_failed",
                "error": str(e),
                "error_type": type(e).__name__,
            }
        )
        raise


router = APIRouter(redirect_slashes=False)
router.include_router(
    google_auth.router, prefix="/google-auth", tags=["User Authentication"]
)
router.include_router(
    email_analysis.router, prefix="/email-analysis", tags=["Email Analysis"]
)
router.include_router(device_data.router, prefix="/device", tags=["Bureau Eye Submit"])
app.include_router(router)
