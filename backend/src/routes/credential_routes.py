import traceback
from typing import List
import uuid6
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from services.CredentialServices import CredentialServices
from shared.models.storage import Storage
from shared.models.credentials import CouchbaseCredentialModel, CreateCredentialsPayload, DeleteCredentialResponse
from shared.handlers.FilesHandler import FilesHandler


from routes.auth_routes import auth_oauth2_scheme

router = APIRouter(prefix="/credentials", tags=["Credentials"])

@router.get(
    path="/all", 
    summary="List all cloud credentials",
    response_model=List[CouchbaseCredentialModel]
)
async def list_all_credentials(
    _: str = Depends(auth_oauth2_scheme)
) -> List[CouchbaseCredentialModel]:
    credentialServices = CredentialServices()

    response = await credentialServices.list_all_cloud()
    
    return response

@router.get(
    path="/id/{credential_uuid}", 
    summary="List credential by id",
    response_model=CouchbaseCredentialModel
)
async def get_credential_by_id(
    credential_uuid: str, 
    _: str = Depends(auth_oauth2_scheme)
) -> CouchbaseCredentialModel:

    credentialServices = CredentialServices()

    response = await credentialServices.list_by_id(credential_id=credential_uuid)
    
    return response
    

# @router.get(
#     path="/visa/{visa_uuid}", 
#     summary="List credential by visa id", 
#     response_model=List[CouchbaseCredentialModel]
# )
# async def get_credential_by_visa_id(visa_uuid: str, _: str = Depends(auth_oauth2_scheme)) -> List[CouchbaseCredentialModel]:
    
#     credentialServices = CredentialServices()

#     response = await credentialServices.list_by_visa_id(visa_uuid=visa_uuid)
    
#     return response

# @router.get(
#     path="/query", 
#     summary="List credential by visa id",
#     response_model=List[CouchbaseCredentialModel]
# )
# async def get_credential_by_visa_ids(
#     visa_uuids: str = Query(...), 
#     _: str = Depends(auth_oauth2_scheme)
# ) -> List[CouchbaseCredentialModel]:
    
#     id_list = json.loads(visa_uuids)

#     try:
#         if not isinstance(id_list, list):
#             return HTTPException({"error": "visa_uuids should be a list of values"})
#     except json.JSONDecodeError:
#         raise({"error": "Invalid format for ids. Expected JSON list format, e.g., [1,2,3]."})
    
#     credentialServices = CredentialServices()

#     response = await credentialServices.list_by_visa_ids(visa_uuids=id_list)
    
#     return response
    

@router.post(
    path="/create", 
    summary="Uploads a JSON string object containing cloud credentials",
    response_model=CouchbaseCredentialModel
)
async def upload_credentials(
    payload: CreateCredentialsPayload,
    _: str = Depends(auth_oauth2_scheme)
) -> CouchbaseCredentialModel:
    
    try:
        credentialServices = CredentialServices()
        response = await credentialServices.create_credentials(payload)

    except Exception as e:
        error_message = f"Error saving file: {str(e)}"
        stack_trace = traceback.format_exc() 
        print("An error occurred:")
        print(stack_trace)  
        raise HTTPException(
            status_code=500, 
            detail=error_message
        )  

    return response



@router.post(
    path="/create/json", 
    summary="Uploads a JSON file containing cloud credentials", 
    response_model=CouchbaseCredentialModel,
    description="The payload for this route should be a form data containing the uploaded json file and the other parameters."
)
async def upload_credentials_from_json(
    credentials_json: UploadFile = File(...),
    visa_uuids: List[str] = Form(None),
    storage_type: Storage = Form(...),
    bucket_names: List[str] = Form(...),
    _: str = Depends(auth_oauth2_scheme)
) -> CouchbaseCredentialModel:
    
    try:
        file_tmp_name = str(uuid6.uuid7())

        base_path = "/tmp/api"

        filesHandler = FilesHandler(base_path)

        file_path = f"{base_path}/{file_tmp_name}"
        
        await filesHandler.save(file_path, credentials_json.file)

        credentialServices = CredentialServices(files_handler=filesHandler)

        response = await credentialServices.create_credentials_from_json(
            credentials_file_path=file_path, 
            visa_uuids=visa_uuids, 
            storage_type=storage_type, 
            bucket_names=bucket_names
        )

    except Exception as e:
        error_message = f"Error saving file: {str(e)}"
        stack_trace = traceback.format_exc() 
        print("An error occurred:")
        print(stack_trace)  
        raise HTTPException(
            status_code=500, 
            detail=error_message
        )  

    return response



# @router.put(
#     path="/visa/grant/{credential_uuid}", 
#     summary="Grant credentials to visas",
#     response_model=CouchbaseCredentialModel
# )
# async def grant_credentials(
#     credential_uuid: str,
#     visa_uuid: str,
#     _: str = Depends(auth_oauth2_scheme)
# ) -> CouchbaseCredentialModel:
    
#     try:
#         credentialServices = CredentialServices()
#         response = await credentialServices.grant_credential_to_visa(credential_uuid=credential_uuid, visa_uuid=visa_uuid)

#     except Exception as e:
#         error_message = f"Error saving file: {str(e)}"
#         stack_trace = traceback.format_exc() 
#         print("An error occurred:")
#         print(stack_trace)  
#         raise HTTPException(
#             status_code=500, 
#             detail=error_message
#         )  

#     return response


# @router.put(
#     path="/visa/revoke/{credential_uuid}", 
#     summary="Revoke credentials to visas",
#     response_model=CouchbaseCredentialModel
# )
# async def revoke_credentials(
#     credential_uuid: str,
#     visa_uuid: str,
#     _: str = Depends(auth_oauth2_scheme)
# ) -> CouchbaseCredentialModel:
    
#     try:
#         credentialServices = CredentialServices()
#         response = await credentialServices.revoke_credential_from_visa(credential_uuid=credential_uuid, visa_uuid=visa_uuid)

#     except Exception as e:
#         error_message = f"Error saving file: {str(e)}"
#         stack_trace = traceback.format_exc() 
#         print("An error occurred:")
#         print(stack_trace)  
#         raise HTTPException(
#             status_code=500, 
#             detail=error_message
#         )  

#     return response


@router.delete(
    path="/delete/{credential_uuid}", 
    summary="Delete credential by id",
    response_model=DeleteCredentialResponse
)
async def delete_by_id(
    credential_uuid: str, _: str = Depends(auth_oauth2_scheme)
) -> DeleteCredentialResponse:

    credentialServices = CredentialServices()

    response = await credentialServices.delete_by_id(credential_uuid=credential_uuid)

    return DeleteCredentialResponse(deleted_credential_id=response)
