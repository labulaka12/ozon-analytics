import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchOrders, fetchOrderDetail } from '@/api/orders'
import type { OrderItem, OrderDetail } from '@/types/order'
import type { PaginatedResponse } from '@/types/api'

export interface OrderFilters {
  status?: string
  product_id?: number
  date_from?: string
  date_to?: string
  page?: number
  page_size?: number
}

export const useOrderStore = defineStore('orders', () => {
  // ---- state ----
  const orders = ref<OrderItem[]>([])
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(20)
  const filters = ref<OrderFilters>({})
  const currentDetail = ref<OrderDetail | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // ---- actions ----
  async function loadOrders(storeId: number, extraFilters?: OrderFilters) {
    loading.value = true
    error.value = null
    try {
      if (extraFilters) {
        if (extraFilters.page !== undefined) page.value = extraFilters.page
        if (extraFilters.page_size !== undefined) pageSize.value = extraFilters.page_size
        const { page: _p, page_size: _ps, ...rest } = extraFilters
        filters.value = { ...filters.value, ...rest }
      }
      const params = {
        store_id: storeId,
        page: page.value,
        page_size: pageSize.value,
        ...filters.value,
      }
      const res: PaginatedResponse<OrderItem> = await fetchOrders(params)
      orders.value = res.items ?? []
      total.value = res.total ?? 0
      page.value = res.page ?? page.value
    } catch (e: any) {
      const msg = e?.response?.data?.detail || e?.message || '加载订单列表失败'
      error.value = msg
    } finally {
      loading.value = false
    }
  }

  async function loadDetail(storeId: number, postingNumber: string) {
    loading.value = true
    error.value = null
    try {
      currentDetail.value = await fetchOrderDetail(storeId, postingNumber)
    } catch (e: any) {
      const msg = e?.response?.data?.detail || e?.message || '加载订单详情失败'
      error.value = msg
    } finally {
      loading.value = false
    }
  }

  function setFilters(newFilters: OrderFilters) {
    filters.value = { ...filters.value, ...newFilters }
    page.value = 1
  }

  function setPage(p: number) {
    page.value = p
  }

  function setPageSize(ps: number) {
    pageSize.value = ps
    page.value = 1
  }

  function clearFilters() {
    filters.value = {}
    page.value = 1
  }

  function clearDetail() {
    currentDetail.value = null
  }

  function clearError() {
    error.value = null
  }

  return {
    orders,
    total,
    page,
    pageSize,
    filters,
    currentDetail,
    loading,
    error,
    loadOrders,
    loadDetail,
    setFilters,
    setPage,
    setPageSize,
    clearFilters,
    clearDetail,
    clearError,
  }
})
