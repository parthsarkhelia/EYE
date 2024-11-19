import logging
from datetime import datetime
from typing import Dict, Tuple

from bson import ObjectId

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
        analysis_id = str(ObjectId())
        current_time = datetime.now()

        response = EmailAnalysisResponse(
            username=request.username,
            analysis_id=analysis_id,
            analysis_date=current_time,
            email_count=len(request.emails),
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
            **response.dict(),
            created_at=current_time,
            updated_at=current_time,
            analysis_status="completed",
            request_metadata={
                "analyze_credit": request.analyze_credit,
                "analyze_spending": request.analyze_spending,
                "analyze_identity": request.analyze_identity,
                "analyze_portfolio": request.analyze_portfolio,
                "analyze_travel": request.analyze_travel,
            },
        )

        # Insert new analysis record
        mongo.email_analysis_collection.insert_one(record.to_mongo())

        # Update user's analysis history
        mongo.user_analysis_history.insert_one(
            {
                "username": request.username,
                "analysis_id": analysis_id,
                "analysis_date": current_time,
                "email_count": len(request.emails),
                "analysis_type": "full",
                "status": "completed",
                "created_at": current_time,
            }
        )

        logging.info(
            {
                **context,
                "action": "email_analysis_complete",
                "username": request.username,
                "analysis_id": analysis_id,
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


def get_user_analyses(context: Dict, username: str) -> Tuple[int, Dict]:
    try:
        # Get user's analysis history
        analyses = list(
            mongo.user_analysis_history.find({"username": username}, {"_id": 0}).sort(
                "created_at", -1
            )
        )

        return 200, {
            "message": constant.ANALYSIS_HISTORY_FETCH_SUCCESS,
            "data": {
                "username": username,
                "total_analyses": len(analyses),
                "analyses": analyses,
            },
        }

    except Exception as e:
        logging.exception(
            {**context, "action": "get_user_analyses_failed", "error": str(e)}
        )
        return 400, {"message": constant.PROCESSING_ERROR}


def get_analysis_by_id(context: Dict, analysis_id: str) -> Tuple[int, Dict]:
    try:
        # Get specific analysis
        analysis = mongo.email_analysis_collection.find_one(
            {"analysis_id": analysis_id}
        )

        if not analysis:
            return 404, {"message": constant.RECORD_NOT_FOUND}

        return 200, {"message": constant.ANALYSIS_FETCH_SUCCESS, "data": analysis}

    except Exception as e:
        logging.exception({**context, "action": "get_analysis_failed", "error": str(e)})
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


def get_latest_analysis(context: Dict, username: str) -> Tuple[int, Dict]:
    try:
        # Get user's latest analysis
        latest_analysis = mongo.email_analysis_collection.find_one(
            {"username": username}, sort=[("created_at", -1)]
        )

        if not latest_analysis:
            return 404, {"message": constant.RECORD_NOT_FOUND}

        return 200, {
            "message": constant.ANALYSIS_FETCH_SUCCESS,
            "data": latest_analysis,
        }

    except Exception as e:
        logging.exception(
            {**context, "action": "get_latest_analysis_failed", "error": str(e)}
        )
        return 400, {"message": constant.PROCESSING_ERROR}


def get_analysis_summary(context: Dict, username: str) -> Tuple[int, Dict]:
    try:
        # Get analysis statistics
        pipeline = [
            {"$match": {"username": username}},
            {
                "$group": {
                    "_id": None,
                    "total_analyses": {"$sum": 1},
                    "total_emails_analyzed": {"$sum": "$email_count"},
                    "latest_analysis_date": {"$max": "$analysis_date"},
                    "first_analysis_date": {"$min": "$analysis_date"},
                }
            },
        ]

        summary = list(mongo.email_analysis_collection.aggregate(pipeline))

        if not summary:
            return 404, {"message": constant.RECORD_NOT_FOUND}

        return 200, {
            "message": constant.ANALYSIS_SUMMARY_FETCH_SUCCESS,
            "data": summary[0],
        }

    except Exception as e:
        logging.exception(
            {**context, "action": "get_analysis_summary_failed", "error": str(e)}
        )
        return 400, {"message": constant.PROCESSING_ERROR}
