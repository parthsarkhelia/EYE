from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel


class EmailData(BaseModel):
    subject: str
    content: str
    sender: str
    recipient: str
    date: datetime
    labels: Optional[List[str]] = None
    thread_id: str
    message_id: str


class EmailAnalysisRequest(BaseModel):
    user_id: str
    emails: List[EmailData]
    analyze_credit: bool = True
    analyze_spending: bool = True
    analyze_identity: bool = True
    analyze_portfolio: bool = True
    analyze_travel: bool = True


class AnalysisSettings(BaseModel):
    analyze_credit: bool
    analyze_spending: bool
    analyze_identity: bool
    analyze_portfolio: bool
    analyze_travel: bool


class AnalysisRecord(BaseModel):
    analysis_id: str
    user_id: str
    status: str
    created_at: datetime
    updated_at: datetime
    email_count: int
    processed_count: int
    settings: AnalysisSettings
    error: Optional[str] = None

    class Config:
        orm_mode = True


class AnalysisResult(BaseModel):
    analysis_id: str
    user_id: str
    created_at: datetime
    completed_at: datetime
    email_count: int
    credit_analysis: Optional[Dict] = None
    spending_analysis: Optional[Dict] = None
    identity_analysis: Optional[Dict] = None
    portfolio_analysis: Optional[Dict] = None
    travel_analysis: Optional[Dict] = None
    summary: Dict

    class Config:
        orm_mode = True
