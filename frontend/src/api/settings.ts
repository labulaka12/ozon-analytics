import request from './request'

export interface ExchangeRateData {
  rate: number
  updated_at?: string
}

export interface ExpenseItem {
  id: number
  expense_type: string
  amount_cny: number
  product_id: number | null
  description: string | null
  expense_date: string | null
  created_at: string | null
}

export interface ExpenseCreate {
  store_id: number
  expense_type: string
  amount_cny: number
  product_id?: number | null
  description?: string | null
  expense_date?: string | null
}

// 汇率
export function fetchExchangeRate() {
  return request.get<ExchangeRateData>('/api/settings/exchange-rate').then(r => r.data)
}

export function updateExchangeRate(rate: number) {
  return request.put<{ message: string; rate: number }>('/api/settings/exchange-rate', { rate }).then(r => r.data)
}

// 采购成本
export function updateProductCost(storeId: number, productId: number, costPrice: number) {
  return request.put<{ message: string; cost_price: number }>(`/api/products/${productId}/cost`, null, {
    params: { store_id: storeId, cost_price: costPrice },
  }).then(r => r.data)
}

// 手动费用
export function fetchExpenses(storeId: number) {
  return request.get<ExpenseItem[]>('/api/expenses', { params: { store_id: storeId } }).then(r => r.data)
}

export function createExpense(data: ExpenseCreate) {
  return request.post<{ message: string; id: number }>('/api/expenses', data).then(r => r.data)
}

export function updateExpense(id: number, data: Partial<ExpenseCreate>) {
  return request.put<{ message: string }>(`/api/expenses/${id}`, data).then(r => r.data)
}

export function deleteExpense(id: number) {
  return request.delete<{ message: string }>(`/api/expenses/${id}`).then(r => r.data)
}

// CSV 导出（直接打开链接）
export function getExportCsvUrl(storeId: number, dateFrom?: string, dateTo?: string) {
  const params = new URLSearchParams({ store_id: String(storeId) })
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  return `/api/export/csv?${params.toString()}`
}

export function getProfitExportCsvUrl(storeId: number, dateFrom?: string, dateTo?: string) {
  const params = new URLSearchParams({ store_id: String(storeId) })
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  return `/api/export/profit-csv?${params.toString()}`
}
