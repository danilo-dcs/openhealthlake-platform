export interface CatalogCollectionRecord {
  collection_name: string
  storage_type: string
  inserted_by: string
  inserted_at: number
  status: string
  location: string
  collection_description: string
  public: false
  secret: false
  labels: string[]
  id: string
}

export interface CatalogCollectionResponse {
  records?: CatalogCollectionRecord[]
  next_page?: number
  total?: number
}
