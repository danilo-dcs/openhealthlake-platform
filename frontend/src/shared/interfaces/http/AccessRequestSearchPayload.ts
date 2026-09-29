import type { Status } from "@/shared/interfaces/types"

export interface AccessRequestSearchPayload {
  collection_id?: string
  requested_by?: string
  owner_id?: string
  owner_email?: string
  requestor_email?: string
  status?: Status
}
