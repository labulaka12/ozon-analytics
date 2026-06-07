/** 告警通知 API */
import request from './request'
import type { AlertRule, AlertRuleCreate, AlertRuleUpdate, AlertCheckResult } from '@/types/alert'

/** 获取告警规则列表 */
export function fetchAlertRules(storeId?: number) {
  return request.get<{ rules: AlertRule[] }>('/api/alerts/rules', {
    params: storeId ? { store_id: storeId } : {},
  }).then(r => r.data)
}

/** 创建告警规则 */
export function createAlertRule(data: AlertRuleCreate) {
  return request.post<{ message: string; rule: AlertRule }>('/api/alerts/rules', data).then(r => r.data)
}

/** 更新告警规则 */
export function updateAlertRule(ruleId: number, data: AlertRuleUpdate) {
  return request.put<{ message: string; rule: AlertRule }>(`/api/alerts/rules/${ruleId}`, data).then(r => r.data)
}

/** 删除告警规则 */
export function deleteAlertRule(ruleId: number) {
  return request.delete<{ message: string }>(`/api/alerts/rules/${ruleId}`).then(r => r.data)
}

/** 切换规则启用/禁用 */
export function toggleAlertRule(ruleId: number) {
  return request.post<{ message: string; rule: AlertRule }>(`/api/alerts/rules/${ruleId}/toggle`).then(r => r.data)
}

/** 手动触发告警检查 */
export function checkAlerts(storeId?: number) {
  return request.get<AlertCheckResult>('/api/alerts/check', {
    params: storeId ? { store_id: storeId } : {},
  }).then(r => r.data)
}

/** 发送测试告警 */
export function sendTestAlert(channel: string, target: string) {
  return request.get<{ message: string }>('/api/alerts/send-test', {
    params: { channel, target },
  }).then(r => r.data)
}
