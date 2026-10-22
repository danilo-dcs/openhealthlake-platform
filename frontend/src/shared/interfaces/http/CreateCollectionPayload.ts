export interface Label {
  value: string,
  color: string
}

export interface CreateCollectionPayload {
  user_id?: string
  credential_id?: string
  storage_type?: string
  collection_name?: string
  bucket_name?: string
  collection_description?: string
  public?: boolean
  secret?: boolean
  labels?: Label[]
}
