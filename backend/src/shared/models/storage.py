from typing import List, Literal, Optional

from pydantic import BaseModel

from shared.models.catalog import CouchbaseCatalogCollectionModel
from shared.models.visas import VisaModel


Storage = Literal['gcs', 's3', 'hdfs', 'minio']
Collections = Literal['files', 'collections']
FileCategory = Literal["structured", "unstructured"]
FileProcessingLevel = Literal["raw", "processed", "curated"]

class UploadFileRequestPayload(BaseModel):
    collection_catalog_id: str 
    file_name: str 
    file_category: FileCategory
    file_version: Optional[int] = 1
    file_size: Optional[int] = None
    public: Optional[bool] = False
    processing_level: Optional[FileProcessingLevel] = "raw"
    file_description: Optional[str] = None

class DownloadFileRequestPayload(BaseModel):
    catalog_file_id: str

class CreateCollectionPayload(BaseModel):
    storage_type: Storage
    collection_name: str
    namenode_address: Optional[str] = None
    bucket_name: Optional[str] = None
    collection_description: Optional[str] = None
    public: Optional[bool] = False
    secret: Optional[bool] = False

class CreateCollectionResponse(BaseModel):
    catalog_record: CouchbaseCatalogCollectionModel
    associated_visa: VisaModel

class UploadFileRequestResponse(BaseModel):
    upload_url: str
    method: str
    catalog_record_id: str

class DownloadFileRequestResponse(BaseModel):
    download_url: str

class StorageBucketItem(BaseModel):
    storage_type: Storage
    bucket_name: str
class GetStorageBucketListResponse(BaseModel):
    bucket_list: List[StorageBucketItem]