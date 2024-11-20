from fastapi import APIRouter, BackgroundTasks

from src.controller.email_analyzer import AnalyzerController
from src.lib.email_analyzer import AnalyzerService
from src.models.email_analyzer import EmailBatchInput, EmailInput, TrainingInput

router = APIRouter(redirect_slashes=False)


analyzer_service = AnalyzerService()
analyzer_controller = AnalyzerController(analyzer_service)


@router.post("/email")
async def analyze_single_email(email: EmailInput):
    return await analyzer_controller.analyze_email(email)


@router.post("/batch")
async def analyze_email_batch(batch: EmailBatchInput):
    return await analyzer_controller.analyze_batch(batch)


@router.post("/train")
async def train_analyzer(
    training_data: TrainingInput, background_tasks: BackgroundTasks
):
    result = await analyzer_controller.train(training_data)
    background_tasks.add_task(analyzer_service.save_model)
    return result


@router.get("/status")
async def get_status():
    return analyzer_controller.get_status()
