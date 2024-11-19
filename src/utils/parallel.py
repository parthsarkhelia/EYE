import asyncio
import aiohttp
from typing import List, Dict
import time


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


def merged_resposne(endpoints: List[Dict]):
    return asyncio.run(call_apis_parallel(endpoints))


# print(merged_resposne(endpoints_to_call))
endpoints_to_call = [
    {
        "url": "https://api.overwatch.stg.bureau.id/v2/services/email-intelligence",
        "data": {"email": "john.doe@dummy.com"},
        "headers": {
            "Authorization": "Basic Zjg0MzAxMmItNWMxZC00MTgyLWIwMDktN2FkY2FhNTVlZmJhOjAzNzdhOGZlLTNiZDktNDkyZC1iZjI1LTlkN2VkZTAwYmM3Zg==",
            "Content-Type": "application/json",
        },
    },
    {
        "url": "https://api.overwatch.stg.bureau.id/v2/services/email-name-attributes",
        "data": {
            "name": "Anurag Chaubey",
            "email": "anuragchaubey2@gmail.com",
        },
        "headers": {
            "Authorization": "Basic Zjg0MzAxMmItNWMxZC00MTgyLWIwMDktN2FkY2FhNTVlZmJhOjAzNzdhOGZlLTNiZDktNDkyZC1iZjI1LTlkN2VkZTAwYmM3Zg==",
            "Content-Type": "application/json",
        },
    },
    {
        "url": "https://api.overwatch.stg.bureau.id/v2/services/email-social-advance",
        "data": {"email": "rainpatter88@gmail.com"},
        "headers": {
            "Authorization": "Basic Zjg0MzAxMmItNWMxZC00MTgyLWIwMDktN2FkY2FhNTVlZmJhOjAzNzdhOGZlLTNiZDktNDkyZC1iZjI1LTlkN2VkZTAwYmM3Zg==",
            "Content-Type": "application/json",
        },
    },
    {
        "url": "https://api.overwatch.stg.bureau.id/v2/services/phone-name",
        "data": {"phoneNumber": "919408040163", "countryCode": "IND"},
        "headers": {
            "Authorization": "Basic Zjg0MzAxMmItNWMxZC00MTgyLWIwMDktN2FkY2FhNTVlZmJhOjAzNzdhOGZlLTNiZDktNDkyZC1iZjI1LTlkN2VkZTAwYmM3Zg==",
            "Content-Type": "application/json",
        },
    },
    {
        "url": "https://api.overwatch.stg.bureau.id/v2/services/phone-name-attributes",
        "data": {
            "name": "Priyam",
            "phoneNumber": "918309609061",
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
            "phoneNumber": "917289982200",
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
        "data": {"phoneNumber": "919839009836"},
        "headers": {
            "Authorization": "Basic Zjg0MzAxMmItNWMxZC00MTgyLWIwMDktN2FkY2FhNTVlZmJhOjAzNzdhOGZlLTNiZDktNDkyZC1iZjI1LTlkN2VkZTAwYmM3Zg==",
            "Content-Type": "application/json",
        },
    },
]
