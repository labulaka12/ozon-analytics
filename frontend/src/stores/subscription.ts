/** 订阅状态 Store */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { fetchPlans, fetchCurrentSubscription } from '@/api/subscription'
import type { Plan, Subscription, UsageStats, CurrentSubscriptionResponse } from '@/types/subscription'

export const useSubscriptionStore = defineStore('subscription', () => {
  // ---- state ----
  const plans = ref<Plan[]>([])
  const subscription = ref<Subscription | null>(null)
  const usage = ref<UsageStats | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // ---- getters ----
  const currentPlan = computed(() => {
    if (!subscription.value) return null
    return plans.value.find(p => p.name === subscription.value!.plan_name) || null
  })

  const isActive = computed(() => {
    if (!subscription.value) return false
    return ['trialing', 'active'].includes(subscription.value.status)
  })

  const isFreePlan = computed(() => {
    return subscription.value?.plan_name === 'free' || !subscription.value
  })

  const planDisplayName = computed(() => {
    return subscription.value?.plan_display_name || 'Free'
  })

  // ---- actions ----
  async function loadPlans() {
    try {
      plans.value = await fetchPlans()
    } catch (e: any) {
      const msg = e?.response?.data?.detail || e?.message || '获取套餐列表失败'
      error.value = msg
    }
  }

  async function loadCurrentSubscription() {
    loading.value = true
    error.value = null
    try {
      const data: CurrentSubscriptionResponse = await fetchCurrentSubscription()
      subscription.value = data.subscription
      usage.value = data.usage
    } catch (e: any) {
      const msg = e?.response?.data?.detail || e?.message || '获取订阅信息失败'
      error.value = msg
    } finally {
      loading.value = false
    }
  }

  async function loadAll() {
    loading.value = true
    error.value = null
    try {
      await Promise.all([loadPlans(), loadCurrentSubscription()])
    } finally {
      loading.value = false
    }
  }

  function clearError() { error.value = null }
  function clearAll() {
    plans.value = []
    subscription.value = null
    usage.value = null
    loading.value = false
    error.value = null
  }

  return {
    plans, subscription, usage, loading, error,
    currentPlan, isActive, isFreePlan, planDisplayName,
    loadPlans, loadCurrentSubscription, loadAll,
    clearError, clearAll,
  }
})
