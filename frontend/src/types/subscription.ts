/** 订阅/计费相关类型定义 */

export interface Plan {
  id: number
  name: string
  display_name: string
  price_cents: number
  currency: string
  limits: PlanLimits
  stripe_price_id?: string
}

export interface PlanLimits {
  max_stores: number
  max_products_per_store: number
  sync_frequency: 'daily' | 'every_8_hours' | 'hourly'
  data_retention_days: number
  max_alert_rules: number
  max_team_members: number
  profit_analysis: boolean
  profit_prediction: boolean
  api_access: 'none' | 'readonly' | 'full'
  csv_export: boolean
}

export interface Subscription {
  id: number
  plan_id: number
  plan_name: string
  plan_display_name: string
  status: 'trialing' | 'active' | 'past_due' | 'cancelled' | 'expired'
  trial_end: string | null
  current_period_end: string | null
  cancelled_at: string | null
}

export interface UsageStats {
  stores: { current: number; limit: number }
  alert_rules: { current: number; limit: number }
  products: { current: number; limit: number }
  features: {
    profit_analysis: boolean
    profit_prediction: boolean
    csv_export: boolean
    api_access: string
    sync_frequency: string
    data_retention_days: number
  }
}

export interface CurrentSubscriptionResponse {
  subscription: Subscription | null
  usage: UsageStats
}

export interface PaymentRecord {
  id: number
  amount_cents: number
  currency: string
  status: string
  description: string | null
  paid_at: string | null
  created_at: string | null
}
