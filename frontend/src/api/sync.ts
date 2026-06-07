import request from './request'
import type { SyncLog } from '@/types/analytics'

export interface SyncRequest {
  store_id: number
  target_date?: string
  target_dates?: string[]
  product_ids?: number[]
}

export function triggerSync(syncType: string, data: SyncRequest) {
  return request.post<{ message: string }>(`/api/sync/${syncType}`, data).then(r => r.data)
}

export function fetchSyncLogs(storeId?: number, limit = 20) {
  return request.get<SyncLog[]>('/api/sync/logs', { params: { store_id: storeId, limit } }).then(r => r.data)
}
