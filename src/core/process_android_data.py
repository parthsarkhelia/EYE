import logging
import uuid
import time
from typing import Dict, Tuple
from pymongo import MongoClient
from src.secrets import secrets
from src.utils import computation, constant, parallel, utils

KEY_SUCCESS = "success"
KEY_STATUS = "status"


async def bureau_eye_submit(context, device_data, auth_credential: str) -> Dict:
    try:
        """Process Android device data and perform necessary operations"""
        device_fingerprint_response = await get_device_insights(
            device_data=device_data, auth_credential=auth_credential
        )

        if device_fingerprint_response[KEY_STATUS] != KEY_SUCCESS:
            return utils.create_response(
                status="error",
                error="Internal Server Error",
                message=f"Failed to fetch device insights: {device_fingerprint_response["message"]}",
                resp=device_fingerprint_response,
            )

        package_name_list = utils.get_package_names(
            device_data["packageManagerInfo_"]["userApplicationList_"]
        )
        carrier_info = device_data["systemProperties_"]["systemProperties"]
        userId = device_data["userId_"]

        logging.info(
            {
                "message": "succesfully fetched device insights!",
                "response": device_fingerprint_response,
            }
        )

        name, phone_number, email = await get_user_details_from_userId(userId)

        alt_data_requests = parallel.get_alt_data_requests(phone_number, name, email)

        service_response = await parallel.get_alternate_service_response(
            alt_data_requests
        )

        logging.info({"message": "succesfully fetched alternate data response!"})

        risk_model_response = parallel.get_risk_service_response(
            service_response=service_response,
            phone_number=phone_number,
            name=name,
            email=email,
        )

        logging.info({"message": "succesfully fetched risk model response!"})
        signals_output = parallel.get_signals_response(
            service_response=service_response, risk_model_response=risk_model_response
        )
        account_list = utils.get_account_list(signals_output)
        final_score_response = computation.calculate_final_score(
            alternate_risk_score=signals_output[constant.ALTERNATE_RISK_SCORE],
            device_risk_level=device_fingerprint_response["response"]["response"][
                "riskLevel"
            ],
            name_from_input=name,
            name_from_alt_data=signals_output[constant.NAME],
            network_from_device=carrier_info,
            network_from_alt_data=signals_output[constant.CURRENT_NETWORK_NAME],
            downloaded_apps=package_name_list,
            account_apps=account_list,
        )

        logging.info(
            {
                "message": "succesfully computed final score",
                "final_score": final_score_response["final_score"],
            }
        )
        updateUserEvaluation(
            userId=userId,
            final_score_response=final_score_response,
            risk_signals=device_fingerprint_response["response"]["response"]["riskCauses"],
        )
        return utils.create_response(
            status=KEY_SUCCESS,
            message="succesfully computed final score",
            resp=final_score_response,
        )

    except Exception as e:
        logging.exception(
            {"Exception": "failed to process device data", "description": str(e)}
        )
        return utils.create_response(
            status="error", error="Internal Server Error", message=str(e)
        )


async def get_device_insights(device_data: dict, auth_credential: str) -> Dict:
    try:
        url = "https://api.stg.bureau.id/v1/deviceService/deviceData/android"
        user_ip = device_data["networkInfo_"]["iPV4_"]
        session_id = str(uuid.uuid4())  # todo: add uniqueness in SDK
        device_data["sessionId_"] = session_id

        headers = {
            "Content-Type": "application/json",
            "X-Bureau-Auth-Credential-ID": auth_credential,
            "X-Bureau-Client-Ip": user_ip,
        }
        device_response = utils.do_http_request(
            url=url, headers=headers, request_body=device_data, request_type="POST"
        )
        if device_response[KEY_STATUS] == KEY_SUCCESS:
            get_url = "https://api.stg.bureau.id/v1/suppliers/device-fingerprint"
            headers = {
                "Content-Type": "application/json",
                "Authorization": secrets["authorization_key"],
            }
            request_body = {
                "sessionId": session_id,
            }

            device_insights_response = utils.do_http_request(
                url=get_url,
                headers=headers,
                request_body=request_body,
                request_type="POST",
            )
            if device_insights_response[KEY_STATUS] == KEY_SUCCESS:
                return utils.create_response(
                    status="success",
                    message="Succesfully done post!",
                    resp=device_insights_response,
                )
            else:
                logging.error(
                    {
                        "message": "failed to get device session insights",
                        "error": device_insights_response["error"],
                        "description": device_insights_response["message"],
                    }
                )
                return utils.create_response(
                    status="error",
                    message="failed to get device insights!",
                    error="Internal Server Error",
                    resp=device_insights_response,
                )
        else:
            logging.error(
                {
                    "error": "failed to post device data",
                    "description": device_response["message"],
                }
            )
            return utils.create_response(
                status="error",
                message=f"failed to submit device data: {device_response['message']}",
                error="Internal Server Error",
                resp=device_response,
            )
    except Exception as e:
        logging.exception(
            {
                "Exception": "failed to post device data",
                "description": str(e),
            }
        )
        return utils.create_response(
            status="error",
            error="Internal Server Error",
            message=f"Got Exception: {str(e)}",
        )

from typing import Tuple, Optional

async def get_user_details_from_userId(userId: str) -> Tuple[str, str, str]:
    try:
        # Split string by underscore
        components = userId.split("_")

        if len(components) != 3:
            raise ValueError(
                "Invalid userId format. Expected format: name_phoneNumber_email"
            )

        name, phone_number, email = components

        if len(phone_number) < 12:
            raise ValueError("Invalid phone number")

        if "@" not in email:
            raise ValueError("Invalid email format")

        return name, phone_number, email

    except Exception as e:
        logging.exception({
            "message": "failed to parse userId",
            "Exception": str(e)
        })
        raise ValueError(f"Failed to parse userId: {str(e)}")       
    
def updateUserEvaluation(userId: str, final_score_response, risk_signals: list):
    client = MongoClient(secrets["mongodb_conn_string"])
    db = client['BureauEYE']
    collection = db['user_evaluation']  
    update_data = {
            "userID": userId,
            "finalScore": final_score_response["final_score"],
            "computedScores": {
                "riskScore": final_score_response["component_scores"]["risk_score"],
                "deviceRiskScore": final_score_response["component_scores"]["device_risk_score"],
                "inputValidationScore": final_score_response["component_scores"]["input_validation_score"],
                "networkValidationScore": final_score_response["component_scores"]["network_validation_score"],
                "appScore": final_score_response["component_scores"]["app_score"],
            },
            "riskSignals": risk_signals,
            "createdAt": int(time.time() * 1000)
        }
    transactions = collection.insert_one(update_data)
    client.close()
    return transactions