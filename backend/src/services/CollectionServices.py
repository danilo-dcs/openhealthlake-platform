import logging

from shared.models.catalog import CatalogCollectionBaseModel, CatalogFilter, CouchbaseCatalogCollectionModel
from shared.models.storage import CreateCollectionPayload, CreateCollectionResponse, UpdateCollectionPayload
from shared.models.visas import AssertedVisaModel, CreateVisaPayload
from fastapi import HTTPException, status
from uuid import UUID
from shared.factories.StorageClientFactory import StorageClientFactory

class CollectionServices:
    logger = logging.getLogger(__name__)

    async def update_collection(
        self,
        collection_id: str,
        payload: UpdateCollectionPayload,
        user_id: str,
    ) -> CouchbaseCatalogCollectionModel:
        from services.CatalogServices import CatalogServices
        from services.VisasServices import VisaServices

        catalog_services = CatalogServices()
        collection = await catalog_services.get_by_id_api(
            document_id=collection_id,
            collection_name="collections",
        )

        if not collection or not collection.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Collection not found")

        if not collection.inserted_by or collection.inserted_by.split(":", 1)[0] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the collection owner can update this collection",
            )

        changes = payload.model_dump(exclude_unset=True)
        old_name = collection.collection_name
        new_name = changes.get("collection_name", collection.collection_name)

        if new_name != old_name:
            filters = [
                CatalogFilter(property_name="collection_name", operator="=", property_value=new_name),
                CatalogFilter(property_name="storage_type", operator="=", property_value=collection.storage_type),
                CatalogFilter(property_name="bucket", operator="=", property_value=collection.bucket),
                CatalogFilter(property_name="status", operator="!=", property_value="deleted"),
            ]
            matches = await catalog_services.get_by_filters(filters=filters)

            if any(record.id != collection_id for record in matches.records):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"The collection {new_name} already exists in this storage location",
                )

        for field, value in changes.items():
            setattr(collection, field, value)

        await catalog_services.couchbaseRepo.upsert_document(
            collection_name="collections",
            key=collection_id,
            value=collection.model_dump(exclude_none=True, exclude_unset=True),
        )

        if new_name != old_name or "collection_description" in changes:
            visa_services = VisaServices()

            visas = await visa_services.list_all()

            visa_name = f"{collection_id}:{new_name}"
            
            old_visa = next((visa for visa in visas if visa.visaName == f"{collection_id}:{old_name}"), None)

            if old_visa:
                await visa_services.update_visa(AssertedVisaModel(
                    id=old_visa.id,
                    visaName=visa_name,
                    visaIssuer=old_visa.visaIssuer,
                    visaDescription=changes.get("collection_description", old_visa.visaDescription),
                    visaSecret=old_visa.visaSecret,
                ))

        return collection

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
        from shared.handlers.EncryptionHandler import EncryptionHandler

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

        if payload.dua:
            try:
                dua_id = str(UUID(payload.dua))
            except (ValueError, TypeError, AttributeError) as error:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid DUA document id.",
                ) from error

            dua_credential = target_credential[0]
            decoded_credential = EncryptionHandler().decrypt_credentials(dua_credential.credential)
            storage_client = StorageClientFactory.create_client(
                storage_type=payload.storage_type,
                bucket=payload.bucket_name,
                credentials=decoded_credential,
                minio_endpoint_use="internal",
            )
            staged_object_name = (
                f"{payload.bucket_name}/documents/pending/{user_id}/{dua_id}.pdf"
            )
            try:
                if storage_client.get_object_size(staged_object_name) is None:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="The uploaded DUA was not found or has expired. Upload it again.",
                    )
            finally:
                storage_client.close()
        else:
            dua_id = None
        
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
            dua=dua_id,
            public=payload.public if payload.public else False,
            secret=payload.secret if payload.secret else False,
            labels=payload.labels
        )

        catalog_item = await catalogServices.create_catalog_record(payload=catalog_record_payload, collection_name="collections")

        if dua_id:
            decoded_credential = EncryptionHandler().decrypt_credentials(target_credential[0].credential)
            storage_client = StorageClientFactory.create_client(
                storage_type=payload.storage_type,
                bucket=payload.bucket_name,
                credentials=decoded_credential,
                minio_endpoint_use="internal",
            )
            staged_object_name = (
                f"{payload.bucket_name}/documents/pending/{user_id}/{dua_id}.pdf"
            )
            final_object_name = (
                f"{payload.bucket_name}/documents/{catalog_item.id}/{dua_id}.pdf"
            )
            try:
                storage_client.move_object(staged_object_name, final_object_name)
            except Exception as error:
                # Keep the provider error in server logs; the public response stays
                # generic because SDK exceptions can contain credential details.
                self.logger.exception(
                    "Could not move staged DUA %s to collection %s (%s/%s)",
                    dua_id,
                    catalog_item.id,
                    payload.storage_type,
                    payload.bucket_name,
                )
                try:
                    if storage_client.get_object_size(final_object_name) is not None:
                        storage_client.delete_object(final_object_name)
                except Exception:
                    self.logger.exception(
                        "Could not remove partially moved DUA %s for collection %s",
                        dua_id,
                        catalog_item.id,
                    )
                try:
                    await catalogServices.delete_catalog_record(
                        document_id=catalog_item.id,
                        collection_name="collections",
                    )
                except Exception:
                    self.logger.exception(
                        "Could not remove collection record %s after DUA move failed",
                        catalog_item.id,
                    )
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="The DUA could not be attached to the new collection.",
                ) from error
            finally:
                storage_client.close()

        visa_payload = CreateVisaPayload(
            visaIssuer=inserted_by,
            visaName=f"{catalog_item.id}:{payload.collection_name}",
            visaDescription= payload.collection_description if payload.collection_description else f"Visa to grant access to collection '{payload.collection_name}'"
        )

        visa_item = await visaServices.create_visa(payload=visa_payload)

        if not visa_item:
            await catalogServices.delete_collection_record(document_id=catalog_item.id, user_id=user.id)
            if dua_id:
                cleanup_client = StorageClientFactory.create_client(
                    storage_type=payload.storage_type,
                    bucket=payload.bucket_name,
                    credentials=EncryptionHandler().decrypt_credentials(target_credential[0].credential),
                    minio_endpoint_use="internal",
                )
                try:
                    final_object_name = (
                        f"{payload.bucket_name}/documents/{catalog_item.id}/{dua_id}.pdf"
                    )
                    if cleanup_client.get_object_size(final_object_name) is not None:
                        cleanup_client.delete_object(final_object_name)
                except Exception:
                    # The collection creation error is primary; storage cleanup is best-effort.
                    pass
                finally:
                    cleanup_client.close()
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
