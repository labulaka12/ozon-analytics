<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useStoreStore } from '@/stores/store'
import { fetchExchangeRate, updateExchangeRate, fetchExpenses, createExpense, updateExpense, deleteExpense, getExportCsvUrl, getProfitExportCsvUrl } from '@/api/settings'
import type { ExchangeRateData, ExpenseItem, ExpenseCreate } from '@/api/settings'

const storeStore = useStoreStore()

// ---- 汇率 ----
const exchangeRate = ref<ExchangeRateData | null>(null)
const rateInput = ref('')
const rateLoading = ref(false)
const rateMessage = ref('')

async function loadRate() {
  rateLoading.value = true
  try {
    exchangeRate.value = await fetchExchangeRate()
    rateInput.value = String(exchangeRate.value.rate)
  } catch { /* ignore */ }
  finally { rateLoading.value = false }
}

async function saveRate() {
  const val = parseFloat(rateInput.value)
  if (isNaN(val) || val <= 0) return
  rateLoading.value = true
  rateMessage.value = ''
  try {
    const res = await updateExchangeRate(val)
    exchangeRate.value = { rate: res.rate }
    rateMessage.value = '汇率更新成功'
  } catch {
    rateMessage.value = '更新失败'
  } finally {
    rateLoading.value = false
    setTimeout(() => rateMessage.value = '', 3000)
  }
}

// ---- 手动费用 ----
const expenses = ref<ExpenseItem[]>([])
const expenseLoading = ref(false)
const showExpenseForm = ref(false)
const editingExpense = ref<ExpenseItem | null>(null)
const expenseForm = ref<ExpenseCreate>({ store_id: 0, expense_type: '', amount_cny: 0 })
const expenseMessage = ref('')

async function loadExpenses() {
  if (!storeStore.currentStoreId) return
  expenseLoading.value = true
  try {
    expenses.value = await fetchExpenses(storeStore.currentStoreId)
  } catch { /* ignore */ }
  finally { expenseLoading.value = false }
}

function openNewExpense() {
  editingExpense.value = null
  expenseForm.value = { store_id: storeStore.currentStoreId ?? 0, expense_type: '', amount_cny: 0 }
  showExpenseForm.value = true
}

function openEditExpense(e: ExpenseItem) {
  editingExpense.value = e
  expenseForm.value = {
    store_id: storeStore.currentStoreId ?? 0,
    expense_type: e.expense_type,
    amount_cny: e.amount_cny,
  }
  showExpenseForm.value = true
}

async function saveExpense() {
  expenseLoading.value = true
  expenseMessage.value = ''
  try {
    if (editingExpense.value) {
      await updateExpense(editingExpense.value.id, expenseForm.value)
      expenseMessage.value = '费用更新成功'
    } else {
      await createExpense(expenseForm.value)
      expenseMessage.value = '费用添加成功'
    }
    showExpenseForm.value = false
    await loadExpenses()
  } catch {
    expenseMessage.value = '操作失败'
  } finally {
    expenseLoading.value = false
    setTimeout(() => expenseMessage.value = '', 3000)
  }
}

async function removeExpense(id: number) {
  if (!confirm('确定删除此费用记录？')) return
  expenseLoading.value = true
  try {
    await deleteExpense(id)
    expenseMessage.value = '删除成功'
    await loadExpenses()
  } catch {
    expenseMessage.value = '删除失败'
  } finally {
    expenseLoading.value = false
    setTimeout(() => expenseMessage.value = '', 3000)
  }
}

// ---- CSV 导出 ----
const exportDateFrom = ref('')
const exportDateTo = ref('')

function getCsvLink() {
  if (!storeStore.currentStoreId) return '#'
  return getExportCsvUrl(storeStore.currentStoreId, exportDateFrom.value || undefined, exportDateTo.value || undefined)
}

function getProfitCsvLink() {
  if (!storeStore.currentStoreId) return '#'
  return getProfitExportCsvUrl(storeStore.currentStoreId, exportDateFrom.value || undefined, exportDateTo.value || undefined)
}

// ---- 生命周期 ----
onMounted(() => {
  loadRate()
})

watch(() => storeStore.currentStoreId, () => {
  loadExpenses()
})
</script>

<template>
  <div class="settings-view">
    <!-- 消息 -->
    <div v-if="rateMessage || expenseMessage" class="message-bar" :class="{ 'message-success': rateMessage }">
      {{ rateMessage || expenseMessage }}
    </div>

    <!-- 汇率设置 -->
    <section class="setting-card">
      <h3 class="section-title">汇率设置</h3>
      <p class="section-desc">人民币 (CNY) 兑卢布 (RUB) 汇率</p>
      <div class="rate-form">
        <div class="form-group rate-input-group">
          <label for="rate">1 CNY = ? RUB</label>
          <input
            id="rate"
            v-model="rateInput"
            type="number"
            step="0.01"
            class="form-input"
            placeholder="例如 13.50"
          />
        </div>
        <div class="rate-info" v-if="exchangeRate">
          上次更新：{{ exchangeRate.updated_at ?? '未知' }}
        </div>
        <button class="btn btn-primary" :disabled="rateLoading" @click="saveRate">
          保存汇率
        </button>
      </div>
    </section>

    <!-- 手动费用管理 -->
    <section class="setting-card">
      <div class="section-header">
        <div>
          <h3 class="section-title">手动费用</h3>
          <p class="section-desc">记录平台费用、物流费等额外支出</p>
        </div>
        <button class="btn btn-primary" @click="openNewExpense">添加费用</button>
      </div>

      <!-- 费用表单 -->
      <div v-if="showExpenseForm" class="expense-form">
        <div class="form-group">
          <label>费用类型</label>
          <select v-model="expenseForm.expense_type" class="form-select">
            <option value="platform_fee">平台费用</option>
            <option value="logistics">物流费</option>
            <option value="advertising">广告费</option>
            <option value="storage">仓储费</option>
            <option value="other">其他</option>
          </select>
        </div>
        <div class="form-group">
          <label>金额 (CNY)</label>
          <input v-model.number="expenseForm.amount_cny" type="number" step="0.01" class="form-input" />
        </div>
        <div class="form-actions">
          <button class="btn btn-primary btn-sm" :disabled="expenseLoading" @click="saveExpense">
            {{ editingExpense ? '更新' : '保存' }}
          </button>
          <button class="btn btn-ghost btn-sm" @click="showExpenseForm = false">取消</button>
        </div>
      </div>

      <!-- 费用列表 -->
      <div v-if="expenseLoading && expenses.length === 0" class="loading-bar">加载中...</div>
      <div v-else-if="expenses.length === 0" class="empty-state-sm">暂无费用记录</div>
      <div v-else class="table-wrapper">
        <table class="data-table">
          <thead>
            <tr>
              <th>类型</th>
              <th>金额 (CNY)</th>
              <th>描述</th>
              <th>日期</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="e in expenses" :key="e.id">
              <td>{{ e.expense_type }}</td>
              <td>¥{{ e.amount_cny.toFixed(2) }}</td>
              <td>{{ e.description ?? '-' }}</td>
              <td>{{ e.expense_date ?? e.created_at?.slice(0, 10) ?? '-' }}</td>
              <td>
                <button class="btn btn-text btn-sm" @click="openEditExpense(e)">编辑</button>
                <button class="btn btn-text btn-sm btn-text-danger" @click="removeExpense(e.id)">删除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- CSV 导出 -->
    <section class="setting-card">
      <h3 class="section-title">数据导出</h3>
      <p class="section-desc">导出 CSV 格式数据用于本地分析</p>
      <div class="export-form">
        <div class="filter-group">
          <label class="filter-label">日期范围</label>
          <input v-model="exportDateFrom" type="date" class="form-input filter-input" />
          <span class="filter-sep">~</span>
          <input v-model="exportDateTo" type="date" class="form-input filter-input" />
        </div>
        <div class="export-actions">
          <a :href="getCsvLink()" class="btn btn-secondary" download>导出分析数据</a>
          <a :href="getProfitCsvLink()" class="btn btn-secondary" download>导出利润数据</a>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.settings-view {
  max-width: 900px;
}

.setting-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 10px;
  padding: 24px;
  margin-bottom: 20px;
}

.section-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 4px;
  color: var(--color-text);
}

.section-desc {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin: 0 0 16px;
}

.message-bar {
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 13px;
  margin-bottom: 16px;
}

.message-success {
  background: var(--color-success-bg);
  color: var(--color-success);
}

.loading-bar {
  text-align: center;
  padding: 12px;
  color: var(--color-text-tertiary);
  font-size: 14px;
}

.empty-state-sm {
  text-align: center;
  padding: 24px;
  color: var(--color-text-tertiary);
  font-size: 14px;
}

/* 汇率 */
.rate-form {
  display: flex;
  align-items: flex-end;
  gap: 16px;
  flex-wrap: wrap;
}

.rate-input-group {
  width: 200px;
}

.rate-input-group label {
  display: block;
  font-size: 13px;
  color: var(--color-text-secondary);
  margin-bottom: 4px;
}

.rate-info {
  font-size: 12px;
  color: var(--color-text-tertiary);
}

/* 费用表单 */
.expense-form {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  padding: 16px;
  background: var(--color-bg);
  border-radius: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.form-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

/* 导出 */
.export-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-label {
  font-size: 13px;
  color: var(--color-text-secondary);
  white-space: nowrap;
}

.filter-input {
  width: 150px;
}

.filter-sep {
  color: var(--color-text-tertiary);
}

.export-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}
</style>
