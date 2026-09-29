import type { Status } from "@/shared/interfaces/types"

export interface AccessRequestModel {
  collection_id: string
  requested_at: number
  requested_by: string
  owner_id: string
  owner_email: string
  requestor_email: string
  status: Status
  id: string
}

export interface AccessRequestSearchResponse {
  access_requests: AccessRequestModel[]
}
