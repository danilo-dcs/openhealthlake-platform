import json
import httpx
import logging

from shared.models.env import EnvSettings

class CouchbaseRepository:

    BUCKET_PORT = 8091
    QUERY_PORT = 8093

    def __init__(self, scope: str):

        settings = EnvSettings()

        self.host = settings.COUCHBASE_HOST
        self.user = settings.COUCHBASE_USER
        self.password = settings.COUCHBASE_PASSWORD
        self.bucket = settings.COUCHBASE_BUCKET

        self.scope = scope
        self.auth = tuple([self.user, self.password])
        self.base_url = f"http://{self.host}"

    async def __request_handler__(self, url: str, method: str, **kwargs) -> dict:
        logger = logging.getLogger(__name__)
        
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url, 
                auth=self.auth, 
                **kwargs
            )

        if response.is_error:
            logger.error("Couchbase request failed (%s): %s", response.status_code, response.text)

        response.raise_for_status()

        try:
            parsed_response = response.json()
        except ValueError:
            raise RuntimeError("Invalid JSON response from Couchbase")

        if parsed_response and parsed_response.get("status", None) != "success":
            error_msg = parsed_response.get("errors", {}).get("msg", "Unknown error")
            raise RuntimeError(f"Couchbase error: {error_msg}")
        
        return parsed_response


    async def create_collection(self, collection_name: str) -> dict:
        url = f"{self.base_url}:{CouchbaseRepository.BUCKET_PORT}/pools/default/buckets/{self.bucket}/scopes/{self.scope}/collections"

        data = {"name": collection_name, "maxTTL": "0", "history": "false"}

        response = await self.__request_handler__(url=url, method="POST", json=data)

        return response

    async def create_document(
        self, collection_name: str, key: str, value: dict
    ) -> dict:
        url = f"{self.base_url}:{CouchbaseRepository.QUERY_PORT}/query/service"

        query = f'INSERT INTO `{self.bucket}`.`{self.scope}`.`{collection_name}` (KEY, VALUE) VALUES ( "{key}",  {value} );'

        payload = {"statement": query}

        response = await self.__request_handler__(url=url, method="POST", json=payload)

        return response

      
    async def create_index(self, collection_name: str) -> dict:
        url = f"{self.base_url}:{CouchbaseRepository.QUERY_PORT}/query/service"

        query = f"CREATE PRIMARY INDEX ON `{self.bucket}`.`{self.scope}`.`{collection_name}`;"

        payload = {"statement": query}

        response = await self.__request_handler__(url=url, method="POST", json=payload)

        return response

    # deletion
    async def delete_collection(self, collection_name: str) -> dict:
        url = f"{self.base_url}:{CouchbaseRepository.BUCKET_PORT}/pools/default/buckets/{self.bucket}/scopes/{self.scope}/collections/{collection_name}"

        response = await self.__request_handler__(url=url, method="DELETE")

        return response

    async def delete_document(self, collection_name: str, document_key: str) -> dict:
        url = f"{self.base_url}:{CouchbaseRepository.BUCKET_PORT}/pools/default/buckets/{self.bucket}/scopes/{self.scope}/collections/{collection_name}/docs/{document_key}"

        response = await self.__request_handler__(url=url, method="DELETE")

        return response
    
    async def delete_document_2(self, collection_name: str, document_key: str) -> dict:
        url = f"{self.base_url}:{CouchbaseRepository.QUERY_PORT}/query/service"

        query = f"DELETE FROM `{self.bucket}`.`{self.scope}`.`{collection_name}` WHERE META().id = '{document_key}'"

        payload = {"statement": query}

        response = await self.__request_handler__(url=url, method="POST", json=payload)

        return response

    # get
    async def get_bucket(self) -> dict:
        url = f"{self.base_url}:{CouchbaseRepository.BUCKET_PORT}/pools/default/buckets/{self.bucket}"

        response = await self.__request_handler__(url=url, method="GET")

        return dict(response)

     
    async def get_document_by_id(
        self, collection_name: str, document_key: str
    ) -> list[dict]:
        url = f"{self.base_url}:{CouchbaseRepository.QUERY_PORT}/query/service"

        query = f"SELECT META().id, * FROM `{self.bucket}`.`{self.scope}`.`{collection_name}` USE KEYS {json.dumps([document_key])};"

        payload = {"statement": query}

        response = await self.__request_handler__(url=url, method="POST", json=payload)

        results = [dict(row) for row in response.get("results", [])]

        return results

    async def get_documents(self, collection_name: str):
        url = f"{self.base_url}:{CouchbaseRepository.QUERY_PORT}/query/service"

        query = f"SELECT META().id, * FROM `{self.bucket}`.`{self.scope}`.`{collection_name}`;"

        payload = {"statement": query}

        response = await self.__request_handler__(url=url, method="POST", json=payload)

        results = [dict(row) for row in response.get("results", [])]

        return results

    async def list_collections(self):
        url = f"{self.base_url}:{CouchbaseRepository.BUCKET_PORT}/pools/default/buckets/{self.bucket}/scopes"

        response = await self.__request_handler__(url=url, method="GET")

        scopes = [
            dict(name=scope["name"], collections=scope["collections"])
            for scope in response["scopes"]
            if scope["name"] == self.scope
        ]

        return scopes

    async def query(self, statement: str):
        url = f"{self.base_url}:{CouchbaseRepository.QUERY_PORT}/query/service"

        payload = {"statement": statement}

        response = await self.__request_handler__(url=url, method="POST", json=payload)

        results = [dict(row) for row in response.get("results", [])]

        return results
    

    async def upsert_document(
        self, collection_name: str, key: str, value: dict
    ) -> dict:
        url = f"{self.base_url}:{CouchbaseRepository.QUERY_PORT}/query/service"

        query = f'UPSERT INTO `{self.bucket}`.`{self.scope}`.`{collection_name}` (KEY, VALUE) VALUES ( "{key}",  {value} );'

        payload = {"statement": query}

        response = await self.__request_handler__(url=url, method="POST", json=payload)

        return response
