import type { StorageType } from "../types"


export interface CredentialItem {
  visa_uuids: string[]
  storage_type: StorageType
  bucket_names: []
  credential: string
  id: string
}

export type CredentialsAllResponse = CredentialItem[]
