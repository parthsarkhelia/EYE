from pydantic import Field

class SubmitRequestBody:
    payload: any = Field(...,alias="payload")
    aes256_key: str = Field(...,alias="eaIV")
    aes256_iv: str = Field(...,alias="eaKey")