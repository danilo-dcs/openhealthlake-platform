
from typing import List, Literal, Optional
from pydantic import BaseModel

FileStatus = Literal["ready", "processing", "uploading", "deleted"]

CatalogProcessingLevelFilter = Literal["raw", "processed", "curated"]

FilterOperators = Literal["=",">","<", ">=", "<=", '*', "!="]

FileCategory = Literal["structured", "unstructured"]

CatalogType = Literal["files", "collections"]
class CatalogFileBaseModel(BaseModel):
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    collection_id: Optional[str] = None
    collection_name: Optional[str] = None
    processing_level: Optional[str] = None
    storage_type: Optional[str] = None
    file_location: Optional[str] = None
    inserted_by: Optional[str] = None
    inserted_at: Optional[int] = None
    file_description: Optional[str] = None
    file_category: Optional[FileCategory] = None
    file_status: Optional[FileStatus] = None
    expires_at: Optional[int] = None
    file_version: Optional[int] = None
    public: Optional[bool] = False

class CatalogCollectionBaseModel(BaseModel):
    collection_name: Optional[str] = None
    storage_type: Optional[str] = None
    inserted_by: Optional[str] = None
    inserted_at: Optional[int] = None
    status: Optional[FileStatus] = None
    location: Optional[str] = None
    collection_description: Optional[str] = None
    public: Optional[bool] = False
    secret: Optional[bool] = False


class CouchbaseCatalogFileModel(CatalogFileBaseModel):
    id: Optional[str] = None

class CouchbaseCatalogCollectionModel(CatalogCollectionBaseModel):
    id: Optional[str] = None

class CatalogFilter(BaseModel):
    property_name: str
    operator: FilterOperators
    property_value: str | int | float

class CatalogFilterPayload(BaseModel):
    filters: List[CatalogFilter]
    page_number: Optional[int] = 1
    # processing_level: Optional[CatalogProcessingLevelFilter] = None

class SetRecordStatusPayload(BaseModel):
    status: FileStatus


class GetFilesCatalogResponse(BaseModel):
    records: List[CouchbaseCatalogFileModel]
    next_page: Optional[int] = None
    total: Optional[int] = None

class GetCollectionsCatalogResponse(BaseModel):
    records: List[CouchbaseCatalogCollectionModel]
    next_page: Optional[int] = None
    total: Optional[int] = None