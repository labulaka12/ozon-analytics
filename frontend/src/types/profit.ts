export interface ProfitSummary {
  total_revenue: number
  total_cost: number
  total_fees: number
  total_profit: number
  profit_margin: number
}

export interface ProfitTrendItem {
  date: string
  revenue: number
  fees: number
  cost: number
  profit: number
  margin: number
}

export interface ProfitTrendResponse {
  items: ProfitTrendItem[]
  group_by: string
}

export interface ProductProfitItem {
  product_id: number
  offer_id: string
  product_name: string
  sold_units: number
  revenue: number
  profit: number
  margin: number
}

export interface FeeItem {
  name: string
  amount: number
  pct: number
}

export interface FeeResponse {
  items: FeeItem[]
  total: number
}

export interface ProfitDetailItem {
  product_id: number
  offer_id: string
  product_name: string
  sold_units: number
  revenue: number
  cost: number
  fees: number
  profit: number
  margin: number
}

export interface ProfitPredictResponse {
  avg_daily_profit: number
  trend_direction: string
  trend_amount: number
  predicted_daily_profit: number
  predicted_total: number
  days_ahead: number
  data_points: number
  confidence: string
}

export interface BreakevenResponse {
  breakeven_units: number
  is_profitable: boolean
  fixed_cost_rub: number
  avg_price: number
  avg_variable_fee: number
  unit_contribution: number
  current_sold_units: number
  message: string
}

/* ========== V2 利润引擎类型 ========== */

/** V2 费用分解 */
export interface ProfitBreakdown {
  revenue: number
  returns_loss: number
  net_revenue: number
  commission: number
  logistics: number
  advertising: number
  penalty: number
  other_platform_fees: number
  total_platform_fees: number
  purchase_cost_cny: number
  freight_cost_cny: number
  customs_cost_cny: number
  other_manual_cost_cny: number
  total_manual_cost_rub: number
  total_cost: number
  net_profit: number
  net_profit_cny: number
  profit_margin: number
  roi: number
  exchange_rate: number
}

/** V2 单商品利润 */
export interface ProductProfitV2 {
  product_id: number
  offer_id: string
  product_name: string
  sold_units: number
  unit_profit: number
  revenue: number
  returns_loss: number
  net_revenue: number
  commission: number
  logistics: number
  advertising: number
  penalty: number
  other_platform_fees: number
  total_platform_fees: number
  purchase_cost_cny: number
  freight_cost_cny: number
  customs_cost_cny: number
  other_manual_cost_cny: number
  total_manual_cost_rub: number
  total_cost: number
  net_profit: number
  net_profit_cny: number
  profit_margin: number
  roi: number
  exchange_rate: number
}

/** V2 店铺利润汇总 */
export interface StoreProfitV2 {
  store_id: number
  store_name: string
  total_products: number
  total_sold_units: number
  revenue: number
  returns_loss: number
  net_revenue: number
  commission: number
  logistics: number
  advertising: number
  penalty: number
  other_platform_fees: number
  total_platform_fees: number
  purchase_cost_cny: number
  freight_cost_cny: number
  customs_cost_cny: number
  other_manual_cost_cny: number
  total_manual_cost_rub: number
  total_cost: number
  net_profit: number
  net_profit_cny: number
  profit_margin: number
  roi: number
  exchange_rate: number
  top_products: ProductProfitV2[]
  worst_products: ProductProfitV2[]
}
