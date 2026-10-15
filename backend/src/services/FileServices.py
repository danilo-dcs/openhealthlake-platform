from fastapi import HTTPException, status
from starlette.formparsers import MultiPartParser

from services.CatalogServices import CatalogServices
from services.CredentialServices import CredentialServices
from shared.models.catalog import CatalogFileBaseModel, CatalogFilter, CouchbaseCatalogFileModel
from shared.factories.StorageClientFactory import StorageClientFactory
from shared.models.credentials import CouchbaseCredentialModel
from shared.models.storage import DownloadFileRequestPayload, DownloadFileRequestResponse, UploadFileRequestPayload, UploadFileRequestResponse
from shared.handlers.TimeHandler import TimeHandler

MultiPartParser.max_file_size = 20 * 1024 * 1024  # setting th emax file size to 20 MB


class FileServices:

    @staticmethod
    def __file_object_name(file_record: CatalogFileBaseModel) -> str:
        return (
            f"{file_record.file_bucket}/collections/{file_record.collection_name}/"
            f"{file_record.processing_level or 'raw'}/"
            f"v{file_record.file_version}/{file_record.file_name}"
        )

    @staticmethod
    async def __get_credential_by_storage_bucket(storage_type: str, bucket_name: str) -> CouchbaseCredentialModel:
        credentialServices = CredentialServices()

        credentials = await credentialServices.list_all_cloud(collection_name="cloud")

        response_list = [
            item
            for item in credentials
            if storage_type == item.storage_type and bucket_name in item.bucket_names
        ]

        if not response_list:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No {storage_type} credentials are configured for bucket {bucket_name}",
            )

        return response_list[0]

    
    async def create_upload_file_request_directly(
        self, 
        payload: UploadFileRequestPayload,
        user_id: str
    ) -> UploadFileRequestResponse:
        """Returns a string containing a hash key for the file upload folder"""
        from shared.handlers.EncryptionHandler import EncryptionHandler

        encryptionHandler = EncryptionHandler()

        catalogServices = CatalogServices()
        
        collection_record = await catalogServices.get_by_id(
            document_id=payload.collection_catalog_id, 
            user_id=user_id, 
            collection_name="collections"
        )

        if not collection_record:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail=f"Collection catalog id {payload.collection_catalog_id} was not found"
            )
        
        credential = await self.__get_credential_by_storage_bucket(
            storage_type=collection_record.storage_type,
            bucket_name=collection_record.bucket,
        )
        
        #checking for redundant file
        filters = [
            CatalogFilter(
                property_name="collection_id",
                operator="=",
                property_value=collection_record.id
            ),
            CatalogFilter(
                property_name="file_name",
                operator="=",
                property_value=payload.file_name
            ),
            CatalogFilter(
                property_name="file_category",
                operator="=",
                property_value=payload.file_category
            ),
            CatalogFilter(
                property_name="processing_level",
                operator="=",
                property_value=payload.processing_level
            )
        ]

        catalog_file_items = await catalogServices.get_by_filters(filters=filters, collection_name="files", user_id=user_id)

        latest_version = 1

        if catalog_file_items and catalog_file_items.records:
            for record in catalog_file_items.records:
                if record.file_version > latest_version:
                    latest_version = record.file_version
            latest_version = latest_version + 1

        timeHandler = TimeHandler()
 
        expiry_date = timeHandler.expiry_at(seconds=30*60)

        expiry_date = int(float(timeHandler.datetime_to_unix_timestamp(date=expiry_date)))

        inserted_at = int(float(timeHandler.datetime_to_unix_timestamp(date=timeHandler.utc_now())))

        catalog_payload = CatalogFileBaseModel(
            collection_id=collection_record.id,
            collection_name=collection_record.collection_name,
            file_name=payload.file_name,
            file_category=payload.file_category if payload.file_category else "unstructured",
            processing_level=payload.processing_level if payload.processing_level else "raw",
            file_location=collection_record.bucket,
            storage_type=collection_record.storage_type,
            inserted_by=collection_record.inserted_by,
            inserted_at=inserted_at,
            expires_at=expiry_date,
            file_status="uploading",
            file_description=payload.file_description if payload.file_description else None,
            file_version=payload.file_version if (payload.file_version and payload.file_version > 1 and payload.file_version != latest_version) else latest_version,
            file_size=payload.file_size,
            public=payload.public if payload.public else collection_record.public
        )

        catalogRecord = await catalogServices.create_catalog_record(payload=catalog_payload)

        upload_url = None

        blob_name = self.__file_object_name(catalog_payload)

        decoded_credential = encryptionHandler.decrypt_credentials(credential.credential)
   
        storage_client = StorageClientFactory.create_client(
            storage_type=collection_record.storage_type, 
            bucket=collection_record.bucket,
            credentials=decoded_credential
        )

        try:
            upload_url = storage_client.generate_upload_url(blob_name)
        finally:
            storage_client.close()
  

        if not upload_url:
            await catalogServices.delete_catalog_record(document_id=catalogRecord.id, collection_name="files")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Unable to generate upload url"
            )

        return UploadFileRequestResponse(
            upload_url=upload_url,
            method="POST" if collection_record.storage_type == 'hdfs' else "PUT",
            catalog_record_id=catalogRecord.id
        )

    async def complete_upload(
        self,
        catalog_record_id: str,
        user_id: str,
    ) -> CouchbaseCatalogFileModel:
        """Verify an uploaded object and mark its catalog record ready."""
        from shared.handlers.EncryptionHandler import EncryptionHandler

        catalog_services = CatalogServices()

        file_record = await catalog_services.get_by_id(
            document_id=catalog_record_id,
            user_id=user_id,
            collection_name="files",
        )

        if not file_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File upload record was not found or is not accessible.",
            )

        if file_record.file_status == "ready":
            return file_record
        if file_record.file_status != "uploading":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"File record cannot be completed from status '{file_record.file_status}'.",
            )

        credential_record = await self.__get_credential_by_storage_bucket(
            storage_type=file_record.storage_type,
            bucket_name=file_record.file_bucket,
        )
        decoded_credential = EncryptionHandler().decrypt_credentials(credential_record.credential)

        object_name = self.__file_object_name(file_record)

        storage_client = StorageClientFactory.create_client(
            storage_type=file_record.storage_type, 
            bucket=file_record.file_bucket,
            credentials=decoded_credential
        )
        
        try:
            object_size = storage_client.get_object_size(
                object_name
            ) 
            
        finally:
            storage_client.close()

        if object_size is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Uploaded object is not available yet.",
            )

        if file_record.file_size is not None and object_size != file_record.file_size:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Uploaded object size ({object_size} bytes) does not match the "
                    f"expected size ({file_record.file_size} bytes)."
                ),
            )

        record_status = await catalog_services.set_record_status(
            document_id=catalog_record_id,
            new_status="ready",
            collection_name="files",
        )

        return record_status

   
    async def create_download_request_directly(
        self,
        payload: DownloadFileRequestPayload,
        user_id: str
    ) -> DownloadFileRequestResponse:
        """Returns a string containing the signed url to download the file"""

        from shared.handlers.EncryptionHandler import EncryptionHandler

        enctyptionHandler = EncryptionHandler()

        timeHandler = TimeHandler()

        catalogServices = CatalogServices()

        catalog_record = await catalogServices.get_by_id(document_id=payload.catalog_file_id, user_id=user_id)

        if not catalog_record:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Catalog record does not exist or invalid record id!"
            )
        
        credential = await self.__get_credential_by_storage_bucket(storage_type=catalog_record.storage_type, bucket_name=catalog_record.file_bucket)

        if not credential:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail=f"Missing credentials to operate in the following bucket enviroment {catalog_record.file_bucket}"
            )
        
        decoded_credential = enctyptionHandler.decrypt_credentials(credential.credential)

        expire_time = 30 * 60

        expiry_date = timeHandler.expiry_at(seconds=expire_time)

        expiry_date = timeHandler.datetime_to_unix_timestamp(date=expiry_date)

        download_url = None

        blob_name = self.__file_object_name(catalog_record)

        storage_client = StorageClientFactory.create_client(
            catalog_record.storage_type,
            decoded_credential,
            endpoint=catalog_record.file_bucket if catalog_record.storage_type == "hdfs" else None,
            minio_endpoint_use="public",
        )

        try:
            download_url = storage_client.generate_download_url(
                blob_name
            ) if catalog_record.storage_type == "hdfs" else storage_client.generate_download_url(
                catalog_record.file_bucket, blob_name, expire_time
            )
        finally:
            storage_client.close()

        return DownloadFileRequestResponse(
            download_url=download_url
        )
