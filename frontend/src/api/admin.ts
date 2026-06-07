/** 管理后台 API */
import request from './request'
import type { AdminUser, AdminSubscription, SystemStats, AuditLogEntry, HealthStatus } from '@/types/admin'

/** 获取用户列表 */
export function fetchUsers(page = 1, pageSize = 20, search?: string) {
  return request.get<{ items: AdminUser[]; total: number; page: number; page_size: number; total_pages: number }>(
    '/api/admin/users',
    { params: { page, page_size: pageSize, search } },
  ).then(r => r.data)
}

/** 切换用户状态 */
export function toggleUserStatus(userId: number) {
  return request.put<{ message: string; is_active: boolean }>(`/api/admin/users/${userId}/status`).then(r => r.data)
}

/** 修改用户角色 */
export function changeUserRole(userId: number, role: string) {
  return request.put<{ message: string }>(`/api/admin/users/${userId}/role`, { role }).then(r => r.data)
}

/** 获取订阅列表 */
export function fetchSubscriptions(page = 1, pageSize = 20, status?: string) {
  return request.get<{ items: AdminSubscription[]; total: number; page: number; page_size: number }>(
    '/api/admin/subscriptions',
    { params: { page, page_size: pageSize, status } },
  ).then(r => r.data)
}

/** 获取系统统计 */
export function fetchSystemStats() {
  return request.get<SystemStats>('/api/admin/stats').then(r => r.data)
}

/** 获取审计日志 */
export function fetchAuditLogs(page = 1, pageSize = 50, userId?: number, action?: string) {
  return request.get<{ items: AuditLogEntry[] }>(
    '/api/admin/audit-logs',
    { params: { page, page_size: pageSize, user_id: userId, action } },
  ).then(r => r.data)
}

/** 系统健康检查 */
export function fetchHealth() {
  return request.get<HealthStatus>('/api/admin/health').then(r => r.data)
}
