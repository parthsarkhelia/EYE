from typing import Dict, Optional
from datetime import datetime
import logging

from src import utils    
from src.utils.parallel import get_alternate_service_response,endpoints_to_call,get_risk_service_response

async def bureau_eye_submit(
    self,
    decrypted_device_data: any,
    encrypted_device_data: str,
    api_version: str,
    auth_credential: str
) -> Dict:
    try:
        """Process Android device data and perform necessary operations"""
        user_application_data = decrypted_device_data["packageManagerInfo_"]["userApplicationList_"]
        device_fingerprint_response = get_device_insights()
        sevice_response=get_alternate_service_response(endpoints_to_call)
        logging.info({"Service Resposne":sevice_response})

        risk_model_response=get_risk_service_response(service_response=sevice_response)
        if risk_model_response==None:
            raise Exception("Didn't get response from risk model")
        
        
    except Exception as e:
        return utils.create_response(
            status="error",
            error="Internal Server Error",
            message=str(e)
        )
        
def get_device_insights(encrypted_device_data: any, api_version: str) -> Dict:
    try: 
        print("unimplemented")
    except Exception as e:
        return utils.create_response(
            status="error",
            error="Internal Server Error",
            message=str(e)
        )
        
     
    

   