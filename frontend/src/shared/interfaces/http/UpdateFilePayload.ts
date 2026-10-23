import type { FileCategory } from '@/shared/interfaces/types'
import type { Label } from '@/shared/interfaces/http/CreateCollectionPayload'

export interface UpdateFilePayload {
  file_category: FileCategory
  file_description: string
  labels: Label[]
}
