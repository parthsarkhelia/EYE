from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class AnalysisResponse(BaseModel):
    category: Optional[str] = None
    merchant: Optional[str] = None
    amount: Optional[float] = None
    payment_mode: Optional[str] = None
    is_transaction: bool = False
    confidence_scores: Optional[Dict[str, float]] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


class BatchSummary(BaseModel):
    total_emails: int
    total_transactions: int
    total_amount: float
    top_categories: Dict[str, int]
    top_merchants: Dict[str, int]

    model_config = ConfigDict(arbitrary_types_allowed=True)


class BatchAnalysisResponse(BaseModel):
    results: List[AnalysisResponse]
    summary: BatchSummary

    model_config = ConfigDict(arbitrary_types_allowed=True)


class TrainingMetrics(BaseModel):
    category_accuracy: Optional[float] = None
    merchant_accuracy: Optional[float] = None
    amount_mae: Optional[float] = None
    transaction_detection: Optional[float] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


class TrainingResponse(BaseModel):
    status: str
    metrics: Optional[TrainingMetrics] = None
    model_version: str

    model_config = ConfigDict(arbitrary_types_allowed=True)


class StatusResponse(BaseModel):
    is_trained: bool
    model_version: str
    model_path: str

    model_config = ConfigDict(arbitrary_types_allowed=True)


class EmailInput(BaseModel):
    subject: str
    content: str
    sender: str
    date: datetime

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "subject": "Transaction Alert: Purchase at AMAZON.IN",
                "content": "Your credit card ending 1234 was charged Rs. 2,499.00 at AMAZON.IN",
                "sender": "alerts@bank.com",
                "date": "2024-03-20T10:30:00",
            }
        },
    )


class EmailBatchInput(BaseModel):
    emails: List[EmailInput]

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ModelParameters(BaseModel):
    batch_size: Optional[int] = 32
    epochs: Optional[int] = 10
    learning_rate: Optional[float] = 0.001

    model_config = ConfigDict(arbitrary_types_allowed=True)


class TrainingInput(BaseModel):
    emails: List[EmailInput]
    model_params: Optional[ModelParameters] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)
