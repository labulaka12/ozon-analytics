import request from './request'
import type { OrderItem, OrderDetail } from '@/types/order'
import type { PaginatedResponse } from '@/types/api'

export interface OrderParams {
  store_id: number
  status?: string
  product_id?: number
  date_from?: string
  date_to?: string
  page?: number
  page_size?: number
}

export function fetchOrders(params: OrderParams) {
  return request.get<PaginatedResponse<OrderItem>>('/api/orders', { params }).then(r => r.data)
}

export function fetchOrderDetail(storeId: number, postingNumber: string) {
  return request.get<OrderDetail>(`/api/orders/${postingNumber}`, { params: { store_id: storeId } }).then(r => r.data)
}
