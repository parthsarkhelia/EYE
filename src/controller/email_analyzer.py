from fastapi import HTTPException

from src.lib.email_analyzer import AnalyzerService
from src.models.email_analyzer import (
    AnalysisResponse,
    BatchAnalysisResponse,
    EmailBatchInput,
    EmailInput,
    StatusResponse,
    TrainingInput,
    TrainingResponse,
)


class AnalyzerController:
    def __init__(self, service: AnalyzerService):
        self.service = service

    async def analyze_email(self, email: EmailInput) -> AnalysisResponse:
        try:
            return await self.service.analyze_email(email)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def analyze_batch(self, batch: EmailBatchInput) -> BatchAnalysisResponse:
        try:
            return await self.service.analyze_batch(batch.emails)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def train(self, training_data: TrainingInput) -> TrainingResponse:
        if len(training_data.emails) < 10:
            raise HTTPException(
                status_code=400,
                detail="Insufficient training data. Minimum 10 emails required.",
            )

        try:
            return await self.service.train_model(
                training_data.emails, training_data.model_params
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    def get_status(self) -> StatusResponse:
        return StatusResponse(
            is_trained=self.service.is_trained,
            model_version=self.service.model_version,
            model_path=str(self.service.model_path),
        )
