from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from services.AuthServices import AuthServices
from shared.models.authentication import GetTokenPayload, TokenData, TokenResponse, UserTokenResponse #, handlers

from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel
from fastapi.openapi.models import OAuth2 as OAuth2Model

from shared.handlers.TimeHandler import TimeHandler

auth_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

security_scheme = OAuth2Model(
    flows=OAuthFlowsModel(password={"tokenUrl": "/auth/token"})
)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


@router.post("/login", response_model=UserTokenResponse)
async def login(payload: GetTokenPayload, response: Response):
    authServices = AuthServices()
    tokens = await authServices.authenticate(email=payload.email, password=payload.password)

    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    auth_token, refresh_token = tokens

    decoded_token = authServices.decode_jwt_token(auth_token)

    authServices.set_refresh_cookie(response, refresh_token)

    return UserTokenResponse(
        access_token=auth_token,
        token_type="Bearer",
        user_id=decoded_token.user_id,
        user_role=decoded_token.user_role,
        user_email=decoded_token.user_email
    )

@router.post("/refresh", response_model=UserTokenResponse)
async def refresh(request: Request, response: Response):
    authServices = AuthServices()

    timeHandler = TimeHandler()

    refresh_token = request.cookies.get("refresh_token")

    if not refresh_token:
        raise HTTPException(status_code=401, detail="Missing refresh token cookie")

    decoded_token = authServices.decode_jwt_token(refresh_token, refresh=True)

    if timeHandler.is_expired(str(decoded_token.exp)):
        raise HTTPException(status_code=401, detail="Refresh token expired")

    token_data = decoded_token.model_dump(exclude=["exp", "sub"])
    new_access_token = await authServices.refresh(TokenData(**token_data))

    return UserTokenResponse(
        access_token=new_access_token,
        token_type="Bearer",
        user_id=decoded_token.user_id,
        user_role=decoded_token.user_role,
        user_email=decoded_token.user_email,
    )

@router.post(
    "/token", 
    response_model=TokenResponse, 
    summary="For UI/Docs purposes", 
    description="It returns the authorization token to be used by the Docs UI",
    include_in_schema=False
)
async def token(form_data: OAuth2PasswordRequestForm = Depends()):
    authServices = AuthServices()
    token, _ = await authServices.authenticate(email=form_data.username, password=form_data.password)
    return TokenResponse(access_token=token, token_type="bearer")

@router.post("/logout")
async def logout(response: Response):
    from services.AuthServices import AuthServices
    authServices = AuthServices()
    authServices.clear_refresh_cookie(response)
    return {"message": "Logged out successfully"}