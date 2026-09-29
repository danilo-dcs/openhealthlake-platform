from typing import Optional
from pydantic import BaseModel

class GetTokenPayload(BaseModel):
    email: str
    password: str

# class RefreshTokenPayload(BaseModel):
#     refresh_token: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_email: str = None
    user_id: str = None
    exp: int = None
    sub: str = None
    user_role: str = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    # refresh_token: Optional[str] = None

class UserTokenResponse(TokenResponse):
    user_id: str
    user_role: Optional[str] = None
    user_email: Optional[str] = None

class AuthenticationHeader(BaseModel):
    Authorization: str