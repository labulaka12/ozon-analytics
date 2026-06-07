import request from './request'
import type {
  ProfitSummary, ProfitTrendResponse, ProductProfitItem,
  FeeResponse, ProfitDetailItem, ProfitPredictResponse, BreakevenResponse,
} from '@/types/profit'
import type { PaginatedResponse } from '@/types/api'

export interface ProfitParams {
  store_id: number
  date_from?: string
  date_to?: string
}

export function fetchProfitSummary(params: ProfitParams) {
  return request.get<ProfitSummary>('/api/profit/summary', { params }).then(r => r.data)
}

export function fetchProfitTrend(params: ProfitParams & { group_by?: string }) {
  return request.get<ProfitTrendResponse>('/api/profit/trend', { params }).then(r => r.data)
}

export function fetchProfitProducts(params: ProfitParams & { limit?: number }) {
  return request.get<{ items: ProductProfitItem[] }>('/api/profit/products', { params }).then(r => r.data)
}

export function fetchProfitFees(params: ProfitParams) {
  return request.get<FeeResponse>('/api/profit/fees', { params }).then(r => r.data)
}

export function fetchProfitDetail(params: ProfitParams & { page?: number; page_size?: number; sort_by?: string; sort_order?: string }) {
  return request.get<PaginatedResponse<ProfitDetailItem>>('/api/profit/detail', { params }).then(r => r.data)
}

export function fetchProfitPredict(storeId: number, daysAhead = 30) {
  return request.get<ProfitPredictResponse>('/api/profit/v2/predict', { params: { store_id: storeId, days_ahead: daysAhead } }).then(r => r.data)
}

export function fetchBreakeven(storeId: number) {
  return request.get<BreakevenResponse>('/api/profit/v2/breakeven', { params: { store_id: storeId } }).then(r => r.data)
}

/** V2 店铺利润汇总（完整费用分解） */
export function fetchProfitV2Summary(params: ProfitParams) {
  return request.get<import('@/types/profit').StoreProfitV2>('/api/profit/v2/summary', { params }).then(r => r.data)
}

/** V2 商品利润排行榜（支持 ROI 排序） */
export function fetchProfitV2Products(
  params: ProfitParams & { limit?: number; sort_by?: string; sort_order?: string },
) {
  return request.get<{ items: import('@/types/profit').ProductProfitV2[]; total: number }>(
    '/api/profit/v2/products',
    { params },
  ).then(r => r.data)
}

/** V2 单商品利润分解 */
export function fetchProfitV2Product(
  productId: number,
  params: ProfitParams,
) {
  return request.get<import('@/types/profit').ProductProfitV2>(
    `/api/profit/v2/product/${productId}`,
    { params },
  ).then(r => r.data)
}
