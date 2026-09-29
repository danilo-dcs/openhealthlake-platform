export type FileCategory = 'structured' | 'unstructured'
export type ProcessingLevel = 'raw' | 'processed' | 'curated'
export type Status = 'requested' | 'granted' | 'revoked'
export type StorageType = 'gcs' | 's3' | 'hdfs' | 'minio'
export const StorageOptions = ['gcs', 's3', 'hdfs', 'minio']

export type OperatorKey = 'equals' | 'not equals' | 'contains' | 'greater than' | 'lower than'

export type PropertyName =
  | 'collection_id'
  | 'collection_name'
  | 'is_public'
  | 'inserted_at'
  | 'inserted_by'
  | 'storage_type'
  | 'location'
  | 'collection_description'
  | 'status'


export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'

