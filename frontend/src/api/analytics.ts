import request from './request'
import type { AnalyticsResponse, AnalyticsSummary } from '@/types/analytics'

export interface AnalyticsParams {
  store_id: number
  product_ids?: string
  date_from?: string
  date_to?: string
}

export function fetchAnalytics(params: AnalyticsParams) {
  return request.get<AnalyticsResponse>('/api/analytics', { params }).then(r => r.data)
}

export function fetchAnalyticsSummary(params: AnalyticsParams) {
  return request.get<AnalyticsSummary>('/api/analytics/summary', { params }).then(r => r.data)
}
