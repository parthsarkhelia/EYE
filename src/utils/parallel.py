import asyncio
import aiohttp
from typing import List, Dict
import time
import requests
import logging
import json

from src.utils import constant


async def make_post_request(
    session: aiohttp.ClientSession, url: str, data: Dict, headers: Dict = None
) -> Dict:
    """
    Make a single POST request

    Args:
        session: aiohttp client session
        url: API endpoint
        data: POST request body
        headers: Request headers
    """
    try:
        async with session.post(url, json=data, headers=headers) as response:
            return {
                "url": url,
                "status": response.status,
                "data": await response.json(),
            }
    except Exception as e:
        return {"url": url, "status": "error", "error": str(e)}


async def call_apis_parallel(endpoints: List[Dict]) -> Dict:
    """
    Call multiple API endpoints in parallel

    Args:
        endpoints: List of dictionaries containing url and data for each endpoint
        headers: Common headers for all requests
    """
    async with aiohttp.ClientSession() as session:
        tasks = [
            make_post_request(
                session=session,
                url=endpoint["url"],
                data=endpoint["data"],
                headers=endpoint["headers"],
            )
            for endpoint in endpoints
        ]
        responses = await asyncio.gather(*tasks)

        # Merge responses
        merged_response = {"success": {}, "failed": {}, "execution_time": 0}

        for response in responses:
            if response["status"] == "error" or response["status"] >= 400:
                merged_response["failed"][response["url"]] = {
                    "error": response.get("error", f"{response}")
                }
            else:
                merged_response["success"][response["url"]] = response["data"]

        return merged_response

async def get_alternate_service_response(endpoints: List[Dict]):
    return await call_apis_parallel(endpoints)

def get_alt_data_requests(phone, name, email):
    return [
        {
            "url": "https://api.overwatch.stg.bureau.id/v2/services/email-intelligence",
            "data": {"email": email},
            "headers": {
                "Authorization": "Basic Zjg0MzAxMmItNWMxZC00MTgyLWIwMDktN2FkY2FhNTVlZmJhOjAzNzdhOGZlLTNiZDktNDkyZC1iZjI1LTlkN2VkZTAwYmM3Zg==",
                "Content-Type": "application/json",
            },
        },
        {
            "url": "https://api.overwatch.stg.bureau.id/v2/services/email-name-attributes",
            "data": {
                "name": name,
                "email": email,
            },
            "headers": {
                "Authorization": "Basic Zjg0MzAxMmItNWMxZC00MTgyLWIwMDktN2FkY2FhNTVlZmJhOjAzNzdhOGZlLTNiZDktNDkyZC1iZjI1LTlkN2VkZTAwYmM3Zg==",
                "Content-Type": "application/json",
            },
        },
        {
            "url": "https://api.overwatch.stg.bureau.id/v2/services/email-social-advance",
            "data": {"email": email},
            "headers": {
                "Authorization": "Basic Zjg0MzAxMmItNWMxZC00MTgyLWIwMDktN2FkY2FhNTVlZmJhOjAzNzdhOGZlLTNiZDktNDkyZC1iZjI1LTlkN2VkZTAwYmM3Zg==",
                "Content-Type": "application/json",
            },
        },
        {
            "url": "https://api.overwatch.stg.bureau.id/v2/services/phone-name",
            "data": {"phoneNumber": phone, "countryCode": "IND"},
            "headers": {
                "Authorization": "Basic Zjg0MzAxMmItNWMxZC00MTgyLWIwMDktN2FkY2FhNTVlZmJhOjAzNzdhOGZlLTNiZDktNDkyZC1iZjI1LTlkN2VkZTAwYmM3Zg==",
                "Content-Type": "application/json",
            },
        },
        {
            "url": "https://api.overwatch.stg.bureau.id/v2/services/phone-name-attributes",
            "data": {
                "name": name,
                "phoneNumber": phone,
                "serviceType": "PREMIUM_QUICK",
            },
            "headers": {
                "Authorization": "Basic Zjg0MzAxMmItNWMxZC00MTgyLWIwMDktN2FkY2FhNTVlZmJhOjAzNzdhOGZlLTNiZDktNDkyZC1iZjI1LTlkN2VkZTAwYmM3Zg==",
                "Content-Type": "application/json",
            },
        },
        {
            "url": "https://api.overwatch.stg.bureau.id/v2/services/phone-social-advance",
            "data": {
                "phoneNumber": phone,
                "countryCode": "IND",
                "requestedServices": [],
            },
            "headers": {
                "Authorization": "Basic Zjg0MzAxMmItNWMxZC00MTgyLWIwMDktN2FkY2FhNTVlZmJhOjAzNzdhOGZlLTNiZDktNDkyZC1iZjI1LTlkN2VkZTAwYmM3Zg==",
                "Content-Type": "application/json",
            },
        },
        {
            "url": "https://api.overwatch.stg.bureau.id/v2/services/phone-network",
            "data": {"phoneNumber": phone},
            "headers": {
                "Authorization": "Basic Zjg0MzAxMmItNWMxZC00MTgyLWIwMDktN2FkY2FhNTVlZmJhOjAzNzdhOGZlLTNiZDktNDkyZC1iZjI1LTlkN2VkZTAwYmM3Zg==",
                "Content-Type": "application/json",
            },
        },
    ]

def get_signals_response(service_response,risk_model_response):
    
    phone_name_service =service_response.get("success",{}).get("https://api.overwatch.stg.bureau.id/v2/services/phone-name",{})
    phone_social_advance_service =service_response.get("success",{}).get("https://api.overwatch.stg.bureau.id/v2/services/phone-social-advance",{})
    phone_network_service =service_response.get("success",{}).get("https://api.overwatch.stg.bureau.id/v2/services/phone-network",{})

    whatsapp_business_presence_final="0"
    whatsapp_business_presence=phone_social_advance_service.get("isWABusiness","Error")

    if whatsapp_business_presence=="Account Found":
        whatsapp_business_presence_final="1"
    elif whatsapp_business_presence=="Account Not Found":
        whatsapp_business_presence_final="0"

    names = phone_name_service.get("names",[""]),
        
    return {
        constant.NAME: names[0],
        constant.CURRENT_NETWORK_NAME: phone_network_service.get("currentNetworkName",""),
        constant.PHONE_WHATSAPP: phone_social_advance_service.get("whatsapp","Error"),
        constant.PHONE_INSTAGRAM: phone_social_advance_service.get("instagram","Error"),
        constant.PHONE_AMAZON: phone_social_advance_service.get("amazon","Error"),
        constant.PHONE_PAYTM:  phone_social_advance_service.get("paytm","Error"),
        constant.PHONE_FLIPKART:  phone_social_advance_service.get("flipkart","Error"),
        constant.PHONE_INDIAMART: phone_social_advance_service.get("indiamart","Error"),
        constant.PHONE_JEEVANSAATHI: phone_social_advance_service.get("jeevansaathi","Error"),
        constant.PHONE_JIOMART:  phone_social_advance_service.get("jiomart","Error"),
        constant.PHONE_SHAADI:  phone_social_advance_service.get("shaadi","Error"),
        constant.PHONE_SWIGGY: phone_social_advance_service.get("swiggy","Error"),
        constant.PHONE_TOI: phone_social_advance_service.get("toi","Error"),
        constant.PHONE_YATRA: phone_social_advance_service.get("yatra","Error"),
        constant.PHONE_ZOHO: phone_social_advance_service.get("zoho","Error"),
        constant.PHONE_WHATSAPPBUSINESS: whatsapp_business_presence_final,
        constant.ALTERNATE_RISK_SCORE: risk_model_response.get("alternateRiskScore",0),
    }


def get_risk_service_response(service_response,phone_number,name,email):
    
    email_intelligence_service =service_response.get("success",{}).get("https://api.overwatch.stg.bureau.id/v2/services/email-intelligence",{})
    email_name_attributes_service =service_response.get("success",{}).get("https://api.overwatch.stg.bureau.id/v2/services/email-name-attributes",{})
    email_social_advance_service =service_response.get("success",{}).get("https://api.overwatch.stg.bureau.id/v2/services/email-social-advance",{})
    phone_name_service =service_response.get("success",{}).get("https://api.overwatch.stg.bureau.id/v2/services/phone-name",{})
    phone_name_attributes_service =service_response.get("success",{}).get("https://api.overwatch.stg.bureau.id/v2/services/phone-name-attributes",{})
    phone_social_advance_service =service_response.get("success",{}).get("https://api.overwatch.stg.bureau.id/v2/services/phone-social-advance",{})
    phone_network_service =service_response.get("success",{}).get("https://api.overwatch.stg.bureau.id/v2/services/phone-network",{})

    url = "https://api.overwatch.stg.bureau.id/v2/services/riskmodel"
    whatsapp_business_presence_final=-1
    whatsapp_business_presence=phone_social_advance_service.get("isWABusiness","Error")

    if whatsapp_business_presence=="Account Found":
        whatsapp_business_presence_final="1"
    elif whatsapp_business_presence=="Account Not Found":
        whatsapp_business_presence_final="0"

    
    payload = json.dumps({
    "name": name,
    "phone": phone_number,
    "email": email,

    "currentNetworkName": phone_network_service.get("currentNetworkName",""),
    "currentNetworkBillingType":phone_network_service.get("numberBillingType",""),
    "isPhoneReachable": phone_network_service.get("isPhoneReachable",""),
    "ported": phone_network_service.get("numberHasPortingHistory",""),
    "roaming": phone_network_service.get("roaming",""),

    "emailFinalRecommendation":email_intelligence_service.get("emailFinalRecommendation",""),
    "domainExists": email_intelligence_service.get("domainExists",""),
    "emailExists": email_intelligence_service.get("emailExists",""),

    "phoneWhatsApp": phone_social_advance_service.get("whatsapp","Error"),
    "phoneInstagram": phone_social_advance_service.get("instagram","Error"),
    "phoneAmazon": phone_social_advance_service.get("amazon","Error"),
    "phonePaytm":  phone_social_advance_service.get("paytm","Error"),
    "phoneFlipkart":  phone_social_advance_service.get("flipkart","Error"),
    "phoneIndiamart": phone_social_advance_service.get("indiamart","Error"),
    "phoneJeevansaathi": phone_social_advance_service.get("jeevansaathi","Error"),
    "phoneJiomart":  phone_social_advance_service.get("jiomart","Error"),
    "phoneShaadi":  phone_social_advance_service.get("shaadi","Error"),
    "phoneSwiggy": phone_social_advance_service.get("swiggy","Error"),
    "phoneToi": phone_social_advance_service.get("toi","Error"),
    "phoneYatra": phone_social_advance_service.get("yatra","Error"),
    "phoneZoho": phone_social_advance_service.get("zoho","Error"),
    "phoneWhatsAppBusiness": whatsapp_business_presence_final,

    "emailInstagram": email_social_advance_service.get("instagram","Error"),
    "emailAmazon": email_social_advance_service.get("amazon","Error"),
    "emailPaytm": email_social_advance_service.get("paytm","Error"),
    "emailFlipkart":email_social_advance_service.get("flipkart","Error"),
    "emailHousing": email_social_advance_service.get("housing","Error"),
    "emailJeevansaathi": email_social_advance_service.get("jeevansaathi","Error"),
    "emailShaadi": email_social_advance_service.get("amazon","Error"),
    "emailToi": email_social_advance_service.get("toi","Error"),
    "emailYatra": email_social_advance_service.get("yatra","Error"),
    "emailZoho": email_social_advance_service.get("zoho","Error"),

    "emailDigitalAge": email_name_attributes_service.get("digitalage",""),
    "emailNameMatchScore": email_name_attributes_service.get("nameMatchScore",""),
    "emailUNRScore": email_name_attributes_service.get("unrScore",""),

    "phoneDigitalAge": phone_name_attributes_service.get("digitalage",""),
    "phoneNameMatchScore": phone_name_attributes_service.get("nameMatchScore",""),
    "phoneUNRScore": phone_name_attributes_service.get("unrScore",""),

    "riskModels": [
        "alternate_risk-model_config_1",
        "mule_risk-model_config_2",
        "onboarding_risk-model_config_23"
    ]
    })

    headers = {
    'Authorization': 'Basic ZTBhMmNhYTYtYzFjMy00YTI0LTkzMzktNzc3YzE5MmI3ZWJiOjVkMGM0NDg3LTY4NTItNGRkNi05YWZmLTZkNmEyNWRkMjBkOQ==',
    'Content-Type': 'application/json'
    }

    try:
        response = requests.post(url, headers=headers, data=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        logging.info(f"HTTP error occurred: {http_err}")
        return None
    except requests.exceptions.RequestException as err:
        logging.info(f"Error occurred: {err}")
        return None


