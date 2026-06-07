export interface Store {
  id: number
  name: string
  client_id: string
  is_active: boolean
  last_sync_at: string | null
  created_at: string
  product_count?: number
}

export interface StoreCreate {
  name: string
  client_id: string
  api_key: string
}

export interface StoreUpdate {
  name?: string
  client_id?: string
  api_key?: string
}
