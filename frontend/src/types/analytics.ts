export interface AnalyticsRow {
  product_id: number
  offer_id: string
  sku: number | null
  date: string
  impressions_search: number
  views_pdp: number
  views_total: number
  sessions: number
  add_to_cart: number
  conversion_to_cart: number
  ctr: number
  order_conversion: number
  ordered_units: number
  revenue: number
  returns_count: number
  cancellations: number
  position_avg: number | null
}

export interface AnalyticsSummary {
  total_impressions: number
  total_views_pdp: number
  total_views: number
  total_sessions: number
  total_add_to_cart: number
  total_ordered: number
  total_revenue: number
  total_returns: number
  total_cancellations: number
  days_with_data: number
  date_from: string
  date_to: string
}

export interface AnalyticsResponse {
  items: AnalyticsRow[]
  dates: string[]
  products: { product_id: number; offer_id: string; name: string }[]
}

export interface SyncLog {
  id: number
  store_id: number
  sync_type: string | null
  status: string | null
  message: string | null
  created_at: string | null
}
