<script setup lang="ts">
import { onMounted, watch, ref } from 'vue'
import { useStoreStore } from '@/stores/store'
import { useOrderStore } from '@/stores/orders'

const storeStore = useStoreStore()
const orderStore = useOrderStore()
const detailVisible = ref(false)

function loadData() {
  if (!storeStore.currentStoreId) return
  orderStore.loadOrders(storeStore.currentStoreId)
}

onMounted(loadData)
watch(() => storeStore.currentStoreId, () => {
  orderStore.clearFilters()
  loadData()
})

function onPageChange(page: number) {
  if (!storeStore.currentStoreId) return
  orderStore.loadOrders(storeStore.currentStoreId, { page })
}

function showDetail(postingNumber: string) {
  if (!storeStore.currentStoreId) return
  orderStore.loadDetail(storeStore.currentStoreId, postingNumber)
  detailVisible.value = true
}

function closeDetail() {
  detailVisible.value = false
  orderStore.clearDetail()
}

function statusClass(status: string) {
  if (status === 'delivered') return 'tag-success'
  if (status === 'shipped') return 'tag-info'
  if (status === 'cancelled') return 'tag-danger'
  return 'tag-default'
}

function statusLabel(status: string) {
  const map: Record<string, string> = {
    delivered: '已送达',
    shipped: '已发货',
    cancelled: '已取消',
    awaiting_packaging: '待打包',
    awaiting_delivery: '待发货',
  }
  return map[status] ?? status
}

const totalPages = ref(0)
watch(() => [orderStore.total, orderStore.pageSize], () => {
  totalPages.value = Math.ceil(orderStore.total / orderStore.pageSize) || 1
}, { immediate: true })
</script>

<template>
  <div class="orders-view">
    <!-- 筛选栏 -->
    <section class="filter-bar">
      <div class="filter-group">
        <label class="filter-label">状态</label>
        <select v-model="orderStore.filters.status" class="form-select filter-select" @change="loadData">
          <option value="">全部</option>
          <option value="delivered">已送达</option>
          <option value="shipped">已发货</option>
          <option value="cancelled">已取消</option>
          <option value="awaiting_packaging">待打包</option>
          <option value="awaiting_delivery">待发货</option>
        </select>
      </div>
      <div class="filter-group">
        <label class="filter-label">日期</label>
        <input v-model="orderStore.filters.date_from" type="date" class="form-input filter-input" @change="loadData" />
        <span class="filter-sep">~</span>
        <input v-model="orderStore.filters.date_to" type="date" class="form-input filter-input" @change="loadData" />
      </div>
      <button class="btn btn-secondary" @click="orderStore.clearFilters(); loadData()">重置</button>
    </section>

    <!-- 加载状态 -->
    <div v-if="orderStore.loading" class="loading-bar">加载中...</div>
    <div v-if="orderStore.error" class="error-bar">{{ orderStore.error }}</div>

    <!-- 订单表格 -->
    <section v-if="orderStore.orders.length > 0" class="table-section">
      <div class="table-wrapper">
        <table class="data-table">
          <thead>
            <tr>
              <th>发货单号</th>
              <th>商品</th>
              <th>数量</th>
              <th>单价</th>
              <th>总价</th>
              <th>佣金</th>
              <th>收入</th>
              <th>状态</th>
              <th>下单时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="order in orderStore.orders" :key="order.posting_number">
              <td class="cell-mono">{{ order.posting_number.slice(0, 12) }}...</td>
              <td>{{ order.product_name ?? order.offer_id ?? '-' }}</td>
              <td>{{ order.quantity }}</td>
              <td>¥{{ order.price.toFixed(2) }}</td>
              <td>¥{{ order.total_price.toFixed(2) }}</td>
              <td>¥{{ order.commission.toFixed(2) }}</td>
              <td>¥{{ order.payout.toFixed(2) }}</td>
              <td><span class="tag" :class="statusClass(order.status)">{{ statusLabel(order.status) }}</span></td>
              <td class="cell-mono">{{ order.order_created_at?.slice(0, 10) ?? '-' }}</td>
              <td>
                <button class="btn btn-text" @click="showDetail(order.posting_number)">详情</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 分页 -->
      <div class="pagination">
        <button
          class="btn btn-ghost btn-sm"
          :disabled="orderStore.page <= 1"
          @click="onPageChange(orderStore.page - 1)"
        >
          上一页
        </button>
        <span class="page-info">第 {{ orderStore.page }} / {{ totalPages }} 页（共 {{ orderStore.total }} 条）</span>
        <button
          class="btn btn-ghost btn-sm"
          :disabled="orderStore.page >= totalPages"
          @click="onPageChange(orderStore.page + 1)"
        >
          下一页
        </button>
      </div>
    </section>

    <!-- 空状态 -->
    <section v-else-if="!orderStore.loading" class="empty-state">
      <p>暂无订单数据</p>
    </section>

    <!-- 订单详情弹窗 -->
    <div v-if="detailVisible && orderStore.currentDetail" class="modal-overlay" @click.self="closeDetail">
      <div class="modal-card">
        <div class="modal-header">
          <h3>订单详情</h3>
          <button class="btn btn-ghost" @click="closeDetail">✕</button>
        </div>
        <div class="modal-body">
          <div class="detail-info">
            <div class="detail-row">
              <span class="detail-label">发货单号</span>
              <span class="detail-value cell-mono">{{ orderStore.currentDetail.posting_number }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">状态</span>
              <span class="detail-value">
                <span class="tag" :class="statusClass(orderStore.currentDetail.status)">{{ statusLabel(orderStore.currentDetail.status) }}</span>
              </span>
            </div>
            <div class="detail-row">
              <span class="detail-label">下单时间</span>
              <span class="detail-value">{{ orderStore.currentDetail.order_created_at ?? '-' }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">发货时间</span>
              <span class="detail-value">{{ orderStore.currentDetail.shipped_at ?? '-' }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">送达时间</span>
              <span class="detail-value">{{ orderStore.currentDetail.delivered_at ?? '-' }}</span>
            </div>
          </div>

          <h4 class="detail-subtitle">商品明细</h4>
          <table class="data-table detail-table">
            <thead>
              <tr>
                <th>商品</th>
                <th>数量</th>
                <th>单价</th>
                <th>小计</th>
                <th>佣金</th>
                <th>收入</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, idx) in orderStore.currentDetail.items" :key="idx">
                <td>{{ item.product_name ?? item.offer_id ?? '-' }}</td>
                <td>{{ item.quantity }}</td>
                <td>¥{{ item.price.toFixed(2) }}</td>
                <td>¥{{ item.total_price.toFixed(2) }}</td>
                <td>¥{{ item.commission.toFixed(2) }}</td>
                <td>¥{{ item.payout.toFixed(2) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.orders-view {
  max-width: 1400px;
}

.filter-bar {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  margin-bottom: 20px;
  flex-wrap: wrap;
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

.filter-select {
  width: 140px;
}

.filter-sep {
  color: var(--color-text-tertiary);
}

.loading-bar {
  text-align: center;
  padding: 12px;
  color: var(--color-text-tertiary);
  font-size: 14px;
}

.error-bar {
  background: var(--color-danger-bg);
  color: var(--color-danger);
  padding: 10px 14px;
  border-radius: 8px;
  margin-bottom: 16px;
  font-size: 13px;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--color-text-tertiary);
  font-size: 15px;
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-top: 16px;
  padding: 12px 0;
}

.page-info {
  font-size: 13px;
  color: var(--color-text-secondary);
}

.cell-mono {
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 12px;
}

/* 弹窗 */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  padding: 20px;
}

.modal-card {
  background: var(--color-surface);
  border-radius: 12px;
  width: 100%;
  max-width: 720px;
  max-height: 80vh;
  overflow-y: auto;
  box-shadow: var(--shadow-lg);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--color-border);
}

.modal-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.modal-body {
  padding: 20px;
}

.detail-info {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 20px;
}

.detail-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.detail-label {
  font-size: 13px;
  color: var(--color-text-secondary);
  min-width: 80px;
}

.detail-value {
  font-size: 14px;
  color: var(--color-text);
}

.detail-subtitle {
  font-size: 14px;
  font-weight: 600;
  margin: 0 0 12px;
  color: var(--color-text);
}

.detail-table {
  font-size: 13px;
}
</style>
