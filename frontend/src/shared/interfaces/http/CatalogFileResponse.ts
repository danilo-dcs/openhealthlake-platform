export interface CatalogFileRecord {
  file_name: string
  file_size: number
  collection_name: string
  processing_level: string
  storage_type: string
  file_bucket: string
  inserted_by: string
  inserted_at: number
  file_description: string
  file_category: string
  file_status: string
  expires_at: number
  file_version: number
  public: false
  labels: string[]
  id: string
}

export interface CatalogFileResponse {
  records?: CatalogFileRecord[]
  next_page?: number
  total?: number
}
