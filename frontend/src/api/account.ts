/** 账户设置 API */
import request from './request'
import type { UserProfile, UpdateProfileRequest, UpdateEmailRequest } from '@/types/account'

/** 更新个人资料 */
export function updateProfile(data: UpdateProfileRequest) {
  return request.put<{ message: string }>('/api/account/profile', data).then(r => r.data)
}

/** 修改邮箱 */
export function updateEmail(data: UpdateEmailRequest) {
  return request.put<{ message: string }>('/api/account/email', data).then(r => r.data)
}

/** 修改密码 */
export function changePassword(oldPassword: string, newPassword: string) {
  return request.post<{ message: string }>('/api/auth/change-password', {
    old_password: oldPassword,
    new_password: newPassword,
  }).then(r => r.data)
}

/** 请求密码重置 */
export function forgotPassword(email: string) {
  return request.post<{ message: string }>('/api/auth/forgot-password', { email }).then(r => r.data)
}

/** 重置密码 */
export function resetPassword(token: string, newPassword: string) {
  return request.post<{ message: string }>('/api/auth/reset-password', {
    token,
    new_password: newPassword,
  }).then(r => r.data)
}

/** 验证邮箱 */
export function verifyEmail(token: string) {
  return request.post<{ message: string }>('/api/auth/verify-email', { token }).then(r => r.data)
}

/** 重新发送验证邮件 */
export function resendVerification() {
  return request.post<{ message: string }>('/api/auth/resend-verification').then(r => r.data)
}

/** 导出用户数据 */
export function exportUserData() {
  return request.get('/api/account/export', { responseType: 'blob' }).then(r => r.data)
}

/** 删除账户 */
export function deleteAccount(password: string) {
  return request.delete<{ message: string }>('/api/account', {
    data: { password, confirm: 'DELETE' },
  }).then(r => r.data)
}
