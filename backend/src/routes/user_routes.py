from typing import List

from fastapi import APIRouter, Depends, Query, Request

from services.UserServices import UserServices
from shared.models.users import AssertUserVisasPayload, CouchbaseUserAssertionModel, CouchbaseUserModelNoPassword, CreateUserPayload, PasswordChangeRequest, PasswordRecoveryRequest

from routes.auth_routes import auth_oauth2_scheme


router = APIRouter(prefix="/user", tags=["User Passports"])


@router.get(
    "/all", 
    summary="List all users", 
    response_model=List[CouchbaseUserModelNoPassword], 
    response_model_exclude_none=True, 
    response_model_exclude_unset=True
)
async def list_all_users(_: str = Depends(auth_oauth2_scheme)) -> List[CouchbaseUserModelNoPassword]:
    usersService = UserServices()
    response = await usersService.list_all()
    return response


@router.get(
    "/id/{user_uuid}", 
    summary="Get User Info by Id", 
    response_model=CouchbaseUserModelNoPassword,
    response_model_exclude_none=True, 
    response_model_exclude_unset=True
)
async def list_user_details_by_id(user_uuid: str, _: str = Depends(auth_oauth2_scheme)) -> CouchbaseUserModelNoPassword:
    usersService = UserServices()
    response = await usersService.list_info_by_user_id(user_uuid=user_uuid)
    return response


@router.get("/visas/{user_uuid}", summary="Get User Visas by Id", response_model=CouchbaseUserAssertionModel)
async def list_user_visas(user_uuid: str, _: str = Depends(auth_oauth2_scheme)) -> CouchbaseUserAssertionModel:
    usersService = UserServices()
    response = await usersService.list_passport_by_user_id(user_uuid=user_uuid)
    return response


@router.post("/create", summary="Create User", response_model=CouchbaseUserModelNoPassword, response_model_exclude_none=True, response_model_exclude_unset=True)
async def create_users(
   payload: CreateUserPayload
) -> CouchbaseUserModelNoPassword:
    
    usersService = UserServices()
    response = await usersService.create_user(payload)
    return response


@router.put("/{user_uuid}/visas/grant", summary="Grant visas to users", response_model=CouchbaseUserAssertionModel)
async def grant_user_visas(
    user_uuid: str,
    payload: AssertUserVisasPayload,
    _: str = Depends(auth_oauth2_scheme)
) -> CouchbaseUserAssertionModel:
    usersService = UserServices()
    response = await usersService.grant_visas_to_user(user_uuid=user_uuid, visa_uuids=payload.visas_uuids)
    return response

@router.put("/{user_uuid}/visas/revoke", summary="Grant visas to users", response_model=CouchbaseUserAssertionModel)
async def revoke_user_visas(
    user_uuid: str,
    payload: AssertUserVisasPayload,
    _: str = Depends(auth_oauth2_scheme)
) -> CouchbaseUserAssertionModel:
    usersService = UserServices()
    response = await usersService.revoke_visas_from_user(user_uuid=user_uuid, visa_uuids=payload.visas_uuids)
    return response

@router.post(
    path="/password-recovery", 
    summary="Opens a new password recovery request", 
    description="A password change token will be sent to the user's email",
    response_model=str
)
async def password_recovery_request(payload: PasswordRecoveryRequest):
    usersService = UserServices()

    response = await usersService.password_recovery_request(payload=payload)

    return response


@router.post(
    path="/password-change", 
    summary="Changes user password", 
    description="A request token sent to the user's email is necessary",
    response_model=str
)
async def change_password(payload: PasswordChangeRequest):
    usersService = UserServices()
    respose = await usersService.password_change_request(payload=payload)
    return respose


@router.delete(
    path="/delete/{user_uuid}", 
    response_model=str,
    summary="Delete User",
    description="This endpoint allows for possession tranfering. To transfer an user's collections and files to another user before deleting them, please provide the `trasfer_ownership_to_user_id` query parameter. *WARNING:* All the collections and files created by an user will be automatically deleted if possession transfering is not used."
)
async def delete(
    request: Request,
    user_uuid: str,
    trasfer_ownership_to_user_id = Query(
        default=None, include_in_schema=True, 
        alias="trasfer_ownership_to_user_id"
    ),
    _: str = Depends(auth_oauth2_scheme)
) -> str:
    
    user_id = request.state.user if request.state.user else None
    user_role = request.state.user_role if request.state.user_role else None
 
    usersService = UserServices()

    response = await usersService.delete_user(user_uuid=user_uuid, requestor_id=user_id, requestor_role=user_role, new_owner_id=trasfer_ownership_to_user_id)

    return response
