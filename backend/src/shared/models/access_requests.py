from typing import List, Literal, Optional
from pydantic import BaseModel

Status = Literal["requested", "granted", "revoked"]

class AccessRequestModel(BaseModel):
    collection_id: str
    requested_by: str
    owner_id: str

class InviteCollaboratorPayload(BaseModel):
    collection_id: str
    email: str


class CouchbaseAccessRequestModel(AccessRequestModel):
    requested_at: Optional[int] = None
    owner_email: Optional[str] = None
    requestor_email: Optional[str] = None
    status: Optional[Status] = None
    id: str
    
class AccessRequestSearchResponse(BaseModel):
    access_requests: List[CouchbaseAccessRequestModel]

class AccessRequestSearchPayload(BaseModel):
    collection_id: Optional[str] = None
    requested_by: Optional[str] = None
    owner_id: Optional[str] = None
    owner_email: Optional[str] = None
    requestor_email: Optional[str] = None
    status: Optional[Status] = None

class GrantAccessRequestPayload(BaseModel):
    access_request_id: str

class RevokeAccessRequestPayload(BaseModel):
    access_request_id: str
