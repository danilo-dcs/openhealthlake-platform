from typing import List, Union
from fastapi import HTTPException, status
import uuid6


from repositories.CouchbaseRepository import CouchbaseRepository
from services.CredentialServices import CredentialServices
from shared.models.access_requests import AccessRequestSearchPayload
from shared.models.catalog import CatalogCollectionBaseModel, CatalogFileBaseModel, CatalogFilter, CouchbaseCatalogCollectionModel, CouchbaseCatalogFileModel, FileStatus, GetCollectionsCatalogResponse, GetFilesCatalogResponse

from shared.models.credentials import CouchbaseCredentialModel
from shared.models.storage import Collections
from shared.factories.StorageClientFactory import StorageClientFactory

import math

from typing import TypeVar

T = TypeVar("T")

class CatalogServices:
    def __init__(self) -> None:
        self.scope = "catalogs"

        self.couchbaseRepo = CouchbaseRepository(
            scope=self.scope
        )

    def __catalog_pagination(self, catalog: List[T], page_number: int) -> tuple[List[T], int, int]:
            
            if not catalog:
                return (list(), None, 0)

            size = len(catalog)
            page_size = 1000
            n_pages = math.ceil(size/page_size)

            if page_number > n_pages:
                raise HTTPException(status_code=400, detail="Page not found!")
            
            
            if page_number < 1:
                page_number = 1

            start_index = (page_number-1)*page_size
            end_index = min(start_index+page_size, len(catalog))
            
            catalog = catalog[start_index:end_index]

            next_page = page_number+1 if end_index <= n_pages else None

            return (
                catalog,
                next_page,
                size
            )
        
    async def __get_credential_by_storage_bucket(self, storage_type: str, bucket_name: str) -> CouchbaseCredentialModel:
        credentialServices = CredentialServices()

        credentials = await credentialServices.list_all_cloud(collection_name="cloud")

        response_list = [ item for item in credentials if storage_type == item.storage_type and bucket_name in item.bucket_names ]

        return response_list[0]
    
    async def __user_collection_accesses(self, user_id: str) -> List[str]:
        from services.UserServices import UserServices

        userServices = UserServices()

        user_passport = await userServices.list_passport_by_user_id(user_uuid=user_id)

        collection_names = []

        if not user_passport or not user_passport.passportVisaAssertions:
            return collection_names

        visas = [ visaAssertions.passportVisa for visaAssertions in user_passport.passportVisaAssertions ]

        # collection_ids = []

        for visa in visas:
            col_id, col_name = visa.visaName.split(":")
            collection_names.append(col_name)
            # collection_ids.append(col_id)

        return collection_names


    async def create_catalog_record(
        self, 
        payload: CatalogFileBaseModel | CatalogCollectionBaseModel, 
        collection_name: Collections = "files"
    ) -> Union[CouchbaseCatalogFileModel | CouchbaseCatalogCollectionModel]:
        record_id = str(uuid6.uuid7())

        couchbasePayload = {}

        if collection_name == "files":
            couchbasePayload = CouchbaseCatalogFileModel(id=record_id, **payload.__dict__)
        elif collection_name == "collections":
            couchbasePayload = CouchbaseCatalogCollectionModel(id=record_id, **payload.__dict__)

        dumped_payload = couchbasePayload.model_dump(exclude_none=True, exclude_unset=True)

        await self.couchbaseRepo.create_document(collection_name=collection_name, key=record_id, value=dumped_payload)

        return couchbasePayload
    
    async def get_by_id_api(self, document_id: str, collection_name: Collections = "files") -> Union[CouchbaseCatalogFileModel, CouchbaseCatalogCollectionModel]:

        response = await self.couchbaseRepo.get_document_by_id(collection_name=collection_name, document_key=document_id)

        if not response:
            return {}
        
        couchbasePayload = []

        if collection_name == "files":
            couchbasePayload = list(map(lambda x: CouchbaseCatalogFileModel(**x[collection_name]), response))
        elif collection_name=="collections":
            couchbasePayload = list(map(lambda x: CouchbaseCatalogCollectionModel(**x[collection_name]), response))
        
        catalog_record = couchbasePayload[0]

        return catalog_record
    

    async def get_by_id(self, document_id: str, user_id: str, collection_name: Collections = "files") -> Union[CouchbaseCatalogFileModel, CouchbaseCatalogCollectionModel]:

        response = await self.couchbaseRepo.get_document_by_id(collection_name=collection_name, document_key=document_id)

        if not response:
            return {}
        
        couchbasePayload = []

        if collection_name == "files":
            couchbasePayload = list(map(lambda x: CouchbaseCatalogFileModel(**x[collection_name]), response))
        elif collection_name=="collections":
            couchbasePayload = list(map(lambda x: CouchbaseCatalogCollectionModel(**x[collection_name]), response))
        
        catalog_record = couchbasePayload[0]

        user_collections_names = await self.__user_collection_accesses(user_id=user_id)

        if not catalog_record.public and catalog_record.collection_name not in user_collections_names:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Access Denied: User has no granted visa to access this item")

        return catalog_record
    
    
    async def get_by_filters(
        self, 
        filters: List[CatalogFilter], 
        page_number: int = 1,
        user_id: str = None,
        collection_name: Collections = "collections",
    ) -> Union[GetFilesCatalogResponse, GetCollectionsCatalogResponse]:
        from shared.handlers.CouchbaseQueryBuilder import CouchbaseQueryBuilder
        from shared.handlers.TimeHandler import TimeHandler

        timeHandler = TimeHandler()

        queryBuilder = CouchbaseQueryBuilder(scope=self.scope, collection=collection_name)

        for filter_item in filters:
            if filter_item.property_name in ["inserted_at", "expires_at"]:
                if isinstance(filter_item.property_value, str) and filter_item.property_value.isdigit():
                    filter_item.property_value = int(filter_item.property_value)
                elif isinstance(filter_item.property_value, str):
                    filter_item.property_value = int(float(
                        timeHandler.datetime_to_unix_timestamp(
                            timeHandler.datetime_from_str(filter_item.property_value)
                        )
                    ))
                else:
                    raise HTTPException(status_code=400, detail="Invalid time value for date properties")
                
            
            elif filter_item.operator == '*' and isinstance(filter_item.property_value, str):
                queryBuilder.ilike(field=filter_item.property_name, value=filter_item.property_value)
                continue

            queryBuilder.where(field=filter_item.property_name, op=filter_item.operator, value=filter_item.property_value)

        query = queryBuilder.build()

        response = await self.couchbaseRepo.query(query)

        if not response:
            return GetFilesCatalogResponse(records=[], next_page=None, total=0) if collection_name == "files" else GetCollectionsCatalogResponse(records=[], next_page=None, total=0)
        
        loaded_catalog = []

        if collection_name == "files":
            loaded_catalog = list(map(lambda x: CouchbaseCatalogFileModel(**x[collection_name]), response))
        elif collection_name=="collections":
            loaded_catalog = list(map(lambda x: CouchbaseCatalogCollectionModel(**x[collection_name]), response))

        if user_id:
            user_collections_names = await self.__user_collection_accesses(user_id=user_id)

            if not user_collections_names:
                if collection_name == "files":
                    loaded_catalog = [ 
                        item for item in loaded_catalog 
                        if item.public 
                        and item.file_status != "deleted"
                    ]
                else:
                    loaded_catalog = [ 
                        item for item in loaded_catalog 
                        if not item.secret 
                        and item.status != "deleted"
                    ]

            if collection_name == "files":
                loaded_catalog = [ 
                    item for item in loaded_catalog 
                    if item.file_status != "deleted" 
                    and (
                        item.collection_name in user_collections_names 
                        or item.public
                    )
                ]
            else:
                loaded_catalog = [ 
                    item for item in loaded_catalog 
                    if item.status != "deleted" 
                    and (
                        item.collection_name in user_collections_names 
                        or not item.secret
                    )
                ]

        catalog_page, next_page, size = self.__catalog_pagination(catalog=loaded_catalog, page_number=page_number)

        return GetFilesCatalogResponse(records=catalog_page, next_page=next_page, total=size) if collection_name == "files" else GetCollectionsCatalogResponse(records=catalog_page, next_page=next_page, total=size)


    async def list_collections(self, user_id: str = None, page_number: int = 1) -> GetCollectionsCatalogResponse: 
        response = await self.couchbaseRepo.get_documents(collection_name="collections") 

        parsed_catalog = list(map(lambda x: CouchbaseCatalogCollectionModel(**x["collections"]), response))

        catalog = []

        if not user_id:
            catalog = parsed_catalog

        else:
            user_collection_names = await self.__user_collection_accesses(user_id=user_id)
            if not user_collection_names:
                catalog = [
                    item for item in parsed_catalog 
                    if not item.secret
                    and item.status != "deleted"
                ]
            else:
                catalog = [ 
                    item for item in parsed_catalog if item.status != "deleted" 
                    and (
                        item.collection_name in user_collection_names 
                        or user_id in item.inserted_by 
                        or not item.secret
                    )
                ]

        catalog_page, next_page, size = self.__catalog_pagination(catalog=catalog, page_number=page_number)

        return GetCollectionsCatalogResponse(records=catalog_page, next_page=next_page, total=size)
    
    
    async def list_files(self, user_id: str = None, page_number: int = 1) -> GetFilesCatalogResponse: 
        response = await self.couchbaseRepo.get_documents(collection_name="files") 

        parsed_catalog = list(map(lambda x: CouchbaseCatalogFileModel(**x["files"]), response))

        catalog = []
       
        if not user_id:
            catalog = [ item for item in parsed_catalog if item.public ]
        else:
            user_collection_names = await self.__user_collection_accesses(user_id=str(user_id))
            if not user_collection_names:
                catalog = [
                    item for item in parsed_catalog 
                    if item.public and item.file_status != "deleted"
                ]
            else:
                catalog = [ 
                    item for item in parsed_catalog 
                    if item.file_status != "deleted" 
                    and (
                        item.collection_name in user_collection_names 
                        or user_id in item.inserted_by 
                        or item.public
                    )
                ]

        catalog_page, next_page, size = self.__catalog_pagination(catalog=catalog, page_number=page_number)

        return GetFilesCatalogResponse(records=catalog_page, next_page=next_page, total=size)
    
    
    async def set_record_status(self, document_id: str, new_status: FileStatus = "ready", collection_name: Collections = "files") -> Union[CouchbaseCatalogFileModel | CouchbaseCatalogCollectionModel]:

        response = await self.couchbaseRepo.get_document_by_id(collection_name=collection_name, document_key=document_id)

        if not response:
            raise HTTPException(status_code=400, detail="Invalid or inexisting document_id")
        
        old_records = {}

        if collection_name == "files":
            old_records = list(map(lambda item: CouchbaseCatalogFileModel(**item[collection_name]),response)) 
        elif collection_name == "collections":
            old_records = list(map(lambda item: CouchbaseCatalogCollectionModel(**item[collection_name]),response)) 

        old_record = old_records[0]

        if collection_name == "files":
            old_record.file_status = new_status
            old_record.expires_at = None if new_status == "ready" else None
        else:
            old_record.status = new_status

        dumped_record = old_record.model_dump(exclude_none=True)

        await self.couchbaseRepo.upsert_document(collection_name=collection_name, key=document_id, value=dumped_record)

        return old_record

    async def set_collection_owner(self, collection_record: CouchbaseCatalogCollectionModel, new_owner: str) -> CouchbaseCatalogCollectionModel:

        updated_record = collection_record.model_copy(deep=True)

        updated_record.inserted_by = new_owner

        await self.couchbaseRepo.upsert_document(collection_name="collections", key=updated_record.id, value=updated_record.model_dump(exclude_none=True, exclude_unset=True))

        return updated_record
    
    async def upload_catalog_record(self, document_id: str, payload: CatalogFileBaseModel | CatalogCollectionBaseModel, collection_name: Collections = "files") -> Union[CouchbaseCatalogFileModel | CouchbaseCatalogCollectionModel]:
       
        old_document = await self.get_by_id(document_id=document_id, collection_name=collection_name)

        updated_document = {}

        if collection_name == "files":
            old_document = CouchbaseCatalogFileModel(**old_document)
            updated_document = CouchbaseCatalogFileModel(id=document_id, **payload.__dict__)
        elif collection_name == "collections":
            old_document = CouchbaseCatalogCollectionModel(**old_document)
            updated_document = CouchbaseCatalogCollectionModel(id=document_id, **payload.__dict__)

        if old_document == updated_document:
            return old_document
        
        dumped_payload = updated_document.model_dump(exclude_none=True, exclude_unset=True)
        
        await self.couchbaseRepo.upsert_document(collection_name=collection_name, key=document_id, value=dumped_payload)

        return old_document
    

    async def delete_catalog_record(self, document_id: str, collection_name: Collections = "files") -> str:

        await self.couchbaseRepo.delete_document(collection_name=collection_name, document_key=document_id)

        return document_id
    
    
    async def delete_file_record(self, document_id: str, user_id = None) -> CouchbaseCatalogFileModel:
        from shared.handlers.EncryptionHandler import EncryptionHandler  
         
        file_record = await self.get_by_id(document_id=document_id, user_id=user_id, collection_name="files")

        if not file_record:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid file record id!")
        
        file_collection = await self.get_by_id(
            document_id=file_record.collection_id,
            user_id=user_id, 
            collection_name="collections"
        )

        if user_id not in file_collection.inserted_by:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Insuficient privileges for this operation. Only collection can delete files")

        credential = await self.__get_credential_by_storage_bucket(storage_type=file_record.storage_type, bucket_name=file_record.file_bucket)

        if not credential:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail=f"Missing credentials to operate in the following bucket enviroment {file_record.file_bucket}"
            )

        encryptionHandler = EncryptionHandler()

        decrypted_credential = encryptionHandler.decrypt_credentials(credential.credential)

        blob_name = (
            f"{file_record.file_bucket}/collections/{file_record.collection_name}/"
            f"{file_record.processing_level or 'raw'}/v{file_record.file_version}/{file_record.file_name}"
        )
        
        storage_client = StorageClientFactory.create_client(
            storage_type=file_record.storage_type,
            bucket=file_record.file_bucket,
            credentials=decrypted_credential,
            minio_endpoint_use="internal",
        )

        try:
            if file_record.storage_type == "hdfs":
                storage_client.delete_object(blob_name)
            else:
                storage_client.delete_object(file_record.file_bucket, blob_name)
        finally:
            storage_client.close()

        await self.set_record_status(document_id=file_record.id, new_status = "deleted", collection_name="files")

        return file_record


    #TODO [improvement] deletion logic by implementing delete multiple files in the bucket storad (or all the files with a blob prefix or dir)
    async def delete_collection_record(self, document_id: str, user_id = None) -> CouchbaseCatalogCollectionModel:
        from services.VisasServices import VisaServices
        from services.AccessRequestServices import AccessRequestServices
        
        visaServices = VisaServices()

        collection_record = await self.get_by_id(document_id=document_id, user_id=user_id, collection_name="collections")

        if not collection_record:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid collection record id!")

        if user_id not in collection_record.inserted_by:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Insuficient privileges for this operation. Only collection owners can delete collections")
        
        accessRequestService = AccessRequestServices()

        filters = AccessRequestSearchPayload(
            collection_id=collection_record.id
        )

        access_requests = await accessRequestService.search_by_owner_and_collections(payload=filters)

        if access_requests:
            for item in access_requests:
                await accessRequestService.delete_access_request(
                    user_id=user_id, 
                    document_id=item.id
                )

        visas = await visaServices.list_all()

        visa_name = f"{collection_record.id}:{collection_record.collection_name}"

        collection_visa = [ visa for visa in visas if visa.visaName == visa_name ]

        target_visa = collection_visa[0] if collection_visa else None

        if target_visa:
            # list users with this visa
            # revoke this visa from all users that have it
            # delete visa (already includes the previous steps)
            await visaServices.delete_visa(visa_uuid=target_visa.id)

        # deny all the access requests to this collection

        filters = [
            CatalogFilter(property_name="collection_id", operator="=", property_value=collection_record.id),
        ]

        collection_files = await self.get_by_filters(filters=filters, user_id=user_id, collection_name="files")

        if collection_files:
            for file_record in collection_files.records:
                await self.delete_file_record(document_id=file_record.id, user_id=user_id)

        await self.set_record_status(document_id=collection_record.id, new_status = "deleted", collection_name="collections")

        return collection_record
         
