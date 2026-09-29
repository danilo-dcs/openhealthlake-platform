import type { OperatorKey, PropertyName } from "@/shared/interfaces/types"

export interface CollectionFilter {
  property_name: PropertyName
  property_value: any
  operator: OperatorKey
}

export interface CollectionSearchRequest {
  filters?: CollectionFilter[]
  page_number?: number
}
