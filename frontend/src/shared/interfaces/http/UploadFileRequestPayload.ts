import type { FileCategory, ProcessingLevel } from '@/shared/interfaces/types'
import type { Label } from './CreateCollectionPayload'

export interface UploadFileRequestPayload {
  collection_catalog_id: string
  file_name: string
  file_category?: FileCategory
  file_version: number
  file_size: number
  public?: boolean
  processing_level?: ProcessingLevel
  file_description?: string
  labels: Label[]
}
