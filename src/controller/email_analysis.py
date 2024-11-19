import logging
from datetime import datetime
from typing import Dict, Tuple

from src.core import mongo
from src.lib.email_classifier import EmailAnalyzer
from src.models.email_analysis import (
    EmailAnalysisRecord,
    EmailAnalysisRequest,
    EmailAnalysisResponse,
)
from src.utils import constant


def analyze_emails(
    context: Dict, email_analyzer: EmailAnalyzer, request: EmailAnalysisRequest
) -> Tuple[int, Dict]:
    try:
        logging.info(
            {
                **context,
                "action": "analyzing_emails",
                "username": request.username,
                "email_count": len(request.emails),
            }
        )

        # Convert request emails to format expected by analyzer
        emails = [
            {
                "subject": email.subject,
                "content": email.content,
                "sender": email.sender,
                "date": email.date.isoformat(),
                "recipient": email.recipient,
                "attachments": email.attachments,
                "labels": email.labels,
            }
            for email in request.emails
        ]

        # Process emails through analyzer
        analysis_results = email_analyzer.process_emails(emails)

        # Generate complete analysis response
        response = EmailAnalysisResponse(
            username=request.username,
            analysis_date=datetime.now(),
            credit_analysis=analysis_results.get("credit_analysis")
            if request.analyze_credit
            else None,
            spending_analysis=analysis_results.get("spending_analysis")
            if request.analyze_spending
            else None,
            identity_analysis=analysis_results.get("identity_analysis")
            if request.analyze_identity
            else None,
            portfolio_analysis=analysis_results.get("portfolio_analysis")
            if request.analyze_portfolio
            else None,
            travel_analysis=analysis_results.get("travel_analysis")
            if request.analyze_travel
            else None,
            summary=email_analyzer.get_summary_report(analysis_results),
        )

        # Store analysis record
        record = EmailAnalysisRecord(
            **response.dict(), created_at=datetime.now(), updated_at=datetime.now()
        )

        mongo.email_analysis_collection.update_one(
            {"username": request.username}, {"$set": record.to_mongo()}, upsert=True
        )

        logging.info(
            {
                **context,
                "action": "email_analysis_complete",
                "username": request.username,
                "analysis_stored": True,
            }
        )

        return 200, {
            "message": constant.EMAIL_ANALYSIS_SUCCESS,
            "data": response.dict(),
        }

    except Exception as e:
        logging.exception(
            {
                **context,
                "action": "email_analysis_failed",
                "error": str(e),
                "error_type": type(e).__name__,
            }
        )
        return 400, {"message": constant.PROCESSING_ERROR}


def get_categories(context: Dict, email_analyzer: EmailAnalyzer) -> Tuple[int, Dict]:
    try:
        categories = {
            "email_categories": email_analyzer.email_categories,
            "company_categories": email_analyzer.company_categories,
        }

        return 200, {"message": constant.CATEGORIES_FETCH_SUCCESS, "data": categories}

    except Exception as e:
        logging.exception(
            {**context, "action": "get_categories_failed", "error": str(e)}
        )
        return 400, {"message": constant.PROCESSING_ERROR}


def refresh_analysis(
    context: Dict, email_analyzer: EmailAnalyzer, username: str
) -> Tuple[int, Dict]:
    try:
        # Get latest analysis from database
        analysis = mongo.email_analysis_collection.find_one({"username": username})

        if not analysis:
            return 404, {"message": constant.RECORD_NOT_FOUND}

        # Update the analysis timestamp
        analysis["updated_at"] = datetime.now()

        mongo.email_analysis_collection.update_one(
            {"username": username}, {"$set": analysis}
        )

        return 200, {"message": constant.ANALYSIS_REFRESH_SUCCESS, "data": analysis}

    except Exception as e:
        logging.exception(
            {**context, "action": "refresh_analysis_failed", "error": str(e)}
        )
        return 400, {"message": constant.PROCESSING_ERROR}
