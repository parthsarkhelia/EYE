from typing import List

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    detail: str


class BlacklistTokens(BaseModel):
    tokens: List[str]
