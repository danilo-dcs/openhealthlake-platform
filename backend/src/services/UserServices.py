from typing import List
import uuid6
from datetime import datetime, timedelta

import requests
from repositories.CouchbaseRepository import CouchbaseRepository

from shared.models.catalog import CatalogFilter, CouchbaseCatalogCollectionModel

from shared.models.env import EnvSettings
from shared.models.users import (
    CouchbaseUserAssertionModel,
    CouchbaseUserModel,
    CouchbaseUserModelNoPassword,
    CreateUserPayload,
    PassportUserAssertionModel,
    PasswordChangeRequest,
    PasswordRecoveryModel,
    PasswordRecoveryRequest
)
from shared.models.visas import PassportVisaAssertion, VisaModel
from shared.handlers.CouchbaseQueryBuilder import CouchbaseQueryBuilder

from fastapi import HTTPException, status

from shared.handlers.EncryptionHandler import EncryptionHandler
from shared.handlers.MailingClient import MailingClient


class UserServices:
    def __init__(self) -> None:
        settings = EnvSettings()

        self.scope = "users"
        self.couchbaseRepo = CouchbaseRepository(
            scope=self.scope,
        )
        self.passport_broker_url = settings.PASSPORT_BROKER_SERVICE_URL

    async def delete_user(self, user_uuid: str, requestor_id: str, requestor_role: str, new_owner_id: str = None) -> str:
        from services.CatalogServices import CatalogServices

        passport_broker_url = f"{self.passport_broker_url}/admin/ga4gh/passport/v1/users/{user_uuid}"

        user = await self.list_info_by_user_id(user_uuid=user_uuid)

        if not user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"User {user_uuid} not found! Please provide a valid user id")
        
        if user_uuid != requestor_id and requestor_role != "admin":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized! Only admin users can delete other users")
        
        user_passport = await self.list_passport_by_user_id(user_uuid=user_uuid)

        if new_owner_id:
            if not user_passport:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to list user passports/collections")
        
            new_owner = await self.list_info_by_user_id(user_uuid=new_owner_id)

            if not new_owner:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"User {user_uuid} not found! Please specify a valid user id for ownership transfer")

            await self.transfer_collections_ownership(owner_id=user_uuid, new_owner_id=new_owner.id, new_owner_email=new_owner.email, owner_passport=user_passport, user_id=user_uuid)

        else:
            catalogServices = CatalogServices()

            filters = [ 
                CatalogFilter(
                    property_name="inserted_by",
                    operator="*",
                    property_value=user_uuid
                )
            ]

            owned_collections = await catalogServices.get_by_filters(filters=filters, user_id=user_uuid, collection_name="collections")

            try:
                if owned_collections:
                    for collection in owned_collections.records:
                        await catalogServices.delete_collection_record(document_id=collection.id, user_id=user_uuid)
            except Exception as e:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"{str(e)}")
            
        if user_passport:
            await self.couchbaseRepo.delete_document(
                collection_name="visa", document_key=user_passport.id
            )

        requests.delete(url=passport_broker_url)

        await self.couchbaseRepo.delete_document(
            collection_name="info", document_key=user_uuid
        )

        return user_uuid

    async def create_user(
        self, payload: CreateUserPayload
    ) -> CouchbaseUserModelNoPassword:
        from services.AuthServices import AuthServices

        user_search = await self.list_by_email(email=payload.email)

        if user_search:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User {payload.email} already exists!"
            )

        authServices = AuthServices()

        user_id = str(uuid6.uuid7())

        hashed_password = authServices.word_to_hash(payload.password)

        full_payload = CouchbaseUserModel(
            id=user_id,
            name=payload.name,
            email=payload.email,
            password=hashed_password,
            active=True,
            role="user"
        )

        await self.couchbaseRepo.create_document(
            collection_name="info",
            key=user_id,
            value=full_payload.model_dump(exclude_none=True, exclude_unset=True),
        )

        passport_broker_url = (
            f"{self.passport_broker_url}/admin/ga4gh/passport/v1/users"
        )

        data = dict(id=user_id)

        _ = requests.post(url=passport_broker_url, json=data)

        settings = EnvSettings()

        mailingClient = MailingClient()

        mailingClient.add_subject(
            "Welcome to the Lakehouse Database"
        ).add_html_body(
            f"""<h2>Hi {full_payload.name}!</h2> 
            <br> 
            <p>Your account has been successfully created in the OpenHealthLake platform</p>
            <p>To get started please see the 
            <a href="{settings.DOCUMENTATION_URL}">documentation</a> 
            or access the 
            <a href="{settings.FRONTEND_URL}">OpenHealthLake website.</a> </p>
            <br>
            <p>Our best regards,</p>
            <br>
            <p>The OpenHealthLake Team</p>
            """
        )
        
        try:
            mailingClient.send_email(
                full_payload.email
            )
        except Exception as _:
            HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User was created with success but mailing system failed to send a confirmation email to the user."
            )
        

        return CouchbaseUserModelNoPassword.from_full_model(full_payload)

    async def list_all(self) -> List[CouchbaseUserModelNoPassword]:
        response = await self.couchbaseRepo.get_documents(collection_name="info")

        if not response:
            return []

        return list(
            map(lambda x: CouchbaseUserModelNoPassword.from_dict(x["info"]), response)
        )

    async def list_by_email(self, email: str) -> CouchbaseUserModel:
        queryBuilder = CouchbaseQueryBuilder(
            scope=self.scope,
            collection="info",
        )

        queryStatement = queryBuilder.where(field="email", op="=", value=email).build()

        response = await self.couchbaseRepo.query(queryStatement)

        if not response:
            return {}

        response = map(lambda x: CouchbaseUserModel(**x["info"]), response)
        return list(response)[0]

    async def list_info_by_user_id(
        self, user_uuid: str
    ) -> CouchbaseUserModelNoPassword:
        response = await self.couchbaseRepo.get_document_by_id(
            collection_name="info", document_key=user_uuid
        )

        if not response:
            return {}

        response = map(
            lambda x: CouchbaseUserModelNoPassword.from_dict(x["info"]), response
        )

        return list(response)[0]

    async def list_passport_by_user_id(
        self, user_uuid: str
    ) -> CouchbaseUserAssertionModel:
        queryBuilder = CouchbaseQueryBuilder(
            scope=self.scope, collection="visa"
        )

        query = (
            queryBuilder.select().where("user_uuid", op="=", value=user_uuid).build()
        )

        response = await self.couchbaseRepo.query(statement=query)

        if not response:
            return {}

        response = map(lambda x: CouchbaseUserAssertionModel(**x["visa"]), response)

        return list(response)[0]

    async def list_users_by_visa_id(
        self, visa_uuid: str
    ) -> List[CouchbaseUserAssertionModel]:
        
        queryBuilder = CouchbaseQueryBuilder(
            scope=self.scope, collection="visa"
        )

        query = (
            queryBuilder.select()
            .where_any(
                target="assertion",
                in_filed="passportVisaAssertions",
                satisfies="assertion.passportVisa.id",
                op="=",
                value=visa_uuid,
            )
            .build()
        )

        response = await self.couchbaseRepo.query(statement=query)

        if not response:
            return {}

        response = list(
            map(lambda x: CouchbaseUserAssertionModel(**x["visa"]), response)
        )

        return response

    async def grant_visas_to_user(
        self, user_uuid: str, visa_uuids: list[str]
    ) -> CouchbaseUserAssertionModel:
        from services.VisasServices import VisaServices  # To avoid circular import

        user = await self.list_info_by_user_id(user_uuid)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Invalid or inexisting user id: f{user_uuid}"
            )

        passport_broker_url = f"{self.passport_broker_url}/admin/ga4gh/passport/v1/users/{user_uuid}"

        visaServices = VisaServices()

        visas = list([])

        invalid_visas = list([])

        for id in visa_uuids:
            response = await visaServices.get_by_id(visa_uuid=id)
            if response:
                visas.append(
                    VisaModel(
                        id=response.id,
                        visaName=response.visaName,
                        visaIssuer=response.visaIssuer,
                        visaDescription=response.visaDescription,
                        visaSecret=response.visaSecret,
                    )
                )
            else:
                invalid_visas.append(id)

        if invalid_visas:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid or inexisting visa ids: {invalid_visas}"
            )

        time = int(datetime.timestamp(datetime.now()))

        visa_assertions = [
            PassportVisaAssertion(status="Active", assertedAt=time, passportVisa=visa)
            for visa in visas
        ]

        response = await self.list_passport_by_user_id(user_uuid=user_uuid)

        if response:
            old_asserted_visas = response.passportVisaAssertions
            old_asserted_ids = [
                asserted_visa.passportVisa.id for asserted_visa in old_asserted_visas
            ]

            new_assertions = [
                assertion
                for assertion in visa_assertions
                if assertion.passportVisa.id not in old_asserted_ids
            ]
            visa_assertions = old_asserted_visas + new_assertions

        # creating on pass broker
        new_passport_payload = PassportUserAssertionModel(
            id=user_uuid, passportVisaAssertions=visa_assertions
        )

        requests.put(url=passport_broker_url, json=new_passport_payload.model_dump())

        # creating on couchbase

        new_couchbase_payload = {}

        if response:
            new_couchbase_payload = response
            new_couchbase_payload.passportVisaAssertions = visa_assertions

        else:  # if it is a new record
            record_id = str(uuid6.uuid7())
            new_couchbase_payload = CouchbaseUserAssertionModel(
                id=record_id,
                user_uuid=user_uuid,
                passportVisaAssertions=visa_assertions,
            )

        new_couchbase_payload = new_couchbase_payload

        await self.couchbaseRepo.upsert_document(
            collection_name="visa",
            key=new_couchbase_payload.id,
            value=new_couchbase_payload.model_dump(
                exclude_none=True, exclude_unset=True
            ),
        )

        return new_couchbase_payload

    async def revoke_visas_from_user(
        self, user_uuid: str, visa_uuids: list[str]
    ) -> CouchbaseUserAssertionModel:
        from services.VisasServices import VisaServices  # To avoid cisrcular import

        user = await self.list_info_by_user_id(user_uuid)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error due to invalid or inexisting user id: f{user_uuid}"
            )

        passport_broker_url = f"{self.passport_broker_url}/admin/ga4gh/passport/v1/users/{user_uuid}"

        visaServices = VisaServices()

        visas = list([])

        invalid_visas = list([])

        for id in visa_uuids:
            response = await visaServices.get_by_id(visa_uuid=id)
            if response:
                visas.append(response)
            else:
                invalid_visas.append(id)

        if invalid_visas:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error due to invalid or inexisting visa ids: {invalid_visas}"
            )

        response = await self.list_passport_by_user_id(user_uuid=user_uuid)

        if not response:
            return "The especified user has no asserted visas"

        updated_record = response

        updated_record.passportVisaAssertions = [
            visaAssertion
            for visaAssertion in updated_record.passportVisaAssertions
            if visaAssertion.passportVisa.id not in visa_uuids
        ]

        # creating on pass broker
        new_passport_payload = PassportUserAssertionModel(
            id=user_uuid, passportVisaAssertions=updated_record.passportVisaAssertions
        )

        response = requests.put(
            url=passport_broker_url, json=new_passport_payload.model_dump()
        )

        await self.couchbaseRepo.upsert_document(
            collection_name="visa",
            key=updated_record.id,
            value=updated_record.model_dump(),
        )

        return updated_record

    async def password_recovery_request(self, payload: PasswordRecoveryRequest) -> str:

        user = await self.list_by_email(payload.user_email)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User email {payload.user_email} not found!"
            )
        
        dumped_user = user.model_dump(exclude_none=True, exclude_defaults=True)

        time = int((datetime.now() + timedelta(minutes=30)).timestamp())
        
        recovery_token_payload = PasswordRecoveryModel(
            expires_at=time, 
            **dumped_user
        )

        encryptionhandler = EncryptionHandler()

        recovery_token = encryptionhandler.encrypt_credentials(
            recovery_token_payload.model_dump(exclude_none=True, exclude_unset=True)
        )

        mailingClient = MailingClient()

        mailingClient.add_subject(
            "Password Recovery Token"
        ).add_html_body(
            f"""<p>Dear {user.name},</p>
            <br>
            <p>To change your password please use the token below.</p>
            <br>
            <p> Token: 
            <br>
            <i>{recovery_token}</i></p>
            <br>
            <br>
            Kind regards,
            <br>
            The Lakehouse Team
            """
        )

        mailingClient.send_email(user.email)

        return payload.user_email

    async def password_change_request(self, payload: PasswordChangeRequest) -> str:
        from services.AuthServices import AuthServices

        encryptionhandler = EncryptionHandler()

        decoded_token = encryptionhandler.decrypt_credentials(payload.token)

        decoded_token = PasswordRecoveryModel(**decoded_token)

        date_now = int(datetime.now().timestamp())

        if date_now > decoded_token.expires_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Expired token"
            )

        authServices = AuthServices()

        new_decoded_password = authServices.word_to_hash(payload.new_password)

        user = await self.list_info_by_user_id(decoded_token.id)

        uploaded_user = user.model_copy(deep=True)
        uploaded_user.password = new_decoded_password

        _ = await self.couchbaseRepo.upsert_document(
            collection_name="info",
            key=user.id,
            value=uploaded_user.model_dump(exclude_unset=True, exclude_none=True)
        )

        mailingClient = MailingClient()

        mailingClient.add_subject(
            "Password change notice"
        ).add_html_body(
            f"""<p>Dear {user.name},</p>
            <br>
            <p>Your password has been successfully changed. If you did not make this change, please contact the admin team (Data Managers) immediately.</p>
            <br>
            <br>
            Kind regards,
            <br>
            The Lakehouse Team
            """
        )

        mailingClient.send_email(user.email)

        return user.email

    async def transfer_collections_ownership(
            self, 
            owner_id: str, 
            new_owner_id: str, 
            new_owner_email: str, 
            owner_passport: CouchbaseUserAssertionModel = None, 
            user_id: str = None
    ) -> List[CouchbaseCatalogCollectionModel]:
        from services.CatalogServices import CatalogServices

        catalogServices = CatalogServices()
        
        if user_id and user_id != owner_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ownership transfers can only be requested by collection owners!")

        filters = [
            CatalogFilter(property_name="inserted_by", operator="*", property_value=owner_id)
        ]

        collection_records = await catalogServices.get_by_filters(
            filters=filters,
            collection_name="collections"
        )

        if not collection_records.records:
            # raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"No collections with owner {owner_id} was found!")
            return list()
        
        updated_collections = list()
        
        if owner_passport:
            transferable_visa_names = [ 
                f"{record.id}:{record.collection_name}"
                for record in collection_records.records
            ]

            transferable_visa_ids = [ 
                assertion.passportVisa.id
                for assertion in owner_passport.passportVisaAssertions 
                if assertion.passportVisa.visaName in transferable_visa_names
            ]

            new_user_passport = await self.grant_visas_to_user(user_uuid=new_owner_id, visa_uuids=transferable_visa_ids)

            if not new_user_passport:
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to assign visas to new owner")

        for record in collection_records.records:
            new_owner = f"{new_owner_id}:{new_owner_email}"
            updated_record = await catalogServices.set_collection_owner(collection_record=record, new_owner=new_owner)
            updated_collections.append(updated_record)

        return updated_collections
    
    # TODO implement update users
    # async def update_user() -> dict:
