import logging
from datetime import datetime
from enum import Enum
from typing import Dict, Tuple

from bson import ObjectId
from pymongo import MongoClient

from src.core import mongo
from src.lib.email_classifier import EmailAnalyzer
from src.models.email_analysis import EmailAnalysisRequest, StoredEmailAnalysisRequest
from src.secrets import secrets
from src.utils import constant


class AnalysisState(Enum):
    INITIALIZED = "initialized"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


async def create_analysis_from_stored_emails(
    context: Dict, request: StoredEmailAnalysisRequest
) -> Tuple[int, Dict]:
    try:
        analysis_id = str(ObjectId())
        stored_emails = mongo.processed_emails.find(
            {"unique_id": request.unique_id}
        ).to_list(None)

        if not stored_emails:
            return 404, {"message": "No emails found for the provided unique_id"}

        analysis_record = {
            "analysis_id": analysis_id,
            "user_id": request.user_id,
            "unique_id": request.unique_id,
            "status": AnalysisState.INITIALIZED.value,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "email_count": len(stored_emails),
            "processed_count": 0,
            "settings": request.settings.dict(),
            "error": None,
        }

        mongo.email_analysis_collection.insert_one(analysis_record)

        # Update status to processing
        mongo.email_analysis_collection.update_one(
            {"analysis_id": analysis_id},
            {
                "$set": {
                    "status": AnalysisState.PROCESSING.value,
                    "updated_at": datetime.now(),
                }
            },
        )

        service = EmailAnalyzer()
        analysis_results = await service.analyze_emails(stored_emails)

        logging.info(
            {
                **context,
                "action": "create_analysis_session",
                "results": analysis_results,
            }
        )

        # Store results and update status
        mongo.email_analysis_collection.update_one(
            {"analysis_id": analysis_id},
            {
                "$set": {
                    "status": AnalysisState.COMPLETED.value,
                    "updated_at": datetime.now(),
                    "results": analysis_results,
                    "processed_count": len(stored_emails),
                }
            },
        )

        return 200, {
            "message": constant.ANALYSIS_COMPLETED,
            "analysis_id": analysis_id,
            "status": AnalysisState.COMPLETED.value,
        }

    except Exception as e:
        mongo.email_analysis_collection.update_one(
            {"analysis_id": analysis_id},
            {
                "$set": {
                    "status": AnalysisState.FAILED.value,
                    "error": str(e),
                    "updated_at": datetime.now(),
                }
            },
        )
        logging.exception(
            {**context, "action": "create_analysis_session_failed", "error": str(e)}
        )
        return 500, {"message": constant.PROCESSING_ERROR}


async def create_analysis_from_request(
    context: Dict, request: EmailAnalysisRequest
) -> Tuple[int, Dict]:
    try:
        analysis_id = str(ObjectId())
        analysis_record = {
            "analysis_id": analysis_id,
            "user_id": request.user_id,
            "status": AnalysisState.INITIALIZED.value,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "email_count": len(request.emails),
            "processed_count": 0,
            "settings": {
                "analyze_credit": request.analyze_credit,
                "analyze_spending": request.analyze_spending,
                "analyze_identity": request.analyze_identity,
                "analyze_portfolio": request.analyze_portfolio,
                "analyze_travel": request.analyze_travel,
            },
            "error": None,
        }

        mongo.email_analysis_collection.insert_one(analysis_record)

        # Update status to processing
        mongo.email_analysis_collection.update_one(
            {"analysis_id": analysis_id},
            {
                "$set": {
                    "status": AnalysisState.PROCESSING.value,
                    "updated_at": datetime.now(),
                }
            },
        )

        service = EmailAnalyzer()
        analysis_results = await service.analyze_emails(request.emails)

        # Store results and update status
        mongo.email_analysis_collection.update_one(
            {"analysis_id": analysis_id},
            {
                "$set": {
                    "status": AnalysisState.COMPLETED.value,
                    "updated_at": datetime.now(),
                    "results": analysis_results,
                    "processed_count": len(request.emails),
                }
            },
        )

        return 200, {
            "message": constant.ANALYSIS_COMPLETED,
            "analysis_id": analysis_id,
            "status": AnalysisState.COMPLETED.value,
        }

    except Exception as e:
        mongo.email_analysis_collection.update_one(
            {"analysis_id": analysis_id},
            {
                "$set": {
                    "status": AnalysisState.FAILED.value,
                    "error": str(e),
                    "updated_at": datetime.now(),
                }
            },
        )
        logging.exception(
            {**context, "action": "create_analysis_session_failed", "error": str(e)}
        )
        return 500, {"message": constant.PROCESSING_ERROR}


async def resume_analysis(
    context: Dict, analysis_id: str, access_token: str = None
) -> Tuple[int, Dict]:
    try:
        analysis = mongo.email_analysis_collection.find_one(
            {"analysis_id": analysis_id}
        )
        if not analysis:
            return 404, {"message": "Analysis not found"}

        if analysis["status"] not in [
            AnalysisState.FAILED.value,
            AnalysisState.INITIALIZED.value,
        ]:
            return 400, {"message": "Analysis cannot be resumed in current state"}

        mongo.email_analysis_collection.update_one(
            {"analysis_id": analysis_id},
            {
                "$set": {
                    "status": AnalysisState.PROCESSING.value,
                    "updated_at": datetime.now(),
                }
            },
        )

        # Re-run analysis
        emails = mongo.processed_emails.find(
            {"unique_id": analysis["unique_id"]}
        ).to_list(None)
        service = EmailAnalyzer()
        result = await service.analyze_emails(emails)

        mongo.email_analysis_collection.update_one(
            {"analysis_id": analysis_id},
            {
                "$set": {
                    "status": AnalysisState.COMPLETED.value,
                    "results": result,
                    "updated_at": datetime.now(),
                }
            },
        )

        return 200, {
            "message": "Analysis resumed successfully",
            "status": AnalysisState.COMPLETED.value,
        }

    except Exception as e:
        logging.exception(
            {**context, "action": "resume_analysis_failed", "error": str(e)}
        )
        return 500, {"message": constant.PROCESSING_ERROR}


async def get_analysis_status(context: Dict, analysis_id: str) -> Tuple[int, Dict]:
    try:
        analysis = mongo.email_analysis_collection.find_one(
            {"analysis_id": analysis_id},
            {"status": 1, "email_count": 1, "processed_count": 1, "error": 1},
        )

        if not analysis:
            return 404, {"message": "Analysis not found"}

        return 200, {
            "status": analysis["status"],
            "progress": {
                "total": analysis["email_count"],
                "processed": analysis["processed_count"],
                "percentage": round(
                    (analysis["processed_count"] / analysis["email_count"]) * 100, 2
                ),
            },
            "error": analysis.get("error"),
        }

    except Exception as e:
        logging.exception(
            {**context, "action": "get_analysis_status_failed", "error": str(e)}
        )
        return 500, {"message": constant.PROCESSING_ERROR}


async def get_analysis_results(context: Dict, analysis_id: str) -> Tuple[int, Dict]:
    try:
        analysis = mongo.email_analysis_collection.find_one(
            {"analysis_id": analysis_id}
        )

        if not analysis:
            return 404, {"message": "Analysis not found"}

        if analysis["status"] != AnalysisState.COMPLETED.value:
            return 400, {"message": "Analysis results not ready"}

        return 200, {"results": analysis.get("results", {})}

    except Exception as e:
        logging.exception(
            {**context, "action": "get_analysis_results_failed", "error": str(e)}
        )
        return 500, {"message": constant.PROCESSING_ERROR}


async def get_user_analyses(
    context: Dict, user_id: str, page: int = 1, limit: int = 10
) -> Tuple[int, Dict]:
    try:
        skip = (page - 1) * limit
        analyses = (
            mongo.email_analysis_collection.find({"user_id": user_id}, {"_id": 0})
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
            .to_list(None)
        )

        total = mongo.email_analysis_collection.count_documents({"user_id": user_id})

        return 200, {
            "analyses": analyses,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": -(-total // limit),  # Ceiling division
            },
        }

    except Exception as e:
        logging.exception(
            {**context, "action": "get_user_analyses_failed", "error": str(e)}
        )
        return 500, {"message": constant.PROCESSING_ERROR}


async def delete_analysis(context: Dict, analysis_id: str) -> Tuple[int, Dict]:
    try:
        result = mongo.email_analysis_collection.delete_one(
            {"analysis_id": analysis_id}
        )

        if result.deleted_count == 0:
            return 404, {"message": "Analysis not found"}

        return 200, {"message": "Analysis deleted successfully"}

    except Exception as e:
        logging.exception(
            {**context, "action": "delete_analysis_failed", "error": str(e)}
        )
        return 500, {"message": constant.PROCESSING_ERROR}


async def get_all_details(context: Dict) -> (int, dict):
    try:
        response = {}
        emailAnalysisDetails = fetchEmailAnalysisDetail()
        logging.info("In Internal")
        logging.info({"emailAnalysisDetails": emailAnalysisDetails})
        for emailAnalysisDetail in emailAnalysisDetails:
            output = {}
            output["emailAnalysis"] = emailAnalysisDetail
            output["userEvaluation"] = fetchUserEvaluation(
                emailAnalysisDetail.get("user_id")
            )
            response[emailAnalysisDetail.get("user_id")] = output
        return 200, response
    except Exception as e:
        logging.exception(
            {**context, "action": "delete_analysis_failed", "error": str(e)}
        )
        return 500, {"message": constant.PROCESSING_ERROR}


def fetchEmailAnalysisDetail():
    emailAnalysisDetails = mongo.email_analysis_collection.find().to_list(None)
    # Iterate over the cursor and remove the _id field
    for emailAnalysisDetail in emailAnalysisDetails:
        emailAnalysisDetail.pop("_id")
    return emailAnalysisDetails


def fetchUserEvaluation(user_id):
    userEvaluation = mongo.user_evaluation.find_one({"userID": user_id})
    if userEvaluation:
        userEvaluation.pop("_id")
    return userEvaluation
