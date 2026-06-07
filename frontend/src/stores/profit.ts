import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  fetchProfitSummary,
  fetchProfitTrend,
  fetchProfitProducts,
  fetchProfitFees,
  fetchProfitDetail,
  fetchProfitPredict,
  fetchBreakeven,
  fetchProfitV2Summary,
} from '@/api/profit'
import type { ProfitSummary, ProfitTrendItem, ProductProfitItem, FeeItem, ProfitDetailItem, ProfitPredictResponse, BreakevenResponse, StoreProfitV2 } from '@/types/profit'
import type { PaginatedResponse } from '@/types/api'

export interface ProfitFilters {
  date_from?: string
  date_to?: string
  group_by?: string
}

export const useProfitStore = defineStore('profit', () => {
  // ---- state ----
  const summary = ref<ProfitSummary | null>(null)
  const trend = ref<ProfitTrendItem[]>([])
  const products = ref<ProductProfitItem[]>([])
  const fees = ref<FeeItem[]>([])
  const feeTotal = ref(0)
  const detailItems = ref<ProfitDetailItem[]>([])
  const detailTotal = ref(0)
  const detailPage = ref(1)
  const detailSortBy = ref<string>('profit')
  const detailSortOrder = ref<string>('desc')
  const prediction = ref<ProfitPredictResponse | null>(null)
  const breakeven = ref<BreakevenResponse | null>(null)
  const v2Summary = ref<StoreProfitV2 | null>(null)
  const filters = ref<ProfitFilters>({})
  const loading = ref(false)
  const error = ref<string | null>(null)

  // ---- actions ----
  async function loadSummary(storeId: number, extraFilters?: ProfitFilters) {
    loading.value = true
    error.value = null
    try {
      if (extraFilters) filters.value = { ...filters.value, ...extraFilters }
      const params = { store_id: storeId, ...filters.value }
      summary.value = await fetchProfitSummary(params)
    } catch (e: any) {
      const msg = e?.response?.data?.detail || e?.message || '加载利润汇总失败'
      error.value = msg
    } finally {
      loading.value = false
    }
  }

  async function loadTrend(storeId: number, extraFilters?: ProfitFilters) {
    loading.value = true
    error.value = null
    try {
      if (extraFilters) filters.value = { ...filters.value, ...extraFilters }
      const params = { store_id: storeId, ...filters.value }
      const res = await fetchProfitTrend(params)
      trend.value = res.items ?? []
    } catch (e: any) {
      const msg = e?.response?.data?.detail || e?.message || '加载利润趋势失败'
      error.value = msg
    } finally {
      loading.value = false
    }
  }

  async function loadProducts(storeId: number, limit = 10) {
    loading.value = true
    error.value = null
    try {
      const params = { store_id: storeId, ...filters.value, limit }
      const res = await fetchProfitProducts(params)
      products.value = res.items ?? []
    } catch (e: any) {
      const msg = e?.response?.data?.detail || e?.message || '加载产品利润失败'
      error.value = msg
    } finally {
      loading.value = false
    }
  }

  async function loadFees(storeId: number) {
    loading.value = true
    error.value = null
    try {
      const params = { store_id: storeId, ...filters.value }
      const res = await fetchProfitFees(params)
      fees.value = res.items ?? []
      feeTotal.value = res.total ?? 0
    } catch (e: any) {
      const msg = e?.response?.data?.detail || e?.message || '加载费用明细失败'
      error.value = msg
    } finally {
      loading.value = false
    }
  }

  async function loadDetail(storeId: number, pageNum = 1) {
    loading.value = true
    error.value = null
    try {
      detailPage.value = pageNum
      const params = {
        store_id: storeId,
        ...filters.value,
        page: detailPage.value,
        page_size: 20,
        sort_by: detailSortBy.value,
        sort_order: detailSortOrder.value,
      }
      const res: PaginatedResponse<ProfitDetailItem> = await fetchProfitDetail(params)
      detailItems.value = res.items ?? []
      detailTotal.value = res.total ?? 0
      detailPage.value = res.page ?? detailPage.value
    } catch (e: any) {
      const msg = e?.response?.data?.detail || e?.message || '加载利润明细失败'
      error.value = msg
    } finally {
      loading.value = false
    }
  }

  async function loadPrediction(storeId: number, daysAhead = 30) {
    loading.value = true
    error.value = null
    try {
      prediction.value = await fetchProfitPredict(storeId, daysAhead)
    } catch (e: any) {
      const msg = e?.response?.data?.detail || e?.message || '加载利润预测失败'
      error.value = msg
    } finally {
      loading.value = false
    }
  }

  async function loadBreakeven(storeId: number) {
    loading.value = true
    error.value = null
    try {
      breakeven.value = await fetchBreakeven(storeId)
    } catch (e: any) {
      const msg = e?.response?.data?.detail || e?.message || '加载盈亏平衡分析失败'
      error.value = msg
    } finally {
      loading.value = false
    }
  }

  /** 一键加载利润看板所有数据 */
  async function loadAll(storeId: number) {
    loading.value = true
    error.value = null
    try {
      const params = { store_id: storeId, ...filters.value }
      const [summaryRes, trendRes, productsRes, feesRes, predictionRes, breakevenRes, v2Res] = await Promise.all([
        fetchProfitSummary(params),
        fetchProfitTrend(params),
        fetchProfitProducts(params),
        fetchProfitFees(params),
        fetchProfitPredict(storeId),
        fetchBreakeven(storeId),
        fetchProfitV2Summary(params).catch(() => null),
      ])
      summary.value = summaryRes
      trend.value = trendRes.items ?? []
      products.value = productsRes.items ?? []
      fees.value = feesRes.items ?? []
      feeTotal.value = feesRes.total ?? 0
      prediction.value = predictionRes
      breakeven.value = breakevenRes
      v2Summary.value = v2Res
    } catch (e: any) {
      const msg = e?.response?.data?.detail || e?.message || '加载利润数据失败'
      error.value = msg
    } finally {
      loading.value = false
    }
  }

  function setSort(sortBy: string, sortOrder: string) {
    detailSortBy.value = sortBy
    detailSortOrder.value = sortOrder
  }

  function setFilters(newFilters: ProfitFilters) {
    filters.value = { ...filters.value, ...newFilters }
  }

  function clearFilters() {
    filters.value = {}
  }

  function clearError() {
    error.value = null
  }

  function clearAll() {
    summary.value = null
    trend.value = []
    products.value = []
    fees.value = []
    feeTotal.value = 0
    detailItems.value = []
    detailTotal.value = 0
    detailPage.value = 1
    prediction.value = null
    breakeven.value = null
    v2Summary.value = null
    filters.value = {}
    loading.value = false
    error.value = null
  }

  return {
    summary,
    trend,
    products,
    fees,
    feeTotal,
    detailItems,
    detailTotal,
    detailPage,
    detailSortBy,
    detailSortOrder,
    prediction,
    breakeven,
    v2Summary,
    filters,
    loading,
    error,
    loadSummary,
    loadTrend,
    loadProducts,
    loadFees,
    loadDetail,
    loadPrediction,
    loadBreakeven,
    loadAll,
    setSort,
    setFilters,
    clearFilters,
    clearAll,
    clearError,
  }
})
