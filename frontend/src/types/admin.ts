/** 管理后台类型定义 */

export interface AdminUser {
  id: number
  email: string
  is_active: boolean
  email_verified: boolean
  role: string
  created_at: string
}

export interface AdminSubscription {
  id: number
  user_id: number
  user_email: string
  plan_name: string
  status: string
  trial_end: string | null
  current_period_end: string | null
  created_at: string
}

export interface SystemStats {
  users: { total: number; active: number }
  stores: { total: number }
  subscriptions: {
    by_status: Record<string, number>
    by_plan: Record<string, number>
  }
}

export interface AuditLogEntry {
  id: number
  user_id: number | null
  action: string
  target_type: string | null
  target_id: string | null
  detail: Record<string, unknown> | null
  ip_address: string | null
  created_at: string
}

export interface HealthStatus {
  status: string
  database: string
  redis: string
  timestamp: string
}
