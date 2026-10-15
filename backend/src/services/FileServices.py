from datetime import timedelta
from urllib.parse import quote, urlsplit

import boto3
from google.cloud import storage
from google.api_core.exceptions import NotFound as GoogleNotFound
# from hdfs import InsecureClient
from minio import Minio
from minio.error import S3Error

from fastapi import HTTPException, status
from botocore.exceptions import ClientError
import requests


from starlette.formparsers import MultiPartParser

from services.CatalogServices import CatalogServices
from services.CredentialServices import CredentialServices
from shared.functions.regex import get_ip_address
from shared.models.catalog import CatalogFileBaseModel, CatalogFilter, CouchbaseCatalogFileModel, CouchbaseCatalogCollectionModel
from shared.models.credentials import AmazonCredentialsModel, CouchbaseCredentialModel, GoogleCredentialsModel, MinioCredentialsModel
from shared.models.env import EnvSettings
from shared.models.storage import DownloadFileRequestPayload, DownloadFileRequestResponse, UploadFileRequestPayload, UploadFileRequestResponse
from shared.handlers.TimeHandler import TimeHandler

MultiPartParser.max_file_size = 20 * 1024 * 1024  # setting th emax file size to 20 MB


class FileServices:

    @staticmethod
    def __minio_client_options(url: str) -> tuple[str, bool]:
        """Return the host:port and TLS flag expected by the MinIO SDK."""
        parsed_url = urlsplit(url if "://" in url else f"http://{url}")

        if "localhost" in url or "127.0.0.1" in url:
            env = EnvSettings()
            if not env.MINIO_DOMAIN:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="MINIO_DOMAIN must be configured when the MinIO credential uses localhost.",
                )

            replacement = env.MINIO_DOMAIN.strip()
            replacement_url = urlsplit(
                replacement if "://" in replacement else f"{parsed_url.scheme}://{replacement}"
            )
            try:
                if replacement_url.port is None and parsed_url.port is not None:
                    replacement_url = replacement_url._replace(
                        netloc=f"{replacement_url.netloc}:{parsed_url.port}"
                    )
            except ValueError as error:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid MINIO_DOMAIN configuration. Missing minio port",
                ) from error

            url = replacement_url.geturl()
            parsed_url = urlsplit(url)

        if parsed_url.scheme not in ("http", "https") or not parsed_url.hostname:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid MinIO endpoint. Provide an http(s) URL with a host and optional port.",
            )

        if parsed_url.path not in ("", "/") or parsed_url.query or parsed_url.fragment:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid MinIO endpoint. Paths, query strings, and fragments are not supported.",
            )

        return parsed_url.netloc, parsed_url.scheme == "https"

    @staticmethod
    def __file_object_name(file_record: CatalogFileBaseModel) -> str:
        env = EnvSettings()
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

        expiry_in = 30 * 60

        if collection_record.storage_type == "gcs":

            credential = GoogleCredentialsModel(**decoded_credential)

            if not credential.project_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail="Invalid AWS credential"
                )
 
            storage_client = storage.Client.from_service_account_info(info=decoded_credential)

            bucket = storage_client.bucket(collection_record.bucket)
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

            if not credential.access_key:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail="Invalid Google Cloud credential"
                )

            storage_client = boto3.client(
                "s3",
                aws_access_key_id=decoded_credential.get("access_key", ""),
                aws_secret_access_key=decoded_credential.get("secret_access_key", ""),
                region_name=decoded_credential.get("region", "")
            )

            upload_url = storage_client.generate_presigned_url(
                'put_object',
                Params={'Bucket': collection_record.bucket, 'Key': blob_name, "ContentType": "application/octet-stream"},
                ExpiresIn=expiry_in
            )

            storage_client.close()

        elif collection_record.storage_type == "minio":

            credential = MinioCredentialsModel(**decoded_credential)

            if not credential.url:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail="Invalid MinIO credential"
                )

            endpoint, secure = self.__minio_client_options(credential.url)

            minio_region = EnvSettings().MINIO_REGION

            client = Minio(
                endpoint=endpoint,
                access_key=credential.accessKey,
                secret_key=credential.secretKey,
                secure=secure,
                region=minio_region
            )

            upload_url = client.presigned_put_object(
                bucket_name=collection_record.bucket,
                object_name=blob_name,
                expires=timedelta(minutes=30),
            )

        elif collection_record.storage_type == 'hdfs':

            overwrite = False

            hdfs_address = get_ip_address(collection_record.bucket)

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
        credential = EncryptionHandler().decrypt_credentials(credential_record.credential)
        object_name = self.__file_object_name(file_record)
        object_size: int

        if file_record.storage_type == "gcs":
            storage_client = storage.Client.from_service_account_info(info=credential)
            try:
                blob = storage_client.bucket(file_record.file_bucket).blob(object_name)
                blob.reload()
                object_size = int(blob.size)
            except GoogleNotFound as error:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Uploaded object is not available yet.",
                ) from error
            finally:
                storage_client.close()

        elif file_record.storage_type == "s3":
            s3_client = boto3.client(
                "s3",
                aws_access_key_id=credential.get("access_key", ""),
                aws_secret_access_key=credential.get("secret_access_key", ""),
                region_name=credential.get("region", ""),
            )
            try:
                metadata = s3_client.head_object(
                    Bucket=file_record.file_bucket,
                    Key=object_name,
                )
                object_size = int(metadata["ContentLength"])
            except ClientError as error:
                error_code = error.response.get("Error", {}).get("Code", "")
                if error_code in {"404", "NoSuchKey", "NotFound"}:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Uploaded object is not available yet.",
                    ) from error
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Unable to verify the uploaded object in S3.",
                ) from error
            finally:
                s3_client.close()

        elif file_record.storage_type == "minio":
            minio_credential = MinioCredentialsModel(**credential)
            if not minio_credential.url:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid MinIO credential.",
                )
            endpoint, secure = self.__minio_client_options(minio_credential.url)
            minio_client = Minio(
                endpoint,
                access_key=minio_credential.accessKey,
                secret_key=minio_credential.secretKey,
                secure=secure,
                region=EnvSettings().MINIO_REGION,
            )
            try:
                metadata = minio_client.stat_object(file_record.file_bucket, object_name)
                object_size = int(metadata.size)
            except S3Error as error:
                if error.code in {"NoSuchKey", "NoSuchObject"}:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Uploaded object is not available yet.",
                    ) from error
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Unable to verify the uploaded object in MinIO.",
                ) from error

        elif file_record.storage_type == "hdfs":
            hdfs_address = get_ip_address(file_record.file_bucket)
            if not hdfs_address:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid namenode address.",
                )

            response = requests.get(
                f"{hdfs_address}:9870/webhdfs/v1/{quote(object_name, safe='/')}",
                params={"op": "GETFILESTATUS"},
                timeout=30,
            )
            if response.status_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Uploaded object is not available yet.",
                )
            if not response.ok:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Unable to verify the uploaded object in HDFS.",
                )
            object_size = int(response.json()["FileStatus"]["length"])

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported storage type '{file_record.storage_type}'.",
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

        if catalog_record.storage_type == "gcs":

            credential = GoogleCredentialsModel(**decoded_credential)
            
            if not credential.project_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail="Invalid AWS credential"
                )

            storage_client = storage.Client.from_service_account_info(info=decoded_credential)

            bucket = storage_client.bucket(catalog_record.file_bucket)

            blob = bucket.blob(blob_name)

            download_url = blob.generate_signed_url(
                version="v4",
                expiration=expire_time,
                method="GET"
            )


        elif catalog_record.storage_type == "s3":

            credential = AmazonCredentialsModel(**decoded_credential)
            
            if not credential.access_key:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, 
                    detail="Invalid Google Cloud credential"
                )

            storage_client = boto3.client(
                "s3",
                aws_access_key_id=credential.access_key,
                aws_secret_access_key=credential.secret_access_key,
                region_name=credential.region
            )
            download_url = storage_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': catalog_record.file_bucket, 'Key': blob_name},
                ExpiresIn=expire_time
            )

        elif catalog_record.storage_type == 'minio':
            credential = MinioCredentialsModel(**decoded_credential)
            
            if not credential.url:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid MinIO credential",
                )

            endpoint, secure = self.__minio_client_options(credential.url)

            client = Minio(
                endpoint,
                access_key=credential.accessKey,
                secret_key=credential.secretKey,
                secure=secure,
                region=EnvSettings().MINIO_REGION,
            )

            download_url = client.presigned_get_object(
                bucket_name=catalog_record.file_bucket,
                object_name=blob_name,
                expires=timedelta(minutes=30),
            )


        elif catalog_record.storage_type == 'hdfs':
            download_url=f"{catalog_record.file_bucket}/webhdfs/v1/{blob_name}?op=OPEN"

        return DownloadFileRequestResponse(
            download_url=download_url
        )
