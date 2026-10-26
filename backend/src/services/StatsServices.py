from repositories.CouchbaseRepository import CouchbaseRepository
from services.CredentialServices import CredentialServices
from shared.models.catalog import CouchbaseCatalogCollectionModel, CouchbaseCatalogFileModel
from shared.models.stats import (
    CollectionVisibilityStatsResponse,
    FileProcessingStatsResponse,
    TotalStatsResponse,
)


class StatsServices:
    def __init__(self) -> None:
        self.catalog_repo = CouchbaseRepository(scope="catalogs")
        self.credential_services = CredentialServices()

    async def get_bucket_total(self) -> TotalStatsResponse:
        credentials = await self.credential_services.list_all_cloud(collection_name="cloud")
        linked_buckets = {
            (credential.storage_type, bucket_name)
            for credential in credentials
            for bucket_name in (credential.bucket_names or [])
        }
        return TotalStatsResponse(total=len(linked_buckets))

    async def get_collection_total(self) -> TotalStatsResponse:
        records = await self.catalog_repo.get_documents(collection_name="collections")
        collections = [
            CouchbaseCatalogCollectionModel(**record["collections"])
            for record in records
        ]
        total = sum(collection.status != "deleted" for collection in collections)
        return TotalStatsResponse(total=total)

    async def get_collection_visibility(self) -> CollectionVisibilityStatsResponse:
        records = await self.catalog_repo.get_documents(collection_name="collections")
        collections = [
            CouchbaseCatalogCollectionModel(**record["collections"])
            for record in records
        ]
        active_collections = [
            collection for collection in collections if collection.status != "deleted"
        ]
        public_count = sum(bool(collection.public) for collection in active_collections)
        
        return CollectionVisibilityStatsResponse(
            public=public_count,
            private=len(active_collections) - public_count,
        )

    async def get_file_total(self) -> TotalStatsResponse:
        records = await self.catalog_repo.get_documents(collection_name="files")
        files = [
            CouchbaseCatalogFileModel(**record["files"])
            for record in records
        ]
        total = sum(file.file_status != "deleted" for file in files)
        return TotalStatsResponse(total=total)

    async def get_file_processing_levels(self) -> FileProcessingStatsResponse:
        records = await self.catalog_repo.get_documents(collection_name="files")
        files = [
            CouchbaseCatalogFileModel(**record["files"])
            for record in records
        ]
        active_files = [file for file in files if file.file_status != "deleted"]
        return FileProcessingStatsResponse(
            raw=sum(file.processing_level == "raw" for file in active_files),
            processed=sum(file.processing_level == "processed" for file in active_files),
            curated=sum(file.processing_level == "curated" for file in active_files),
        )
