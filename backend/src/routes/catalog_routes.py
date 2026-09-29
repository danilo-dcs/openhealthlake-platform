from fastapi import APIRouter, Depends, HTTPException, Query, Request

from services.CatalogServices import CatalogServices

from routes.auth_routes import auth_oauth2_scheme
from shared.models.catalog import CatalogFilterPayload, CouchbaseCatalogCollectionModel, CouchbaseCatalogFileModel, GetCollectionsCatalogResponse, GetFilesCatalogResponse, SetRecordStatusPayload


router = APIRouter(prefix="/catalog", tags=["Catalog"])

@router.get(
    path="/files/all/", 
    summary="List all file records in the catalog",
    response_model=GetFilesCatalogResponse
)
async def get_files_catalog(
    request: Request,
    page_number: str = Query(None),
    _: str = Depends(auth_oauth2_scheme)
) -> GetFilesCatalogResponse | HTTPException:
    try:
        user_id = request.state.user if request.state.user else None

        page = 1 if not page_number else int(page_number)

        catalogServices = CatalogServices()

        response = await catalogServices.list_files(user_id=user_id, page_number=page)
        
        return response
    
    except Exception as e:
        return HTTPException(status_code=500, detail=str(e))
    
@router.get(
    path="/collections/all/", 
    summary="List all collection records in the catalog",
    response_model=GetCollectionsCatalogResponse
)
async def get_collections_catalog(
    request: Request,
    page_number: str = Query(None),
    _: str = Depends(auth_oauth2_scheme)
) -> GetCollectionsCatalogResponse | HTTPException:
    try:
        user_id = request.state.user if request.state.user else ""

        page = 1 if not page_number else int(page_number)

        catalogServices = CatalogServices()
        response = await catalogServices.list_collections(user_id=user_id, page_number=page)

        return response
    
    except Exception as e:
        return HTTPException(status_code=500, detail=str(e))


@router.get(
    path="/file/id/{record_uuid}", 
    summary="List file record by id",
    response_model=CouchbaseCatalogFileModel
)
async def get_catalog_file_record_by_id(
    request: Request, 
    record_uuid: str,
    _: str = Depends(auth_oauth2_scheme)
) -> CouchbaseCatalogFileModel:

    user_id = request.state.user if request.state.user else None

    catalogServices = CatalogServices()

    response = await catalogServices.get_by_id(document_id=record_uuid, user_id=user_id, collection_name="files")

    return response 

@router.get(
    path="/collection/id/{record_uuid}", 
    summary="List collection record by id",
    response_model=CouchbaseCatalogCollectionModel
)
async def get_catalog_collection_record_by_id(request: Request, record_uuid: str, _: str = Depends(auth_oauth2_scheme)) -> CouchbaseCatalogCollectionModel:

    user_id = request.state.user if request.state.user else None

    catalogServices = CatalogServices()

    response = await catalogServices.get_by_id(document_id=record_uuid, user_id=user_id, collection_name="collections")

    return response

@router.post(
    path="/files/search", 
    summary="Apply a filter to the files catalog based on its properties", 
    response_model=GetFilesCatalogResponse,
    description="""
    Parameters: \n
        - Filter: {\n
            - property_name: the property name must be part of the properties in the catalog (Options:  filename, file_size,collection_name,processing_level,storage_type,file_location,inserted_by,inserted_at,file_description,file_category,status,expires_at,file_version)\n
            - Operator: The operators symbols in the filters should be one of the followint options ('=','>','<', '>=', '<=')\n
            - property_value: the property value can be a str, int, or float value. For dates, it should be the unix timestamp value repesenting the date as an integer\n
        }
    """
)
async def get_file_catalog_by_filters(
    request: Request,
    payload: CatalogFilterPayload, 
    _: str = Depends(auth_oauth2_scheme)
) -> GetFilesCatalogResponse | HTTPException:
    try:
        user_id = request.state.user if request.state.user else None

        catalogServices = CatalogServices()

        page = payload.page_number if payload.page_number else 1

        response = await catalogServices.get_by_filters(payload.filters, user_id=user_id, page_number=page, collection_name="files")

        return response
    
    except Exception as e:
        return HTTPException(status_code=500, detail=str(e))
    
@router.post(
    path="/collections/search", 
    summary="Apply a filter to the collections catalog based on its properties", 
    response_model=GetCollectionsCatalogResponse,
    description="""
    Parameters: \n
        - Filter: {\n
            - property_name: the property name must be part of the properties in the catalog (Options: collection_name,storage_type,inserted_by,status,location,collection_description)\n
            - operator: The operators symbols in the filters should be one of the followint options ('=','>','<', '>=', '<=', '*')\n
            - property_value: the property value can be a str, int, or float value. For dates, it should be the unix timestamp value repesenting the date as an integer\n
        }
    """)
async def get_collection_catalog_by_filters(
    payload: CatalogFilterPayload, 
    request: Request, 
    _: str = Depends(auth_oauth2_scheme)
) -> GetCollectionsCatalogResponse | HTTPException:
    try:
        user_id = request.state.user if request.state.user else None
        catalogServices = CatalogServices()
        response = await catalogServices.get_by_filters(payload.filters, user_id=user_id, collection_name="collections")
        return response
    
    except Exception as e:
        return HTTPException(status_code=500, detail=str(e))
    
@router.put(
    path="/set-file-status/{record_uuid}", 
    summary="Set the status of a catalog file record",
    response_model=CouchbaseCatalogFileModel
)
async def set_file_status(
    payload: SetRecordStatusPayload, 
    record_uuid: str, 
    _: str = Depends(auth_oauth2_scheme),
) -> CouchbaseCatalogFileModel | HTTPException:
    try:
        catalogServices = CatalogServices()
        response = await catalogServices.set_record_status(document_id=record_uuid, new_status=payload.status, collection_name="files")
        return response
    except Exception as e:
        return HTTPException(status_code=500, detail=str(e))
    

@router.delete(
    path="/collections/delete/{collection_uuid}",
    summary="Delete collection records",
    response_model=CouchbaseCatalogCollectionModel
)
async def delete_collection(collection_uuid: str, request: Request,  _: str = Depends(auth_oauth2_scheme)) -> CouchbaseCatalogCollectionModel:
    
    catalogService = CatalogServices()

    user_id = request.state.user if request.state.user else None

    deleted_record = await catalogService.delete_collection_record(document_id=collection_uuid, user_id=user_id)

    return deleted_record
    


@router.delete(
    path="/files/delete/{file_uuid}",
    summary="Delete file records",
    response_model=CouchbaseCatalogFileModel
)
async def delete_file(file_uuid: str, request: Request,  _: str = Depends(auth_oauth2_scheme)) -> CouchbaseCatalogFileModel:

    catalogService = CatalogServices()

    user_id = request.state.user if request.state.user else None

    deleted_record = await catalogService.delete_file_record(document_id=file_uuid, user_id=user_id)

    return deleted_record
    