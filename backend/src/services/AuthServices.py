from datetime import datetime, timedelta, timezone
from typing import Literal
from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext

from fastapi import HTTPException, status, Response

from shared.models.authentication import TokenData
from shared.models.env import EnvSettings

class AuthServices:
    def __init__(self, crypto_scheme: Literal["bcrypt", "argon2"] = "bcrypt"):
        self.pwd_context = CryptContext(schemes=crypto_scheme, deprecated="auto")
        self.env_settings = EnvSettings()

    async def authenticate(self, email: str, password: str) -> tuple | None:
        from services.UserServices import UserServices

        userServices = UserServices()

        user = await userServices.list_by_email(email=email)

        if not user:
            return {}

        if not self.pwd_context.verify(password, user.password):
            return {}
    
        user_data = TokenData(user_id=user.id, user_email=user.email, user_role=user.role)

        if not user_data:
            return {}
        
        token = self.create_jwt_token(data=user_data)

        refresh_token = self.create_jwt_token(data=user_data, refresh_token=True)

        if not token:
            return None

        return (token, refresh_token)
    
    async def refresh(self, token_data: TokenData ) -> str:
        if not token_data:
            return {}
        
        token = self.create_jwt_token(data=token_data)

        return token

    def word_to_hash(self, word: str) -> str:
        if len(word.encode("utf-8")) > 72:
            raise ValueError("Password exceeds 72 bytes, must truncate or reject.")

        hashed = self.pwd_context.hash(word)
        return hashed
    
    def create_jwt_token(
        self,
        data: TokenData, 
        expires_diff: timedelta = None, 
        refresh_token: bool = False
    ) -> str:
        if expires_diff:
            expire = datetime.now(timezone.utc) + expires_diff
        else:
            expiry_time = (
                timedelta(days=7)
                if refresh_token
                else timedelta(minutes=self.env_settings.EXPIRATION_TIME_MINUTES)
            )
            expire = datetime.now(timezone.utc) + expiry_time

        to_encode = data.model_copy()

        to_encode.exp = int(expire.timestamp())
        to_encode.sub = data.user_id

        secret_key = self.env_settings.REFRESH_TOKEN_KEY if refresh_token else self.env_settings.AUTH_SECRET_KEY

        encoded_jwt = jwt.encode(
            to_encode.model_dump(exclude_none=True, exclude_unset=True),
            secret_key,
            algorithm=self.env_settings.AUTH_ALGORITHM
        )

        return encoded_jwt
    
    def decode_jwt_token(self, token: str, refresh: bool = False) -> TokenData:
        try:
            secret_key = self.env_settings.REFRESH_TOKEN_KEY if refresh else self.env_settings.AUTH_SECRET_KEY

            decoded_token = jwt.decode(token, secret_key, algorithms=[self.env_settings.AUTH_ALGORITHM])

            if not decoded_token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token",
                    headers={"WWW-Authenticate": "Bearer"},
                )

        except ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return TokenData(**decoded_token)
    
    def set_refresh_cookie(self, response: Response, token: str):
        # response.set_cookie(
        #     key="refresh_token",
        #     value=token,
        #     httponly=True,
        #     secure=True if self.env_settings.BACKEND_ENV == "dev" else False,
        #     samesite="strict" if self.env_settings.BACKEND_ENV == "dev" else "lax",
        #     max_age=7 * 24 * 3600, 
        #     path="/",
        # )
        response.set_cookie(
            key="refresh_token",
            value=token,
            httponly=True,
            secure=self.env_settings.BACKEND_ENV == "prod",
            samesite="lax",
            max_age=7 * 24 * 3600, 
            path="/",
        )

    def clear_refresh_cookie(self, response: Response):
        response.delete_cookie(
            key="refresh_token",
            path="/",
            httponly=True,
            secure=self.env_settings.BACKEND_ENV == "prod",
            samesite="lax",
        )
