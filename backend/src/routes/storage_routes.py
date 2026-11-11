from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Query,
    Request,
    UploadFile,
)

from starlette.formparsers import MultiPartParser
from starlette.responses import StreamingResponse


from services.CollectionServices import CollectionServices
from services.CredentialServices import CredentialServices
from services.FileServices import FileServices
from shared.models.catalog import CouchbaseCatalogCollectionModel, CouchbaseCatalogFileModel
from shared.models.storage import CreateCollectionPayload, CreateCollectionResponse, DownloadFileRequestPayload, DownloadFileRequestResponse, GetStorageBucketListResponse, StageCollectionDUAResponse, Storage, UpdateCollectionPayload, UpdateFilePayload, UploadCollectionDUAResponse, UploadFileRequestPayload, UploadFileRequestResponse
from routes.auth_routes import auth_oauth2_scheme


router = APIRouter(prefix="/storage", tags=["Storage"])

MultiPartParser.max_file_size = 20 * 1024 * 1024

@router.get("/bucket-list",
    summary="Get the list of storage buckets available in the system", 
    response_model=GetStorageBucketListResponse, 
    response_model_exclude_none=True, 
    response_model_exclude_unset=True
)
async def get_bucket_list(request: Request, _:str = Depends(auth_oauth2_scheme)) -> GetStorageBucketListResponse :
    credentialServices = CredentialServices()

    response = await credentialServices.list_storage_buckets()

    return GetStorageBucketListResponse(bucket_list=response)


@router.post(
    "/collections/create", 
    summary="Create a new collection dir", 
    response_model=CreateCollectionResponse, 
    response_model_exclude_none=True, 
    response_model_exclude_unset=True
)
async def create_collections(
    request: Request,
    payload: CreateCollectionPayload, 
    _: str = Depends(auth_oauth2_scheme)
) -> CreateCollectionResponse:
    
    user_id = request.state.user
    
    collection_services = CollectionServices()

    result = await collection_services.create_collection(payload=payload, user_id=user_id)
    
    return result


@router.post(
    "/collections/dua/stage",
    summary="Upload a PDF DUA before creating its collection",
    response_model=StageCollectionDUAResponse,
)
async def stage_collection_dua(
    request: Request,
    storage_type: Storage = Form(...),
    bucket_name: str = Form(...),
    file: UploadFile = File(...),
    _: str = Depends(auth_oauth2_scheme),
) -> StageCollectionDUAResponse:
    file_services = FileServices()
    return await file_services.stage_collection_dua(
        uploaded_file=file,
        storage_type=storage_type,
        bucket_name=bucket_name,
        user_id=request.state.user,
    )


@router.delete("/collections/dua/stage/{dua_id}")
async def delete_staged_collection_dua(
    dua_id: str,
    request: Request,
    storage_type: Storage = Query(...),
    bucket_name: str = Query(...),
    _: str = Depends(auth_oauth2_scheme),
) -> dict[str, bool]:
    await FileServices().delete_staged_collection_dua(
        dua_id=dua_id,
        storage_type=storage_type,
        bucket_name=bucket_name,
        user_id=request.state.user,
    )
    return {"deleted": True}


@router.post(
    "/collections/{collection_id}/dua",
    summary="Upload a PDF data usage agreement for a collection",
    response_model=UploadCollectionDUAResponse,
)
async def upload_collection_dua(
    collection_id: str,
    request: Request,
    file: UploadFile = File(...),
    _: str = Depends(auth_oauth2_scheme),
) -> UploadCollectionDUAResponse:
    file_services = FileServices()
    return await file_services.upload_collection_dua(
        collection_id=collection_id,
        uploaded_file=file,
        user_id=request.state.user,
    )


@router.get(
    "/collections/{collection_id}/dua",
    summary="Download a collection's attached DUA",
    response_class=StreamingResponse,
    responses={200: {"content": {"application/pdf": {}}}},
)
async def download_collection_dua(
    collection_id: str,
    _: str = Depends(auth_oauth2_scheme),
) -> StreamingResponse:
    file_services = FileServices()
    document_stream, filename = await file_services.open_collection_dua_stream(
        collection_id=collection_id,
    )
    return StreamingResponse(
        document_stream,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.patch(
    "/collections/{collection_id}",
    summary="Update a collection",
    response_model=CouchbaseCatalogCollectionModel,
    response_model_exclude_none=True,
    response_model_exclude_unset=True,
)
async def update_collection(
    collection_id: str,
    request: Request,
    payload: UpdateCollectionPayload,
    _: str = Depends(auth_oauth2_scheme),
) -> CouchbaseCatalogCollectionModel:
    collection_services = CollectionServices()
    return await collection_services.update_collection(
        collection_id=collection_id,
        payload=payload,
        user_id=request.state.user,
    )


@router.post(
    "/files/download-request", 
    summary="Download request", 
    response_model=DownloadFileRequestResponse
)
async def download_file_request(
    request: Request,
    payload: DownloadFileRequestPayload,
    _: str = Depends(auth_oauth2_scheme)
) -> DownloadFileRequestResponse:
    user_id = request.state.user

    files_services = FileServices()

    result = await files_services.create_download_request_directly(payload, user_id=user_id) 

    return result


@router.post(
    "/files/upload-request",
    summary="Open a file upload call to the server",
    description="This endpoint will generate a signed url on the bucket for the user to transfer the file directly",
    response_model=UploadFileRequestResponse
)
async def upload_file_request_direct(
    request: Request,
    payload: UploadFileRequestPayload,
    _: str = Depends(auth_oauth2_scheme)
) -> UploadFileRequestResponse:
    
    user_id = request.state.user

    files_services = FileServices()
    
    result = await files_services.create_upload_file_request_directly(payload=payload, user_id=user_id)

    return result


@router.patch(
    "/files/{catalog_record_id}",
    summary="Update file catalog metadata",
    response_model=CouchbaseCatalogFileModel,
    response_model_exclude_none=True,
    response_model_exclude_unset=True,
)
async def update_file_record(
    catalog_record_id: str,
    request: Request,
    payload: UpdateFilePayload,
    _: str = Depends(auth_oauth2_scheme),
) -> CouchbaseCatalogFileModel:
    file_services = FileServices()
    return await file_services.update_file_record(
        catalog_record_id=catalog_record_id,
        payload=payload,
        user_id=request.state.user,
    )


@router.get(
    "/files/{catalog_record_id}/complete",
    summary="Verify an uploaded object and complete its catalog record",
    response_model=CouchbaseCatalogFileModel,
)
async def complete_file_upload(
    catalog_record_id: str,
    request: Request,
    _: str = Depends(auth_oauth2_scheme),
) -> CouchbaseCatalogFileModel:
    files_services = FileServices()
    return await files_services.complete_upload(
        catalog_record_id=catalog_record_id,
        user_id=request.state.user,
    )
