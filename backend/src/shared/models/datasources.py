
from typing import Optional

from pydantic import BaseModel

class CouchbaseConfigs(BaseModel):
    host: str
    user: str
    password: str
    bucket: Optional[str] = None

class DatasourceConfigs(BaseModel):
    couchbase: CouchbaseConfigs
