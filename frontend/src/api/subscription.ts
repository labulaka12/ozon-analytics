/** 订阅/计费 API */
import request from './request'
import type { Plan, CurrentSubscriptionResponse, PaymentRecord } from '@/types/subscription'

/** 获取所有可用套餐 */
export function fetchPlans() {
  return request.get<Plan[]>('/api/subscription/plans').then(r => r.data)
}

/** 获取当前订阅 + 用量统计 */
export function fetchCurrentSubscription() {
  return request.get<CurrentSubscriptionResponse>('/api/subscription/current').then(r => r.data)
}

/** 创建 Stripe Checkout 会话 */
export function createCheckout(planName: string) {
  return request.post<{ checkout_url: string }>('/api/subscription/checkout', { plan_name: planName }).then(r => r.data)
}

/** 创建 Stripe Customer Portal 会话 */
export function createPortal() {
  return request.post<{ portal_url: string }>('/api/subscription/portal').then(r => r.data)
}

/** 获取支付历史 */
export function fetchPaymentHistory(limit = 20) {
  return request.get<PaymentRecord[]>('/api/subscription/payments', { params: { limit } }).then(r => r.data)
}

/** 取消订阅 */
export function cancelSubscription() {
  return request.post<{ message: string; status: string }>('/api/subscription/cancel').then(r => r.data)
}
