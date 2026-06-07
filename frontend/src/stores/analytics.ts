import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchAnalytics, fetchAnalyticsSummary } from '@/api/analytics'
import type { AnalyticsRow, AnalyticsSummary, AnalyticsResponse } from '@/types/analytics'

export interface AnalyticsFilters {
  product_ids?: string
  date_from?: string
  date_to?: string
}

export const useAnalyticsStore = defineStore('analytics', () => {
  // ---- state ----
  const items = ref<AnalyticsRow[]>([])
  const dates = ref<string[]>([])
  const products = ref<{ product_id: number; offer_id: string; name: string }[]>([])
  const summary = ref<AnalyticsSummary | null>(null)
  const filters = ref<AnalyticsFilters>({})
  const loading = ref(false)
  const error = ref<string | null>(null)

  // ---- actions ----
  async function loadData(storeId: number, extraFilters?: AnalyticsFilters) {
    loading.value = true
    error.value = null
    try {
      if (extraFilters) filters.value = { ...filters.value, ...extraFilters }
      const params = { store_id: storeId, ...filters.value }
      const [analyticsRes, summaryRes] = await Promise.all([
        fetchAnalytics(params),
        fetchAnalyticsSummary(params),
      ])
      applyAnalyticsResponse(analyticsRes)
      summary.value = summaryRes
    } catch (e: any) {
      const msg = e?.response?.data?.detail || e?.message || '加载分析数据失败'
      error.value = msg
    } finally {
      loading.value = false
    }
  }

  function setFilters(newFilters: AnalyticsFilters) {
    filters.value = { ...filters.value, ...newFilters }
  }

  function clearFilters() {
    filters.value = {}
  }

  function applyAnalyticsResponse(res: AnalyticsResponse) {
    items.value = res.items
    dates.value = res.dates
    products.value = res.products
  }

  function clearError() {
    error.value = null
  }

  function clearAll() {
    items.value = []
    dates.value = []
    products.value = []
    summary.value = null
    filters.value = {}
    loading.value = false
    error.value = null
  }

  return {
    items,
    dates,
    products,
    summary,
    filters,
    loading,
    error,
    loadData,
    setFilters,
    clearFilters,
    clearAll,
    clearError,
  }
})
