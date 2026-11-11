import logging
import uuid6
from uuid import UUID
from collections.abc import Iterator

from fastapi import HTTPException, UploadFile, status
from starlette.formparsers import MultiPartParser

from services.CatalogServices import CatalogServices
from services.CredentialServices import CredentialServices
from shared.models.catalog import CatalogFileBaseModel, CatalogFilter, CouchbaseCatalogFileModel
from shared.factories.StorageClientFactory import StorageClientFactory
from shared.models.credentials import CouchbaseCredentialModel
from shared.models.storage import DownloadFileRequestPayload, DownloadFileRequestResponse, StageCollectionDUAResponse, UpdateFilePayload, UploadCollectionDUAResponse, UploadFileRequestPayload, UploadFileRequestResponse
from shared.handlers.TimeHandler import TimeHandler

MultiPartParser.max_file_size = 20 * 1024 * 1024  # setting th emax file size to 20 MB


class FileServices:
    MAX_DUA_SIZE = 20 * 1024 * 1024

    @classmethod
    async def __read_valid_pdf(cls, uploaded_file: UploadFile) -> bytes:
        filename = uploaded_file.filename or ""
        if not filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Only PDF documents are accepted.",
            )

        document_data = await uploaded_file.read(cls.MAX_DUA_SIZE + 1)
        if not document_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The PDF document is empty.",
            )
        if len(document_data) > cls.MAX_DUA_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="The PDF document exceeds the 20 MB upload limit.",
            )
        if b"%PDF-" not in document_data[:1024]:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="The uploaded file does not have a valid PDF signature.",
            )
        return document_data

    @staticmethod
    def __normalize_dua_id(dua_id: str) -> str:
        try:
            return str(UUID(dua_id))
        except (ValueError, TypeError, AttributeError) as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid DUA document id.",
            ) from error

    @classmethod
    def __staged_dua_object_name(cls, bucket_name: str, user_id: str, dua_id: str) -> str:
        safe_dua_id = cls.__normalize_dua_id(dua_id)
        return f"{bucket_name}/documents/pending/{user_id}/{safe_dua_id}.pdf"


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
            file_bucket=collection_record.bucket,
            storage_type=collection_record.storage_type,
            inserted_by=collection_record.inserted_by,
            inserted_at=inserted_at,
            expires_at=expiry_date,
            file_status="uploading",
            file_description=payload.file_description if payload.file_description else None,
            file_version=payload.file_version if (payload.file_version and payload.file_version > 1 and payload.file_version != latest_version) else latest_version,
            file_size=payload.file_size,
            public=payload.public if payload.public else collection_record.public,
            labels=payload.labels
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

    async def upload_collection_dua(
        self,
        collection_id: str,
        uploaded_file: UploadFile,
        user_id: str,
    ) -> UploadCollectionDUAResponse:
        """Store a PDF DUA and attach its ID to the owning collection record."""
        from shared.handlers.EncryptionHandler import EncryptionHandler

        document_data = await self.__read_valid_pdf(uploaded_file)

        catalog_services = CatalogServices()
        collection = await catalog_services.get_by_id_api(
            document_id=collection_id,
            collection_name="collections",
        )
        if not collection or not collection.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Collection was not found.",
            )
        if not collection.inserted_by or collection.inserted_by.split(":", 1)[0] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the collection owner can attach its DUA.",
            )
        if collection.status == "deleted":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A DUA cannot be attached to a deleted collection.",
            )
        if collection.dua:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This collection already has a DUA attached.",
            )
        if not collection.bucket:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The collection does not have an associated storage bucket.",
            )

        credential = await self.__get_credential_by_storage_bucket(
            storage_type=collection.storage_type,
            bucket_name=collection.bucket,
        )
        decoded_credential = EncryptionHandler().decrypt_credentials(credential.credential)

        dua_id = str(uuid6.uuid7())
        object_name = f"{collection.bucket}/documents/{collection.id}/{dua_id}.pdf"
        storage_client = StorageClientFactory.create_client(
            storage_type=collection.storage_type,
            bucket=collection.bucket,
            credentials=decoded_credential,
            minio_endpoint_use="internal",
        )

        try:
            storage_client.upload_object(
                object_name=object_name,
                data=document_data,
                content_type="application/pdf",
            )
            updated_collection = collection.model_copy(update={"dua": dua_id})
            try:
                await catalog_services.couchbaseRepo.upsert_document(
                    collection_name="collections",
                    key=collection.id,
                    value=updated_collection.model_dump(exclude_none=True, exclude_unset=True),
                )
            except Exception:
                try:
                    storage_client.delete_object(object_name)
                except Exception:
                    logging.getLogger(__name__).exception(
                        "Could not remove unlinked DUA object %s", object_name
                    )
                raise
        finally:
            storage_client.close()

        return UploadCollectionDUAResponse(collection_id=collection.id, dua_id=dua_id)

    async def stage_collection_dua(
        self,
        uploaded_file: UploadFile,
        storage_type: str,
        bucket_name: str,
        user_id: str,
    ) -> StageCollectionDUAResponse:
        """Upload a DUA before collection creation under a user-scoped temporary key."""
        from shared.handlers.EncryptionHandler import EncryptionHandler

        document_data = await self.__read_valid_pdf(uploaded_file)
        credential = await self.__get_credential_by_storage_bucket(
            storage_type=storage_type,
            bucket_name=bucket_name,
        )
        decoded_credential = EncryptionHandler().decrypt_credentials(credential.credential)

        dua_id = str(uuid6.uuid7())
        staged_object_name = self.__staged_dua_object_name(bucket_name, user_id, dua_id)
        storage_client = StorageClientFactory.create_client(
            storage_type=storage_type,
            bucket=bucket_name,
            credentials=decoded_credential,
            minio_endpoint_use="internal",
        )
        try:
            storage_client.upload_object(
                object_name=staged_object_name,
                data=document_data,
                content_type="application/pdf",
            )
        finally:
            storage_client.close()

        return StageCollectionDUAResponse(dua_id=dua_id)

    async def delete_staged_collection_dua(
        self,
        dua_id: str,
        storage_type: str,
        bucket_name: str,
        user_id: str,
    ) -> None:
        """Remove an unlinked staged DUA after a collection create failure."""
        from shared.handlers.EncryptionHandler import EncryptionHandler

        credential = await self.__get_credential_by_storage_bucket(
            storage_type=storage_type,
            bucket_name=bucket_name,
        )
        decoded_credential = EncryptionHandler().decrypt_credentials(credential.credential)
        staged_object_name = self.__staged_dua_object_name(bucket_name, user_id, dua_id)
        storage_client = StorageClientFactory.create_client(
            storage_type=storage_type,
            bucket=bucket_name,
            credentials=decoded_credential,
            minio_endpoint_use="internal",
        )
        try:
            if storage_client.get_object_size(staged_object_name) is not None:
                storage_client.delete_object(staged_object_name)
        finally:
            storage_client.close()

    async def open_collection_dua_stream(
        self,
        collection_id: str,
    ) -> tuple[Iterator[bytes], str]:
        """Open the attached DUA for an authenticated API response."""
        from shared.handlers.EncryptionHandler import EncryptionHandler

        catalog_services = CatalogServices()
        collection = await catalog_services.get_by_id_api(
            document_id=collection_id,
            collection_name="collections",
        )
        if not collection or not collection.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Collection was not found.",
            )
        if not collection.dua:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="This collection does not have a DUA attached.",
            )
        if not collection.bucket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="The collection does not have an associated storage bucket.",
            )

        credential = await self.__get_credential_by_storage_bucket(
            storage_type=collection.storage_type,
            bucket_name=collection.bucket,
        )
        decoded_credential = EncryptionHandler().decrypt_credentials(credential.credential)
        object_name = f"{collection.bucket}/documents/{collection.id}/{collection.dua}.pdf"
        storage_client = StorageClientFactory.create_client(
            storage_type=collection.storage_type,
            bucket=collection.bucket,
            credentials=decoded_credential,
            minio_endpoint_use="internal",
        )

        try:
            if storage_client.get_object_size(object_name) is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="The DUA document could not be found in storage.",
                )
            object_stream = storage_client.open_object_stream(object_name)
        except Exception:
            storage_client.close()
            raise

        def stream_with_cleanup() -> Iterator[bytes]:
            try:
                yield from object_stream
            finally:
                storage_client.close()

        return stream_with_cleanup(), "collection-dua.pdf"

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
            credentials=decoded_credential,
            minio_endpoint_use="internal",
        )
        
        try:
            object_size = storage_client.get_object_size(object_name) 
            
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

    async def update_file_record(
        self,
        catalog_record_id: str,
        payload: UpdateFilePayload,
        user_id: str,
    ) -> CouchbaseCatalogFileModel:
        """Update editable metadata on a file catalog record."""
        changes = payload.model_dump(exclude_unset=True)
        if not changes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Provide at least one file field to update.",
            )

        catalog_services = CatalogServices()
        file_record = await catalog_services.get_by_id_api(
            document_id=catalog_record_id,
            collection_name="files",
        )

        if not file_record or not file_record.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File catalog record was not found.",
            )

        if not file_record.inserted_by or file_record.inserted_by.split(":", 1)[0] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the file's collection owner can update this file record.",
            )

        updated_record = file_record.model_copy(update=changes)
        await catalog_services.couchbaseRepo.upsert_document(
            collection_name="files",
            key=catalog_record_id,
            value=updated_record.model_dump(exclude_none=True, exclude_unset=True),
        )

        return updated_record

   
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

        download_url = None

        blob_name = self.__file_object_name(catalog_record)

        storage_client = StorageClientFactory.create_client(
            storage_type=catalog_record.storage_type,
            bucket=catalog_record.file_bucket,
            credentials=decoded_credential
        )

        try:
            download_url = storage_client.generate_download_url(blob_name)
        finally:
            storage_client.close()

        return DownloadFileRequestResponse(
            download_url=download_url
        )
