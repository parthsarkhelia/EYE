import json
from src.secrets import secrets
from structs import structs
from src.utils import utils
from src.core import decrypt_device_data,process_android_data


async def bureau_eye_submit(
    context,
    device_data: structs.SubmitRequestBody,
    api_version: str,
    auth_credential: str
) -> dict:
    try:
        validate_encrypted_data(device_data)
        decryptedPayload = decrypt_device_data.decrypt_request_body(api_version,device_data,secrets["aes256_key"],secrets["aes256_iv"], secrets["rsa_private_key"], auth_credential)
        
        # Convert bytes to string and parse JSON
        decrypted_string = decryptedPayload.decode('utf-8')
        decrypted_payload = json.loads(decrypted_string)

        # Validate device data
        validate_device_data(decrypted_payload)
    
        # Process data through service
        result = await process_android_data(
            decrypted_device_data=decrypted_payload,
            encrypted_device_data=device_data,
            api_version=api_version,
            auth_credential=auth_credential
        )
        
        # Return success response
        return utils.create_response(
            status="success",
            session_id=device_data.sessionId_,
            data=result
        )
        
    except ValueError as e:
        return utils.create_response(
            status="error",
            error="Validation Error",
            message=str(e)
        )
    except Exception as e:
        return utils.create_response(
            status="error",
            error="Internal Server Error",
            message=str(e)
        )

def validate_device_data(device_data: any):
    if not device_data["sessionId_"]:
        raise ValueError("Session ID is required")
    if not device_data["userId_"]:
        raise ValueError("Session ID is required")
    
def validate_encrypted_data(device_data: structs.SubmitRequestBody):
    if len(device_data.payload)==0:
        raise ValueError("payload is required")
    if len(device_data.aes256_iv)==0:
        raise ValueError("encryptionIV is required")
    if len(device_data.aes256_key)==0:
        raise ValueError("encryptionKey is required")