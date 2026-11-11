"""Provider adapters and factory for the application's storage backends."""

import logging
from typing import Any, Iterator, Literal
from io import BytesIO
from urllib.parse import quote, urlsplit, urlunsplit

import boto3
from botocore.exceptions import ClientError
from fastapi import HTTPException, status
from google.api_core.exceptions import NotFound as GoogleNotFound
from google.cloud import storage
from minio import Minio
from minio.commonconfig import CopySource
from minio.error import S3Error
import requests

from shared.models.credentials import (
    AmazonCredentialsModel,
    GoogleCredentialsModel,
    HadoopCredentialsModel,
    MinioCredentialsModel,
)
from shared.models.env import EnvSettings
from shared.models.storage import Storage

MinioEndpointUse = Literal["public", "internal"]


class GoogleCloudClient:
    def __init__(self, bucket: str, credentials: dict[str, Any]):
        parsed = GoogleCredentialsModel(**credentials)

        if not parsed.project_id:
            raise HTTPException(status_code=400, detail="Google Cloud project_id is required.")

        self.bucket = bucket
        
        self.client = storage.Client.from_service_account_info(info=credentials)

    def generate_upload_url(self, object_name: str, expires: int = 3600, content_type: str = "application/octet-stream") -> str:
        return self.client.bucket(self.bucket).blob(object_name).generate_signed_url(
            version="v4", expiration=expires, method="PUT", content_type=content_type
        )

    def generate_download_url(self, object_name: str, expires: int = 3600) -> str:
        return self.client.bucket(self.bucket).blob(object_name).generate_signed_url(
            version="v4", expiration=expires, method="GET"
        )

    def get_object_size(self, object_name: str) -> int | None:
        try:
            blob = self.client.bucket(self.bucket).blob(object_name)
            blob.reload()
            return int(blob.size)
        except GoogleNotFound:
            return None

    def list_blobs(self, prefix: str = "") -> Iterator[Any]:
        return self.client.list_blobs(self.bucket, prefix=prefix)

    def delete_object(self, object_name: str) -> None:
        self.client.bucket(self.bucket).blob(object_name).delete()

    def upload_object(self, object_name: str, data: bytes, content_type: str) -> None:
        self.client.bucket(self.bucket).blob(object_name).upload_from_file(
            BytesIO(data), size=len(data), content_type=content_type
        )

    def move_object(self, source_name: str, destination_name: str) -> None:
        source = self.client.bucket(self.bucket).blob(source_name)
        self.client.bucket(self.bucket).copy_blob(
            source,
            self.client.bucket(self.bucket),
            new_name=destination_name,
        )
        source.delete()

    def open_object_stream(self, object_name: str):
        blob = self.client.bucket(self.bucket).blob(object_name)
        blob.reload()
        reader = blob.open("rb")

        def chunks():
            try:
                while chunk := reader.read(64 * 1024):
                    yield chunk
            finally:
                reader.close()

        return chunks()

    def close(self) -> None:
        self.client.close()


class AwsClient:
    def __init__(self, bucket: str, credentials: dict[str, Any]):
        parsed = AmazonCredentialsModel(**credentials)

        if not parsed.access_key or not parsed.secret_access_key:
            raise HTTPException(status_code=400, detail="S3 access and secret keys are required.")

        self.bucket = bucket
        
        self.client = boto3.client(
            "s3", aws_access_key_id=parsed.access_key,
            aws_secret_access_key=parsed.secret_access_key, region_name=parsed.region,
        )

    def generate_upload_url(self, object_name: str, expires: int = 3600, content_type: str = "application/octet-stream") -> str:
        return self.client.generate_presigned_url(
            "put_object", Params={"Bucket": self.bucket, "Key": object_name, "ContentType": content_type}, ExpiresIn=expires
        )

    def generate_download_url(self, object_name: str, expires: int = 3600) -> str:
        return self.client.generate_presigned_url(
            "get_object", Params={"Bucket": self.bucket, "Key": object_name}, ExpiresIn=expires
        )

    def get_object_size(self, object_name: str) -> int | None:
        try:
            return int(self.client.head_object(Bucket=self.bucket, Key=object_name)["ContentLength"])
        except ClientError as error:
            if error.response.get("Error", {}).get("Code") in {"404", "NoSuchKey", "NotFound"}:
                return None
            raise

    def list_blobs(self, prefix: str = "") -> Iterator[dict[str, Any]]:
        paginator = self.client.get_paginator("list_objects_v2")
        
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            yield from page.get("Contents", [])

    def delete_object(self, object_name: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=object_name)

    def upload_object(self, object_name: str, data: bytes, content_type: str) -> None:
        self.client.put_object(
            Bucket=self.bucket,
            Key=object_name,
            Body=data,
            ContentLength=len(data),
            ContentType=content_type,
        )

    def move_object(self, source_name: str, destination_name: str) -> None:
        self.client.copy_object(
            Bucket=self.bucket,
            Key=destination_name,
            CopySource={"Bucket": self.bucket, "Key": source_name},
        )
        self.client.delete_object(Bucket=self.bucket, Key=source_name)

    def open_object_stream(self, object_name: str):
        response = self.client.get_object(Bucket=self.bucket, Key=object_name)
        body = response["Body"]

        def chunks():
            try:
                yield from body.iter_chunks(chunk_size=64 * 1024)
            finally:
                body.close()

        return chunks()

    def close(self) -> None:
        self.client.close()


class MinioClient:
    def __init__(self, bucket: str, credentials: dict, endpoint_use: MinioEndpointUse = "public"):

        parsed = MinioCredentialsModel(**credentials)

        if (
            not parsed.url or not parsed.accessKey or 
            not parsed.secretKey
        ):
            raise HTTPException(status_code=400, detail="MinIO URL, access key, and secret key are required.")
        
        self.bucket = bucket

        endpoint, secure = self._minio_endpoint(parsed.url, use=endpoint_use)

        self.client = Minio(endpoint, access_key=parsed.accessKey, secret_key=parsed.secretKey,
                            secure=secure, region=EnvSettings().MINIO_REGION)

    @staticmethod
    def _minio_endpoint(url: str, *, use: MinioEndpointUse) -> tuple[str, bool]:
        parsed_url = urlsplit(url if "://" in url else f"http://{url}")

        if "localhost" in url or "127.0.0.1" in url:
            settings = EnvSettings()
            replacement = settings.MINIO_DOMAIN if use == "public" else settings.MINIO_INTERNAL_ENDPOINT

            if not replacement:
                name = "MINIO_DOMAIN" if use == "public" else "MINIO_INTERNAL_ENDPOINT"
                raise HTTPException(status_code=500, detail=f"{name} must be configured for a localhost MinIO URL.")
            
            replacement_url = urlsplit(replacement if "://" in replacement else f"{parsed_url.scheme}://{replacement.strip()}")

            try:
                original_port, replacement_port = parsed_url.port, replacement_url.port
            except ValueError as error:
                raise HTTPException(status_code=400, detail="Invalid MinIO endpoint configuration.") from error
            
            if replacement_port is None and original_port is not None:
                replacement_url = replacement_url._replace(netloc=f"{replacement_url.netloc}:{original_port}")

            parsed_url = replacement_url

        if (
            parsed_url.scheme not in ("http", "https") or not parsed_url.hostname or
            parsed_url.path not in ("", "/") or parsed_url.query or parsed_url.fragment
        ):
            raise HTTPException(status_code=400, detail="Invalid MinIO endpoint; provide an http(s) host and optional port without a path.")
        
        return parsed_url.netloc, parsed_url.scheme == "https"

    def generate_upload_url(self, object_name: str, expires: int = 3600, content_type: str = "application/octet-stream") -> str:
        from datetime import timedelta
        return self.client.presigned_put_object(self.bucket, object_name, expires=timedelta(seconds=expires))

    def generate_download_url(self, object_name: str, expires: int = 3600) -> str:
        from datetime import timedelta
        return self.client.presigned_get_object(self.bucket, object_name, expires=timedelta(seconds=expires))

    def get_object_size(self, object_name: str) -> int | None:
        try:
            return int(self.client.stat_object(self.bucket, object_name).size)
        except S3Error as error:
            if error.code in {"NoSuchKey", "NoSuchObject"}:
                return None
            raise

    def list_blobs(self, prefix: str = "") -> Iterator[Any]:
        return self.client.list_objects(self.bucket, prefix=prefix, recursive=True)

    def delete_object(self, object_name: str) -> None:
        self.client.remove_object(self.bucket, object_name)

    def upload_object(self, object_name: str, data: bytes, content_type: str) -> None:
        self.client.put_object(
            self.bucket,
            object_name,
            BytesIO(data),
            length=len(data),
            content_type=content_type,
        )

    def move_object(self, source_name: str, destination_name: str) -> None:
        self.client.copy_object(
            self.bucket,
            destination_name,
            CopySource(self.bucket, source_name),
        )
        # A copy is the part required to attach the DUA. Some configured MinIO
        # credentials can write the destination but cannot delete the staged
        # source. Do not report the collection creation as failed after the
        # destination has already been created successfully.
        try:
            self.client.remove_object(self.bucket, source_name)
        except S3Error as error:
            if error.code != "AccessDenied":
                raise
            logging.getLogger(__name__).warning(
                "MinIO copied %s to %s in bucket %s but could not delete the staged source; "
                "grant s3:DeleteObject on the staged object prefix to remove it",
                source_name,
                destination_name,
                self.bucket,
            )

    def open_object_stream(self, object_name: str):
        response = self.client.get_object(self.bucket, object_name)

        def chunks():
            try:
                yield from response.stream(amt=64 * 1024)
            finally:
                response.close()
                response.release_conn()

        return chunks()

    def close(self) -> None:
        # MinIO's client has no persistent session close operation.
        return None


class HdfsClient:
    """WebHDFS adapter; upload URLs are redirects issued by the NameNode."""

    def __init__(self, credentials: dict):
        parsed_credentials = HadoopCredentialsModel(**credentials)

        normalized_url = parsed_credentials.namenode_address if "://" in parsed_credentials.namenode_address else f"http://{parsed_credentials.namenode_address}"

        parsed_url = urlsplit(normalized_url)

        if parsed_url.scheme not in ("http", "https") or not parsed_url.hostname:
            raise HTTPException(status_code=400, detail="Invalid HDFS endpoint.")
        try:
            port = parsed_url.port or 9870
        except ValueError as error:
            raise HTTPException(status_code=400, detail="Invalid HDFS endpoint port.") from error
        
        self.base_url = urlunsplit((parsed_url.scheme, f"{parsed_url.hostname}:{port}", "", "", ""))

        self.username = parsed_credentials.username

        self.session = requests.Session()

    def generate_upload_url(self, object_name: str, *, overwrite: bool = False) -> str:
        request_url = f"{self.base_url}/webhdfs/v1/{quote(object_name, safe='/')}"
        params = {"user.name": self.username} if self.username else {}
        params.update({"op": "CREATE", "overwrite": str(overwrite).lower()})

        response = self.session.put(request_url, params=params, allow_redirects=False, timeout=30)

        if response.status_code != 307:
            raise HTTPException(status_code=502, detail=f"Failed to create HDFS upload request: {response.text}")
        
        params = {"user.name": self.username} if self.username else {}
        params["op"] = "APPEND"

        response = self.session.post(request_url, params=params, allow_redirects=False, timeout=30)

        if response.status_code != 307 or not response.headers.get("Location"):
            raise HTTPException(status_code=502, detail="HDFS did not return an upload location.")
        
        return response.headers["Location"]

    def generate_download_url(self, object_name: str) -> str:
        return f"{self.base_url}/webhdfs/v1/{quote(object_name, safe='/')}?op=OPEN"

    def get_object_size(self, object_name: str) -> int | None:
        url = f"{self.base_url}/webhdfs/v1/{quote(object_name, safe='/')}"
        params = {"op": "GETFILESTATUS"}

        if self.username:
            params["user.name"] = self.username

        response = self.session.get(url, params=params, timeout=30)

        if response.status_code == 404:
            return None
        
        response.raise_for_status()

        return int(response.json()["FileStatus"]["length"])

    def list_blobs(self, path: str) -> list[dict[str, Any]]:
        url = f"{self.base_url}/webhdfs/v1/{quote(path, safe='/')}"
        params = {"op": "LISTSTATUS"}

        if self.username:
            params["user.name"] = self.username

        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()

        return response.json().get("FileStatuses", {}).get("FileStatus", [])

    def delete_object(self, object_name: str) -> None:
        url = f"{self.base_url}/webhdfs/v1/{quote(object_name, safe='/')}"
        params = {"op": "DELETE", "user.name": self.username} if self.username else {"op": "DELETE"}

        response = self.session.delete(url, params=params, timeout=30)

        if response.status_code != 200 or not response.json().get("boolean", False):
            raise HTTPException(status_code=502, detail=f"Error deleting HDFS file: {response.text}")

    def upload_object(self, object_name: str, data: bytes, content_type: str) -> None:
        upload_url = self.generate_upload_url(object_name)
        response = self.session.post(
            upload_url,
            data=data,
            headers={"Content-Type": content_type},
            timeout=60,
        )
        response.raise_for_status()

    def move_object(self, source_name: str, destination_name: str) -> None:
        url = f"{self.base_url}/webhdfs/v1/{quote(source_name, safe='/')}"
        params = {"op": "RENAME", "destination": destination_name}
        if self.username:
            params["user.name"] = self.username

        response = self.session.put(url, params=params, timeout=30)
        response.raise_for_status()
        if not response.json().get("boolean", False):
            raise HTTPException(status_code=502, detail="HDFS could not move the staged DUA.")

    def open_object_stream(self, object_name: str):
        url = f"{self.base_url}/webhdfs/v1/{quote(object_name, safe='/')}"
        params = {"op": "OPEN"}
        if self.username:
            params["user.name"] = self.username

        response = self.session.get(
            url,
            params=params,
            stream=True,
            timeout=(30, 60),
        )
        response.raise_for_status()

        def chunks():
            try:
                yield from response.iter_content(chunk_size=64 * 1024)
            finally:
                response.close()

        return chunks()

    def close(self) -> None:
        self.session.close()


class StorageClientFactory:
    """Construct the storage adapter selected by ``storage_type``."""

    @staticmethod
    def create_client(
        storage_type: Storage,
        bucket: str,
        credentials: dict,
        minio_endpoint_use: MinioEndpointUse = "public",
    ) -> GoogleCloudClient | AwsClient | MinioClient | HdfsClient:
        
        if storage_type == "gcs":
            return GoogleCloudClient(bucket, credentials)
        if storage_type == "s3":
            return AwsClient(bucket, credentials)
        if storage_type == "minio":
            return MinioClient(bucket, credentials, endpoint_use=minio_endpoint_use)
        if storage_type == "hdfs":
            return HdfsClient(credentials)
        raise HTTPException(status_code=400, detail=f"Unsupported storage type '{storage_type}'.")
