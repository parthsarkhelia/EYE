from src.core import process_android_data
from src.utils import utils


async def handle_bureau_eye_submit(
    context,
    response,
    device_data: dict,
    auth_credential: str,
) -> dict:
    response.status_code = 500
    try:
        # Validate device data
        validate_device_data(device_data)

        # Process data through service
        result = await process_android_data.bureau_eye_submit(
            context=context, device_data=device_data, auth_credential=auth_credential
        )
        result["sessionId"] = device_data["sessionId_"]
        response.status_code = 200
        return result

    except ValueError as e:
        response.status_code = 400
        return utils.create_response(
            status="error", error="Validation Error", message=str(e)
        )
    except Exception as e:
        return utils.create_response(
            status="error", error="Internal Server Error", message=str(e)
        )


def validate_device_data(device_data):
    if not device_data["sessionId_"]:
        raise ValueError("Session ID is required")
    if not device_data["userId_"]:
        raise ValueError("User ID is required")
