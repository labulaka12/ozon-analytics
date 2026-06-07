/** 告警规则类型 */
export type RuleType = 'sales_drop' | 'stock' | 'price_change' | 'sync_fail'

/** 通知渠道 */
export type ChannelType = 'email' | 'wechat_work' | 'dingtalk' | 'feishu'

/** 告警规则 */
export interface AlertRule {
  id: number
  user_id: number
  store_id: number | null
  name: string
  rule_type: RuleType
  threshold: number
  channel: ChannelType
  target: string
  enabled: boolean
  last_triggered: string | null
  description: string
}

/** 创建告警规则请求 */
export interface AlertRuleCreate {
  store_id?: number | null
  name: string
  rule_type: RuleType
  threshold?: number
  channel?: ChannelType
  target?: string
  enabled?: boolean
  description?: string
}

/** 更新告警规则请求 */
export interface AlertRuleUpdate {
  store_id?: number | null
  name?: string
  rule_type?: RuleType
  threshold?: number
  channel?: ChannelType
  target?: string
  enabled?: boolean
  description?: string
}

/** 告警检查结果 */
export interface AlertCheckResult {
  triggered_count: number
  alerts: TriggeredAlert[]
}

/** 触发的告警 */
export interface TriggeredAlert {
  rule_name: string
  rule_type: string
  severity: 'info' | 'warning' | 'error'
  message: string
  triggered_at: string
  store_id?: number
  product_id?: number
  product_name?: string
  sync_type?: string
  threshold?: number
  current_value?: number
}

/** 规则类型显示映射 */
export const RULE_TYPE_LABELS: Record<RuleType, string> = {
  sales_drop: '销量下降',
  stock: '库存预警',
  price_change: '价格变动',
  sync_fail: '同步失败',
}

/** 通知渠道显示映射 */
export const CHANNEL_LABELS: Record<ChannelType, string> = {
  email: '邮件',
  wechat_work: '企业微信',
  dingtalk: '钉钉',
  feishu: '飞书',
}
