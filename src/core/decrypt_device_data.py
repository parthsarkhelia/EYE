from http.client import HTTPException
from cryptography.hazmat.primitives import padding, serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding as asymmetric_padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import base64
import json
from typing import Tuple, Optional
from dataclasses import dataclass
import logging

# Constants
X_BUREAU_API_VERSION_V1 = "1.1.0"
X_BUREAU_API_VERSION_V2 = "2.0.0"

@dataclass
class EncryptedBody:
    payload: str
    encryptedAES256Key: Optional[str] = None
    encryptedAES256IV: Optional[str] = None

def decrypt_v1(payload: str, aes256_key: bytes, aes256_iv: bytes) -> bytes:
    """
    Decrypt payload using AES-256-CBC for version 1
    """
    try:
        # Decode base64 payload
        encrypted_data = base64.b64decode(payload)
        
        # Create AES cipher
        cipher = Cipher(
            algorithms.AES(aes256_key),
            modes.CBC(aes256_iv),
            backend=default_backend()
        )
        
        # Decrypt
        decryptor = cipher.decryptor()
        padded_data = decryptor.update(encrypted_data) + decryptor.finalize()
        
        # Remove padding
        unpadder = padding.PKCS7(128).unpadder()
        data = unpadder.update(padded_data) + unpadder.finalize()
        
        return data
    except Exception as e:
        logger.error(f"Error in decrypt_v1: {str(e)}")
        raise ValueError("Decryption failed")

def decrypt_v2(payload: str, dynamic_aes256_key: bytes, dynamic_aes256_iv: bytes) -> bytes:
    """
    Decrypt payload using AES-256-CBC for version 2
    """
    try:
        # Decode base64 payload
        encrypted_data = base64.b64decode(payload)
        
        # Create AES cipher with dynamic key and IV
        cipher = Cipher(
            algorithms.AES(dynamic_aes256_key),
            modes.CBC(dynamic_aes256_iv),
            backend=default_backend()
        )
        
        # Decrypt
        decryptor = cipher.decryptor()
        padded_data = decryptor.update(encrypted_data) + decryptor.finalize()
        
        # Remove padding
        unpadder = padding.PKCS7(128).unpadder()
        data = unpadder.update(padded_data) + unpadder.finalize()
        
        return data
    except Exception as e:
        logging.error(f"Error in decrypt_v2: {str(e)}")
        raise ValueError("Decryption failed")

def decrypt_rsa_encrypted_secret_string(encrypted_string: str, rsa_private_key_pem: bytes) -> bytes:
    """
    Decrypt RSA encrypted string using private key
    """
    try:
        # Load private key
        private_key = serialization.load_pem_private_key(
            rsa_private_key_pem,
            password=None,
            backend=default_backend()
        )
        
        # Decode base64 encrypted string
        encrypted_data = base64.b64decode(encrypted_string)
        
        # Decrypt
        decrypted_data = private_key.decrypt(
            encrypted_data,
            asymmetric_padding.OAEP(
                mgf=asymmetric_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        return decrypted_data
    except Exception as e:
        logging.error(f"Error in decrypt_rsa_encrypted_secret_string: {str(e)}")
        raise ValueError("RSA decryption failed")

def is_mitm_attack_detected(decrypted_payload: bytes) -> bool:
    """
    Check if MITM attack is detected in the decrypted payload
    """
    try:
        payload_data = json.loads(decrypted_payload)
        return payload_data.get('mitmAttackDetected', False)
    except json.JSONDecodeError:
        return False

async def decrypt_request_body(
    version: str,
    encrypted_body: EncryptedBody,
    aes256_key: bytes,
    aes256_iv: bytes,
    rsa_private_key: bytes,
    client_id: Optional[str] = None
) -> bytes:
    """
    Main function to handle decryption based on version
    """
    try:
        if version == X_BUREAU_API_VERSION_V1:
            # Version 1 decryption
            return decrypt_v1(encrypted_body.payload, aes256_key, aes256_iv)
            
        elif version == X_BUREAU_API_VERSION_V2:
            # Decrypt dynamic AES key and IV using RSA
            dynamic_aes256_key = decrypt_rsa_encrypted_secret_string(
                encrypted_body.encryptedAES256Key,
                rsa_private_key
            )
            dynamic_aes256_iv = decrypt_rsa_encrypted_secret_string(
                encrypted_body.encryptedAES256IV,
                rsa_private_key
            )
            
            # Decrypt payload using dynamic key and IV
            decrypted_payload = decrypt_v2(
                encrypted_body.payload,
                dynamic_aes256_key,
                dynamic_aes256_iv
            )        
            return decrypted_payload
            
        else:
            logging.info(f"Invalid version detected: {version}")
            raise HTTPException(status_code=400, detail="Bad Request")
            
    except ValueError as e:
        logging.error(f"Decryption error: {str(e)}")
        raise HTTPException(status_code=400, detail="Bad Request")
    except Exception as e:
        logging.error(f"Unexpected error during decryption: {str(e)}")
        raise HTTPException(status_code=400, detail="Bad Request")