import request from './request'
import type { Store, StoreCreate, StoreUpdate } from '@/types/store'

export function fetchStores() {
  return request.get<Store[]>('/api/stores').then(r => r.data)
}

export function createStore(data: StoreCreate) {
  return request.post<{ id: number; message: string }>('/api/stores', data).then(r => r.data)
}

export function updateStore(id: number, data: StoreUpdate) {
  return request.put<{ message: string }>(`/api/stores/${id}`, data).then(r => r.data)
}

export function deleteStore(id: number) {
  return request.delete<{ message: string }>(`/api/stores/${id}`).then(r => r.data)
}
