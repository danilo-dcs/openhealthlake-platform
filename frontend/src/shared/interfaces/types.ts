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

export const defaultColors: Record<string, string> = {
  red: '#EF4444',
  orange: '#F97316',
  amber: '#F59E0B',
  green: '#22C55E',
  teal: '#14B8A6',
  blue: '#3B82F6',
  indigo: '#6366F1',
  violet: '#8B5CF6',
  pink: '#EC4899',
  slate: '#64748B',
};

export const defaultLabels = ["cleaning", "cleanned", "harmonising", "hamonised", "static", "shared"]
