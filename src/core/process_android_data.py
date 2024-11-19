from http import HTTPStatus
import json
import logging
from typing import Dict, Optional
from datetime import datetime
import uuid
from src.utils import utils,parallel
import requests
import logging   
from src.secrets import secrets

KEY_SUCCESS = "success"
KEY_STATUS = "status"

async def bureau_eye_submit(
    context,
    device_data,
    auth_credential: str
) -> Dict:
    try:
        """Process Android device data and perform necessary operations"""
        user_application_data = device_data["packageManagerInfo_"]["userApplicationList_"]
        userId = device_data["userId_"]
        device_fingerprint_response = await get_device_insights(device_data=device_data,auth_credential=auth_credential)
        
        if device_fingerprint_response[KEY_STATUS] != KEY_SUCCESS:
            return utils.create_response(
                status="error",
                error="Internal Server Error",
                message=f"Failed to fetch device insights: {device_fingerprint_response["message"]}",
                response=device_fingerprint_response
            )
        logging.info("succesfully fetched device insights!") 
        
        name, phone_number, email = await get_user_details_from_userId(userId)
        logging.info("fetched user details from userId",name,phone_number,email)
        
        alt_data_requests = parallel.get_alt_data_requests(phone_number,name,email)
        
        sevice_response= parallel.get_alternate_service_response(alt_data_requests)
        logging.info({"Service Response":sevice_response})

        risk_model_response=parallel.get_risk_service_response(service_response=sevice_response)
        logging.info({"risk_model_response":risk_model_response})
        if risk_model_response==None:
            raise Exception("Didn't get response from risk model")
        
        
    except Exception as e:
        return utils.create_response(
            status="error",
            error="Internal Server Error",
            message=str(e)
        )
        
async def get_device_insights(
    device_data: dict, 
    auth_credential: str
) -> Dict:
    try: 
        url = "https://api.stg.bureau.id/v1/deviceService/deviceData/android"
        user_ip = device_data["networkInfo_"]["iPV4_"]
        session_id = uuid.uuid4() # todo: add uniqueness in SDK
        device_data['sessionId_'] = session_id
        
        headers = {
            'Content-Type': 'application/json',
            'X-Bureau-Auth-Credential-ID': auth_credential,
            'X-Bureau-Client-Ip' : user_ip
        }
        device_response = utils.do_http_request(
            url=url, 
            headers=headers, 
            request_body=device_data,
            request_type="POST"
        )
        
        if device_response[KEY_STATUS] == KEY_SUCCESS:
            get_url = "https://api.stg.bureau.id/v1/suppliers/device-fingerprint"
            headers = {
                'Content-Type': 'application/json',
                'Authorization': secrets['authorization_key'],
            }
            request_body = {
                "sessionId": session_id,
            }
            
            device_insights_response = utils.do_http_request(
                url=get_url, 
                headers=headers, 
                request_body=request_body,
                request_type="POST"
            )
            if device_insights_response[KEY_STATUS] == KEY_SUCCESS:
                return utils.create_response(
                    status="success",
                    message="Succesfully done post!",
                    response=device_insights_response
                )
            else:
                logging.error({
                    "message": "failed to get device session insights",
                    "error": device_insights_response["error"],
                    "description": device_insights_response["message"],
                })
                return utils.create_response(
                    status="error",
                    message="failed to get device insights!",
                    error="Internal Server Error",
                    response=device_insights_response
                )
        else:
            logging.error({
                "error":"failed to post device data",
                "description":device_response["message"],
            })
            return utils.create_response(
                status="error",
                message=f"failed to submit device data: {device_response['message']}",
                error="Internal Server Error",
                response=device_response
            )
    except Exception as e:
        logging.exception({
            "Exception": "failed to post device data",
            "description":str(e),
        })
        return utils.create_response(
            status="error",
            error="Internal Server Error",
            message=f"Got Exception: {str(e)}"
        )
   
from typing import Tuple, Optional

async def get_user_details_from_userId(userId: str) -> Tuple[str, str, str]:
    try:
        # Split string by underscore
        components = userId.split('_')
        print("DhruvLogs: ",components)
        
        if len(components) != 3:
            raise ValueError("Invalid userId format. Expected format: name_phoneNumber_email")
            
        name, phone_number, email = components
        
        print(f"{name}, {phone_number}, {email}")
        
        if '@' not in email:
            raise ValueError("Invalid email format")
        
        print("Split ho gaya oye!")
        
        return name, phone_number, email
        
    except Exception as e:
        raise ValueError(f"Failed to parse userId: {str(e)}")       
     
    

   