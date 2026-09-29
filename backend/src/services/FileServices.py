from datetime import timedelta

import boto3
from google.cloud import storage
# from hdfs import InsecureClient
from minio import Minio

from fastapi import HTTPException, status
import requests


from starlette.formparsers import MultiPartParser

from services.CatalogServices import CatalogServices
from services.CredentialServices import CredentialServices
from shared.functions.regex import get_ip_address
from shared.models.catalog import CatalogFileBaseModel, CatalogFilter
from shared.models.credentials import AmazonCredentialsModel, CouchbaseCredentialModel, MinioCredentialsModel
from shared.models.storage import DownloadFileRequestPayload, DownloadFileRequestResponse, UploadFileRequestPayload, UploadFileRequestResponse
from shared.handlers.TimeHandler import TimeHandler

MultiPartParser.max_file_size = 20 * 1024 * 1024  # setting th emax file size to 20 MB


class FileServices:

    async def __get_credential_by_storage_bucket(self, storage_type: str, bucket_name: str) -> CouchbaseCredentialModel:
        credentialServices = CredentialServices()

        credentials = await credentialServices.list_all_cloud(collection_name="cloud")

        response_list = [ item for item in credentials if storage_type == item.storage_type and bucket_name in item.bucket_names ]

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
        
        credential = await self.__get_credential_by_storage_bucket(storage_type=collection_record.storage_type, bucket_name=collection_record.location)

        if not credential:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail=f"Missing credentials to operate in the following bucket enviroment {collection_record.location}"
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
            file_location=collection_record.location,
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

        blob_name = f"lakehouse/collections/{collection_record.collection_name}/raw/v{catalog_payload.file_version}/{catalog_payload.file_name}"

        decoded_credential = encryptionHandler.decrypt_credentials(credential.credential)

        expiry_in = 30 * 60

        if collection_record.storage_type == "gcs":
            storage_client = storage.Client.from_service_account_info(info=decoded_credential)
            bucket = storage_client.bucket(collection_record.location)
            blob = bucket.blob(blob_name)

            upload_url = blob.generate_signed_url(
                version="v4",
                expiration=expiry_in,
                method="PUT",
                content_type="application/octet-stream"
            )

            storage_client.close()

        elif collection_record.storage_type == "s3":

            credential = AmazonCredentialsModel(**decoded_credential)

            storage_client = boto3.client(
                "s3",
                aws_access_key_id=decoded_credential.get("access_key", ""),
                aws_secret_access_key=decoded_credential.get("secret_access_key", ""),
                region_name=decoded_credential.get("region", "")
            )

            upload_url = storage_client.generate_presigned_url(
                'put_object',
                Params={'Bucket': collection_record.location, 'Key': blob_name, "ContentType": "application/octet-stream"},
                ExpiresIn=expiry_in
            )

            storage_client.close()

        elif collection_record.storage_type == "minio":

            credential = MinioCredentialsModel(**decoded_credential)

            client = Minio(
                credential.url,
                access_key=credential.accessKey,
                secret_key=credential.secretKey,
                secure=True,  # False for plain HTTP
            )

            upload_url = client.presigned_put_object(
                bucket_name=collection_record.location,
                object_name=blob_name,
                expires=timedelta(minutes=30),
            )

        elif collection_record.storage_type == 'hdfs':

            overwrite = False

            hdfs_address = get_ip_address(collection_record.location)

            if not hdfs_address:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail="Invalid namenode address"
                )

            params = {
                "op": "CREATE",
                "overwrite": "true" if overwrite else "false"
            }
            
            request_url = f"{hdfs_address}:9870/webhdfs/v1/{blob_name}"

            response = requests.put(request_url, params=params, allow_redirects=False)

            if not response.status_code == 307:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail=f"Failed to create upload request: {response.text}"
                )
            
            params = {
                "op": "APPEND"
            }

            response = requests.post(request_url, params=params, allow_redirects=False)

            if not response.status_code == 307:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail=f"Failed to create upload request: {response.text}"
                )
            
            upload_url = response.headers["Location"]

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
        
        credential = await self.__get_credential_by_storage_bucket(storage_type=catalog_record.storage_type, bucket_name=catalog_record.file_location)

        if not credential:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail=f"Missing credentials to operate in the following bucket enviroment {catalog_record.file_location}"
            )
        
        decoded_credential = enctyptionHandler.decrypt_credentials(credential.credential)

        expire_time = 30 * 60

        expiry_date = timeHandler.expiry_at(seconds=expire_time)

        expiry_date = timeHandler.datetime_to_unix_timestamp(date=expiry_date)

        download_url = None

        blob_name = f"lakehouse/collections/{catalog_record.collection_name}/{catalog_record.processing_level}/v{catalog_record.file_version}/{catalog_record.file_name}"

        if catalog_record.storage_type == "gcs":
            storage_client = storage.Client.from_service_account_info(info=decoded_credential)
            bucket = storage_client.bucket(catalog_record.file_location)

            blob = bucket.blob(blob_name)

            download_url = blob.generate_signed_url(
                version="v4",
                expiration=expire_time,
                method="GET"
            )


        elif catalog_record.storage_type == "s3":
            credential = AmazonCredentialsModel(**decoded_credential)
            storage_client = boto3.client(
                "s3",
                aws_access_key_id=credential.access_key,
                aws_secret_access_key=credential.secret_access_key,
                region_name=credential.region
            )
            download_url = storage_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': catalog_record.file_location, 'Key': blob_name},
                ExpiresIn=expire_time
            )

        elif catalog_record.storage_type == 'minio':
            credential = MinioCredentialsModel(**decoded_credential)
            
            client = Minio(
                credential.url,
                access_key=credential.accessKey,
                secret_key=credential.secretKey,
                secure=True,  # False for plain HTTP
            )

            download_url = client.presigned_get_object(
                bucket_name=catalog_record.file_location,
                object_name=blob_name,
                expires=timedelta(minutes=30),
            )


        elif catalog_record.storage_type == 'hdfs':
            download_url=f"{catalog_record.file_location}/webhdfs/v1/{blob_name}?op=OPEN"

        return DownloadFileRequestResponse(
            download_url=download_url
        )