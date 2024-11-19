from typing import Dict, List, Optional

from pydantic import BaseModel, Field, root_validator


class AnalysisSettings(BaseModel):
    analyze_credit: bool = True
    analyze_spending: bool = True
    analyze_identity: bool = True
    analyze_portfolio: bool = True
    analyze_travel: bool = True

    @root_validator(pre=True)
    def set_defaults(cls, values):
        return {
            **{
                "analyze_credit": True,
                "analyze_spending": True,
                "analyze_identity": True,
                "analyze_portfolio": True,
                "analyze_travel": True,
            },
            **values,
        }


class EmailAnalysisRequest(BaseModel):
    user_id: str
    emails: List[Dict]
    analyze_credit: Optional[bool] = None
    analyze_spending: Optional[bool] = None
    analyze_identity: Optional[bool] = None
    analyze_portfolio: Optional[bool] = None
    analyze_travel: Optional[bool] = None

    @root_validator(pre=True)
    def set_defaults(cls, values):
        return {
            **{
                "analyze_credit": True,
                "analyze_spending": True,
                "analyze_identity": True,
                "analyze_portfolio": True,
                "analyze_travel": True,
            },
            **values,
        }


class StoredEmailAnalysisRequest(BaseModel):
    unique_id: str
    user_id: str
    settings: AnalysisSettings


class ResumeAnalysisRequest(BaseModel):
    access_token: Optional[str] = None


class PaginationParams(BaseModel):
    page: int = Field(default=1, gt=0)
    limit: int = Field(default=10, gt=0, le=100)
