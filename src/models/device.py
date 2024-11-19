from pydantic import Field, BaseModel

class SubmitRequestBody(BaseModel):
    payload: str = Field(...,alias="payload")
    aes256_key: str = Field(...,alias="eaIV")
    aes256_iv: str = Field(...,alias="eaKey")