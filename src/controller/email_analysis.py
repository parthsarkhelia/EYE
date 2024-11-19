import logging
from datetime import datetime
from typing import Dict, Optional, Tuple

from bson import ObjectId

from src.core import mongo
from src.lib.email_classifier import AnalysisState, EmailAnalyzer
from src.models.email_analysis import EmailAnalysisRequest
from src.utils import constant


async def create_analysis_session(
    context: Dict, request: EmailAnalysisRequest
) -> Tuple[int, Dict]:
    try:
        analysis_id = str(ObjectId())

        # Create initial record
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

        await mongo.email_analysis_records.insert_one(analysis_record)

        # Initialize service
        service = EmailAnalyzer()
        result = await service.start_analysis(analysis_id, request.emails)

        return 200, {
            "message": constant.ANALYSIS_STARTED,
            "analysis_id": analysis_id,
            "status": result["status"],
        }

    except Exception as e:
        logging.error(
            {**context, "action": "create_analysis_session_failed", "error": str(e)}
        )
        return 500, {"message": constant.PROCESSING_ERROR}


async def resume_analysis(
    context: Dict, analysis_id: str, access_token: Optional[str] = None
) -> Tuple[int, Dict]:
    try:
        service = EmailAnalyzer()
        record = await service.get_analysis_status(analysis_id)

        if not record:
            return 404, {"message": constant.RECORD_NOT_FOUND}

        if record["status"] == AnalysisState.TOKEN_EXPIRED.value and not access_token:
            return 400, {"message": constant.TOKEN_REQUIRED}

        result = await service.resume_analysis(analysis_id, access_token)

        return 200, {"message": constant.ANALYSIS_RESUMED, "status": result["status"]}

    except Exception as e:
        logging.error({**context, "action": "resume_analysis_failed", "error": str(e)})
        return 500, {"message": constant.PROCESSING_ERROR}


async def get_analysis_status(context: Dict, analysis_id: str) -> Tuple[int, Dict]:
    try:
        service = EmailAnalyzer()
        status = await service.get_analysis_status(analysis_id)

        if not status:
            return 404, {"message": constant.RECORD_NOT_FOUND}

        return 200, {"message": constant.STATUS_FETCH_SUCCESS, "status": status}

    except Exception as e:
        logging.error({**context, "action": "get_status_failed", "error": str(e)})
        return 500, {"message": constant.PROCESSING_ERROR}


async def get_analysis_results(context: Dict, analysis_id: str) -> Tuple[int, Dict]:
    try:
        service = EmailAnalyzer()
        status = await service.get_analysis_status(analysis_id)

        if not status:
            return 404, {"message": constant.RECORD_NOT_FOUND}

        if status["status"] != AnalysisState.ANALYSIS_COMPLETED.value:
            return 400, {"message": constant.ANALYSIS_NOT_COMPLETE}

        results = await service.get_analysis_results(analysis_id)

        return 200, {"message": constant.RESULTS_FETCH_SUCCESS, "results": results}

    except Exception as e:
        logging.error({**context, "action": "get_results_failed", "error": str(e)})
        return 500, {"message": constant.PROCESSING_ERROR}


async def get_user_analyses(
    context: Dict, user_id: str, page: int, limit: int
) -> Tuple[int, Dict]:
    try:
        skip = (page - 1) * limit

        analyses = (
            await mongo.email_analysis_records.find({"user_id": user_id})
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
            .to_list(length=limit)
        )

        total = await mongo.email_analysis_records.count_documents({"user_id": user_id})

        return 200, {
            "message": constant.ANALYSES_FETCH_SUCCESS,
            "data": {
                "analyses": analyses,
                "total": total,
                "page": page,
                "total_pages": (total + limit - 1) // limit,
            },
        }

    except Exception as e:
        logging.error(
            {**context, "action": "get_user_analyses_failed", "error": str(e)}
        )
        return 500, {"message": constant.PROCESSING_ERROR}


async def delete_analysis(context: Dict, analysis_id: str) -> Tuple[int, Dict]:
    try:
        # Delete analysis record
        result = await mongo.email_analysis_records.delete_one(
            {"analysis_id": analysis_id}
        )

        if result.deleted_count == 0:
            return 404, {"message": constant.RECORD_NOT_FOUND}

        # Delete related data
        await mongo.raw_emails_collection.delete_many({"analysis_id": analysis_id})
        await mongo.analysis_results_collection.delete_many(
            {"analysis_id": analysis_id}
        )

        return 200, {"message": constant.ANALYSIS_DELETED}

    except Exception as e:
        logging.error({**context, "action": "delete_analysis_failed", "error": str(e)})
        return 500, {"message": constant.PROCESSING_ERROR}
