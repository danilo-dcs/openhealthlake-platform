from fastapi import Depends, APIRouter, Request
from routes.auth_routes import auth_oauth2_scheme
from services.AccessRequestServices import AccessRequestServices
from shared.models.access_requests import AccessRequestModel, AccessRequestSearchPayload, AccessRequestSearchResponse, CouchbaseAccessRequestModel, GrantAccessRequestPayload, InviteCollaboratorPayload, RevokeAccessRequestPayload


router = APIRouter(prefix="/access-request", tags=["Collection Access Request"])

@router.post("/invite", summary="Invite a user to collaborate on a collection")
async def invite_collection_collaborator(
    request: Request,
    payload: InviteCollaboratorPayload,
    _: str = Depends(auth_oauth2_scheme),
) -> dict[str, str]:
    user_id = request.state.user
    accessRequestServices = AccessRequestServices()
    return await accessRequestServices.invite_collaborator(payload=payload, owner_id=user_id)

@router.post(
    "/create", 
    summary="Create a new Access Request", 
    response_model=CouchbaseAccessRequestModel,
    response_model_exclude_none=True, 
    response_model_exclude_unset=True
)
async def create_access_request(
    payload: AccessRequestModel, 
    _: str = Depends(auth_oauth2_scheme)
) -> CouchbaseAccessRequestModel:
    accessRequestServices = AccessRequestServices()
    response = await accessRequestServices.create_request(payload=payload)
    return response

@router.post(
    "/grant", 
    summary="Grant Access Request", 
    response_model=CouchbaseAccessRequestModel,
    response_model_exclude_none=True, 
    response_model_exclude_unset=True
)
async def grant_access_request(
    request: Request,
    payload: GrantAccessRequestPayload, 
    _: str = Depends(auth_oauth2_scheme)
) -> CouchbaseAccessRequestModel:
    user_id = request.state.user
    accessRequestServices = AccessRequestServices()
    response = await accessRequestServices.grant_access(payload=payload, user_id=user_id)
    return response

@router.post(
    "/revoke", 
    summary="Revoke Access Request", 
    response_model=CouchbaseAccessRequestModel,
    response_model_exclude_none=True, 
    response_model_exclude_unset=True
)
async def revoke_access_request(
    request: Request,
    payload: RevokeAccessRequestPayload, 
    _: str = Depends(auth_oauth2_scheme)
) -> CouchbaseAccessRequestModel:
    user_id = request.state.user
    accessRequestServices = AccessRequestServices()
    response = await accessRequestServices.revoke_access(payload=payload, user_id=user_id)
    return response

@router.post(
    "/search", 
    summary="Search Access Request List Based on user_id and collection_id", 
    response_model=AccessRequestSearchResponse,
    response_model_exclude_none=True, 
    response_model_exclude_unset=True
)
async def list_by_owner_and_collection(
    payload: AccessRequestSearchPayload, 
    _: str = Depends(auth_oauth2_scheme)
) -> AccessRequestSearchResponse:
    accessRequestServices = AccessRequestServices()
    response = await accessRequestServices.search_by_owner_and_collections(payload=payload)
    return AccessRequestSearchResponse(access_requests=response)


@router.delete(
    "/delete/{access_request_uuid}", 
    summary="Delete user accesses requersts",
    response_model=str
)
async def delete_access_request(
    request: Request,
    access_request_uuid: str, 
    _: str = Depends(auth_oauth2_scheme)
) -> str:
    
    user_id= request.state.user

    accessRequestServices = AccessRequestServices()
    response = await accessRequestServices.delete_access_request(user_id=user_id, document_id=access_request_uuid)
    return response
