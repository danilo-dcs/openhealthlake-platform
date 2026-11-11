from typing import List

from fastapi import HTTPException
import uuid6
from repositories.CouchbaseRepository import CouchbaseRepository

from shared.models.access_requests import (
    AccessRequestModel,
    AccessRequestSearchPayload,
    CouchbaseAccessRequestModel,
    GrantAccessRequestPayload,
    InviteCollaboratorPayload,
    RevokeAccessRequestPayload,
)
from shared.handlers.CouchbaseQueryBuilder import CouchbaseQueryBuilder

class AccessRequestServices:
    def __init__(self):
        self.scope = "users"

        self.couchbaseRepo = CouchbaseRepository(
            scope=self.scope,
        )

        self.queryBuilder = CouchbaseQueryBuilder(
            scope=self.scope, collection="access_requests"
        )

    async def invite_collaborator(
        self, payload: InviteCollaboratorPayload, owner_id: str
    ) -> dict[str, str]:
        from services.CatalogServices import CatalogServices
        from services.UserServices import UserServices
        from shared.handlers.MailingClient import MailingClient

        email = payload.email.strip()
        if not email or "@" not in email:
            raise HTTPException(status_code=400, detail="A valid user email is required")

        catalog_services = CatalogServices()
        user_services = UserServices()
        collection = await catalog_services.get_by_id_api(
            document_id=payload.collection_id, collection_name="collections"
        )
        if not collection:
            raise HTTPException(status_code=404, detail="Collection not found")

        collection_owner_id = (collection.inserted_by or "").split(":", 1)[0]
        if owner_id != collection_owner_id:
            raise HTTPException(
                status_code=403,
                detail="Only the collection owner can invite collaborators",
            )

        invited_user = await user_services.list_by_email(email=email)
        if not invited_user:
            raise HTTPException(
                status_code=404,
                detail="The invited user is not registered in the system",
            )

        owner_passport = await user_services.list_passport_by_user_id(user_uuid=owner_id)
        visa_assertions = owner_passport.passportVisaAssertions if owner_passport else []
        target_visa = next(
            (
                assertion.passportVisa
                for assertion in visa_assertions or []
                if assertion.passportVisa.visaName
                == f"{collection.id}:{collection.collection_name}"
            ),
            None,
        )
        if not target_visa:
            raise HTTPException(
                status_code=404,
                detail="The collection access visa could not be found",
            )

        await user_services.grant_visas_to_user(
            user_uuid=invited_user.id, visa_uuids=[target_visa.id]
        )

        mailing_client = MailingClient()
        mailing_client.add_subject(
            f"You were added as a collaborator to {collection.collection_name}"
        ).add_text_body(
            f"You were added as a collaborator to the collection {collection.collection_name}.\n"
            "You can now access it from your OpenHealthLake account."
        )
        if not mailing_client.send_email(invited_user.email):
            raise HTTPException(
                status_code=502,
                detail="Access was granted, but the collaborator notification email could not be sent",
            )

        return {
            "message": f"{email} was added as a collaborator to {collection.collection_name}"
        }

    async def create_request(
        self, payload: AccessRequestModel
    ) -> CouchbaseAccessRequestModel:
        from services.CatalogServices import CatalogServices
        from services.UserServices import UserServices
        from shared.handlers.TimeHandler import TimeHandler
        from shared.handlers.MailingClient import MailingClient

        catalogServices = CatalogServices()
        userServices = UserServices()
        timeHandler = TimeHandler()

        owner_details = await userServices.list_info_by_user_id(
            user_uuid=payload.owner_id
        )
        requestor_details = await userServices.list_info_by_user_id(
            user_uuid=payload.requested_by
        )
        collection_record = await catalogServices.get_by_id_api(
            document_id=payload.collection_id, collection_name="collections"
        )

        if not owner_details:
            raise HTTPException(status_code=400, detail="Invalid owner_id")

        if not requestor_details:
            raise HTTPException(status_code=400, detail="Invalid requested_by id")

        if not collection_record:
            raise HTTPException(status_code=400, detail="Invalid collection_id")

        couchbaseRecord = CouchbaseAccessRequestModel(
            id=str(uuid6.uuid7()),
            collection_id=payload.collection_id,
            owner_id=owner_details.id,
            owner_email=owner_details.email,
            requested_by=requestor_details.id,
            requestor_email=requestor_details.email,
            requested_at=int(
                float(timeHandler.datetime_to_unix_timestamp(timeHandler.utc_now()))
            ),
            status="requested",
        )

        await self.couchbaseRepo.create_document(
            collection_name="access_requests",
            key=couchbaseRecord.id,
            value=couchbaseRecord.model_dump(exclude_none=True, exclude_unset=True),
        )

        mailing_client = MailingClient()

        mailing_client.add_subject(
            f"Access requested to collection {collection_record.collection_name}"
        ).add_text_body(
            f"You have a new request from {couchbaseRecord.requestor_email} to access your collection {collection_record.collection_name}.\n"
            f"Please log into your account to accept or reject it!"
        )
        
        mailing_client.send_email(couchbaseRecord.owner_email)

        return couchbaseRecord

    async def get_by_id(self, document_id: str) -> CouchbaseAccessRequestModel:
        response = await self.couchbaseRepo.get_document_by_id(
            collection_name="access_requests", document_key=document_id
        )

        if not response:
            return {}

        return [
            CouchbaseAccessRequestModel(**item["access_requests"]) for item in response
        ][0]

    async def grant_access(self, payload: GrantAccessRequestPayload, user_id: str):
        from services.UserServices import UserServices
        from services.CatalogServices import CatalogServices
        from shared.handlers.TimeHandler import TimeHandler
        from shared.handlers.MailingClient import MailingClient

        userServices = UserServices()
        catalogServices = CatalogServices()
        timeHandler = TimeHandler()

        access_request = await self.get_by_id(document_id=payload.access_request_id)

        if not access_request:
            raise HTTPException(status_code=400, detail="Invalid request id")

        if access_request.status == "granted":
            raise HTTPException(
                status_code=400, detail="Access request already granted"
            )
        elif access_request.status != "requested":
            raise HTTPException(
                status_code=400,
                detail="Invalid access request: a new request has to be made",
            )

        if user_id != access_request.owner_id:
            raise HTTPException(
                status_code=401,
                detail="Unauthorized: operation valid only for collection owners",
            )

        collection = await catalogServices.get_by_id_api(
            document_id=access_request.collection_id, collection_name="collections"
        )

        if not collection:
            raise HTTPException(
                status_code=400,
                detail="Access request error: requested collection does not exist",
            )

        passport = await userServices.list_passport_by_user_id(
            user_uuid=access_request.owner_id
        )

        visas = [
            assertion.passportVisa for assertion in passport.passportVisaAssertions
        ]

        target_visa = [
            visa
            for visa in visas
            if visa.visaName == f"{collection.id}:{collection.collection_name}"
        ]

        if not target_visa:
            raise HTTPException(
                status_code=400,
                detail="Access request error: requested collection does not exist",
            )

        target_visa = target_visa[0]

        await userServices.grant_visas_to_user(
            user_uuid=access_request.requested_by, visa_uuids=[target_visa.id]
        )

        updated_access_request = access_request.model_copy()

        updated_access_request.status = "granted"
        updated_access_request.requested_at = int(
            float(timeHandler.datetime_to_unix_timestamp(timeHandler.utc_now()))
        )
        updated_access_request.id = str(uuid6.uuid7())

        mailing_client = MailingClient()

        mailing_client.add_subject(
            f"Access granted for collection {collection.collection_name}"
        ).add_text_body(
            f"Your request to access the collection {collection.collection_name} was granted by the collection's owner.\n"
        )
        
        mailing_client.send_email(updated_access_request.requestor_email)

        await self.couchbaseRepo.create_document(
            collection_name="access_requests",
            key=updated_access_request.id,
            value=updated_access_request.model_dump(
                exclude_none=True, exclude_unset=True
            ),
        )

        return updated_access_request

    async def revoke_access(self, payload: RevokeAccessRequestPayload, user_id: str):
        from services.UserServices import UserServices
        from services.CatalogServices import CatalogServices
        from shared.handlers.TimeHandler import TimeHandler
        from shared.handlers.MailingClient import MailingClient

        userServices = UserServices()
        catalogServices = CatalogServices()
        timeHandler = TimeHandler()

        access_request = await self.get_by_id(document_id=payload.access_request_id)

        if not access_request:
            raise HTTPException(status_code=400, detail="Invalid request id")

        if access_request.status == "revoked":
            raise HTTPException(
                status_code=400, detail="Access request already revoked"
            )
        elif access_request.status != "granted":
            raise HTTPException(
                status_code=400,
                detail="Invalid access request: a new request has to be made",
            )

        if user_id != access_request.owner_id:
            raise HTTPException(
                status_code=401,
                detail="Unauthorized: operation valid only for collection owners",
            )

        collection = await catalogServices.get_by_id_api(
            document_id=access_request.collection_id, collection_name="collections"
        )

        if not collection:
            raise HTTPException(
                status_code=400,
                detail="Access request error: requested collection does not exist",
            )

        passport = await userServices.list_passport_by_user_id(
            user_uuid=access_request.requested_by
        )

        visas = [
            assertion.passportVisa for assertion in passport.passportVisaAssertions
        ]

        target_visa = [
            visa
            for visa in visas
            if visa.visaName == f"{collection.id}:{collection.collection_name}"
        ]

        if not target_visa:
            raise HTTPException(
                status_code=400,
                detail="Access request error: requested collection does not exist",
            )

        target_visa = target_visa[0]

        # revoke visas from user
        await userServices.revoke_visas_from_user(
            user_uuid=access_request.requested_by, visa_uuids=[target_visa.id]
        )

        updated_access_request = access_request.model_copy()

        updated_access_request.status = "revoked"
        updated_access_request.requested_at = int(
            float(timeHandler.datetime_to_unix_timestamp(timeHandler.utc_now()))
        )
        updated_access_request.id = str(uuid6.uuid7())

        await self.couchbaseRepo.create_document(
            collection_name="access_requests",
            key=updated_access_request.id,
            value=updated_access_request.model_dump(
                exclude_none=True, exclude_unset=True
            ),
        )

        mailing_client = MailingClient()

        mailing_client.add_subject(
            f"Access request rejected for collection {collection.collection_name}"
        ).add_text_body(
            f"Your request to access the collection {collection.collection_name} was rejected by the collection's owner.\n"
        )
        
        mailing_client.send_email(updated_access_request.requestor_email)

        return updated_access_request

    async def search_by_owner_and_collections(
        self, payload: AccessRequestSearchPayload
    ) -> List[CouchbaseAccessRequestModel]:
        dumped_payload = payload.model_dump(
            exclude_defaults=True, exclude_none=True, exclude_unset=True
        )

        querybuilder = self.queryBuilder.instance_copy(deep=True)

        for key, value in dumped_payload.items():
            querybuilder.where(field=key, op="=", value=value)

        query = querybuilder.order_by_field("requested_at", direction="DESC").build()

        results = await self.couchbaseRepo.query(statement=query)

        if not results:
            return list()

        parsed_results = [
            CouchbaseAccessRequestModel(**item["access_requests"]) for item in results
        ]

        return parsed_results

    async def delete_access_request(self, user_id: str, document_id: str) -> str:
        from services.UserServices import UserServices

        userServices = UserServices()

        access_request = await self.get_by_id(document_id=document_id)

        if not access_request:
            raise HTTPException(status_code=400, detail="Invalid request id")

        owner_details = await userServices.list_info_by_user_id(
            user_uuid=access_request.owner_id
        )
        requestor_details = await userServices.list_info_by_user_id(
            user_uuid=access_request.requested_by
        )

        if user_id not in [owner_details.id, requestor_details.id]:
            raise HTTPException(
                status_code=401,
                detail="Unauthorized operation: user can not delete this access request",
            )

        await self.couchbaseRepo.delete_document(
            collection_name="access_requests", document_key=document_id
        )

        return document_id
