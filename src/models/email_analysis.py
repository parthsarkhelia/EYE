from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class EmailData(BaseModel):
    subject: str
    content: str
    sender: str
    date: datetime
    recipient: str
    attachments: Optional[List[str]] = None
    labels: Optional[List[str]] = None


class EmailAnalysisRequest(BaseModel):
    username: str
    emails: List[EmailData]
    analyze_credit: bool = True
    analyze_spending: bool = True
    analyze_identity: bool = True
    analyze_portfolio: bool = True
    analyze_travel: bool = True


class CreditAnalysis(BaseModel):
    total_cards: int
    cards: dict
    total_due: float
    upcoming_payments: List[dict]


class SpendingAnalysis(BaseModel):
    total_spent: float
    category_wise: dict
    merchant_wise: dict
    monthly_trends: dict
    payment_methods: dict


class IdentityAnalysis(BaseModel):
    verifications: dict
    documents: dict
    recent_activities: List[str]
    verification_status: dict


class PortfolioAnalysis(BaseModel):
    transactions: dict
    current_holdings: dict
    dividend_history: dict
    activity_summary: dict


class TravelAnalysis(BaseModel):
    visited_locations: dict
    recent_bookings: List[dict]
    expense_summary: dict
    transport_preferences: dict
    common_routes: dict


class EmailAnalysisResponse(BaseModel):
    username: str
    analysis_date: datetime
    credit_analysis: Optional[CreditAnalysis]
    spending_analysis: Optional[SpendingAnalysis]
    identity_analysis: Optional[IdentityAnalysis]
    portfolio_analysis: Optional[PortfolioAnalysis]
    travel_analysis: Optional[TravelAnalysis]
    summary: dict


class EmailAnalysisRecord(EmailAnalysisResponse):
    created_at: datetime
    updated_at: datetime

    def to_mongo(self):
        return {
            "username": self.username,
            "analysis_date": self.analysis_date,
            "credit_analysis": self.credit_analysis.dict()
            if self.credit_analysis
            else None,
            "spending_analysis": self.spending_analysis.dict()
            if self.spending_analysis
            else None,
            "identity_analysis": self.identity_analysis.dict()
            if self.identity_analysis
            else None,
            "portfolio_analysis": self.portfolio_analysis.dict()
            if self.portfolio_analysis
            else None,
            "travel_analysis": self.travel_analysis.dict()
            if self.travel_analysis
            else None,
            "summary": self.summary,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
