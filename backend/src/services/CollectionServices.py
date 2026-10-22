from shared.models.catalog import CatalogCollectionBaseModel, CatalogFilter
from shared.models.storage import CreateCollectionPayload, CreateCollectionResponse
from shared.models.visas import CreateVisaPayload
from fastapi import HTTPException, status

class CollectionServices:
    async def create_collection(
        self,
        payload: CreateCollectionPayload,
        user_id: str
    ) -> CreateCollectionResponse:
        
        from services.CredentialServices import CredentialServices
        from services.CatalogServices import CatalogServices
        from services.VisasServices import VisaServices
        from services.UserServices import UserServices

        from shared.handlers.TimeHandler import TimeHandler

        credentialServices = CredentialServices()
        catalogServices = CatalogServices()
        visaServices = VisaServices()
        userServices = UserServices()
        timeHandler = TimeHandler()

        credentials = await credentialServices.list_all_cloud(collection_name='cloud')

        target_credential = [ item for item in credentials if item.storage_type == payload.storage_type and payload.bucket_name in item.bucket_names ]

        if not target_credential:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Operetion not allowed due to the lack of storage credentials for specified storage_type and bucket_name"
            )

        user = await userServices.list_info_by_user_id(user_uuid=user_id)

        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Unable to find user {user_id}")

        filters = [
            CatalogFilter(
                property_name="collection_name",
                operator="=",
                property_value=payload.collection_name
            ),
            CatalogFilter(
                property_name="storage_type",
                operator="=",
                property_value=payload.storage_type
            ),
            CatalogFilter(
                property_name="bucket",
                operator="=",
                property_value=payload.bucket_name,
            ),
            CatalogFilter(
                property_name="status",
                operator="!=",
                property_value="deleted"
            )
        ]

        collections_search = await catalogServices.get_by_filters(filters=filters)

        if collections_search.records:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"The Collection {payload.collection_name} already exists in the storage type {payload.storage_type}. Please provide an unique collection name or any other additional storage type"
            )
        
        inserted_by = f"{user_id}:{user.email}"

        inserted_at = int(float(timeHandler.datetime_to_unix_timestamp(timeHandler.utc_now())))

        catalog_record_payload = CatalogCollectionBaseModel(
            collection_name=payload.collection_name,
            storage_type=payload.storage_type,
            bucket=payload.bucket_name,
            status='ready',
            inserted_by=inserted_by,
            inserted_at=inserted_at,
            collection_description=payload.collection_description,
            public=payload.public if payload.public else False,
            secret=payload.secret if payload.secret else False,
            labels=payload.labels
        )

        catalog_item = await catalogServices.create_catalog_record(payload=catalog_record_payload, collection_name="collections")

        visa_payload = CreateVisaPayload(
            visaIssuer=inserted_by,
            visaName=f"{catalog_item.id}:{payload.collection_name}",
            visaDescription= payload.collection_description if payload.collection_description else f"Visa to grant access to collection '{payload.collection_name}'"
        )

        visa_item = await visaServices.create_visa(payload=visa_payload)

        if not visa_item:
            await catalogServices.delete_collection_record(document_id=catalog_item.id, user_id=user.id)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Unable to create visa for new collection"
            )

        await credentialServices.grant_credential_to_visa(credential_uuid=target_credential[0].id, visa_uuid=visa_item.id)

        await userServices.grant_visas_to_user(user_uuid=user_id, visa_uuids=[visa_item.id])
        
        return CreateCollectionResponse(
            associated_visa=visa_item,
            catalog_record=catalog_item
        )