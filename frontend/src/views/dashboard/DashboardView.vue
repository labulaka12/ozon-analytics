<script setup lang="ts">
import { onMounted, watch, computed } from 'vue'
import { useStoreStore } from '@/stores/store'
import { useAnalyticsStore } from '@/stores/analytics'
import LineChart from '@/components/charts/LineChart.vue'
import BarChart from '@/components/charts/BarChart.vue'

const storeStore = useStoreStore()
const analyticsStore = useAnalyticsStore()

function loadData() {
  if (!storeStore.currentStoreId) return
  analyticsStore.loadData(storeStore.currentStoreId)
}

onMounted(loadData)

watch(() => storeStore.currentStoreId, () => {
  analyticsStore.clearAll()
  loadData()
})

function formatCNY(amount: number) {
  return '¥' + amount.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function formatNumber(n: number) {
  return n.toLocaleString('zh-CN')
}

function formatPct(n: number) {
  return (n * 100).toFixed(2) + '%'
}

// ---- 趋势图数据 ----
const trendData = computed(() => {
  const items = analyticsStore.items
  if (!items.length) return { dates: [], impressions: [], views: [], sessions: [], addToCart: [], orders: [], revenue: [] }

  // 按日期聚合
  const dateMap = new Map<string, { impressions: number; views: number; sessions: number; addToCart: number; orders: number; revenue: number }>()
  for (const row of items) {
    const d = row.date
    const existing = dateMap.get(d) || { impressions: 0, views: 0, sessions: 0, addToCart: 0, orders: 0, revenue: 0 }
    existing.impressions += row.impressions_search
    existing.views += row.views_total
    existing.sessions += row.sessions
    existing.addToCart += row.add_to_cart
    existing.orders += row.ordered_units
    existing.revenue += row.revenue
    dateMap.set(d, existing)
  }

  const sortedDates = [...dateMap.keys()].sort()
  return {
    dates: sortedDates,
    impressions: sortedDates.map(d => dateMap.get(d)!.impressions),
    views: sortedDates.map(d => dateMap.get(d)!.views),
    sessions: sortedDates.map(d => dateMap.get(d)!.sessions),
    addToCart: sortedDates.map(d => dateMap.get(d)!.addToCart),
    orders: sortedDates.map(d => dateMap.get(d)!.orders),
    revenue: sortedDates.map(d => dateMap.get(d)!.revenue),
  }
})

// ---- 转化漏斗数据 ----
const funnelData = computed(() => {
  const s = analyticsStore.summary
  if (!s) return []
  return [
    { name: '展示', value: s.total_impressions },
    { name: '浏览', value: s.total_views },
    { name: '访客', value: s.total_sessions },
    { name: '加购', value: s.total_add_to_cart },
    { name: '成交', value: s.total_ordered },
  ]
})

// ---- 商品 Top10 展示/浏览柱状图 ----
const productTopData = computed(() => {
  const items = analyticsStore.items
  if (!items.length) return { names: [], impressions: [], views: [] }

  // 按 product_id 聚合
  const productMap = new Map<string, { name: string; impressions: number; views: number }>()
  for (const row of items) {
    const key = String(row.product_id)
    const existing = productMap.get(key) || { name: row.offer_id || key, impressions: 0, views: 0 }
    existing.impressions += row.impressions_search
    existing.views += row.views_total
    productMap.set(key, existing)
  }

  // 取展示量 Top10
  const sorted = [...productMap.entries()]
    .sort((a, b) => b[1].impressions - a[1].impressions)
    .slice(0, 10)

  return {
    names: sorted.map(([, v]) => v.name.length > 12 ? v.name.slice(0, 12) + '…' : v.name),
    impressions: sorted.map(([, v]) => v.impressions),
    views: sorted.map(([, v]) => v.views),
  }
})
</script>

<template>
  <div class="dashboard-view">
    <!-- 筛选栏 -->
    <section class="filter-bar">
      <div class="filter-group">
        <label class="filter-label">日期范围</label>
        <input
          v-model="analyticsStore.filters.date_from"
          type="date"
          class="form-input filter-input"
          @change="loadData"
        />
        <span class="filter-sep">~</span>
        <input
          v-model="analyticsStore.filters.date_to"
          type="date"
          class="form-input filter-input"
          @change="loadData"
        />
      </div>
      <button class="btn btn-secondary" @click="analyticsStore.clearFilters(); loadData()">
        重置
      </button>
    </section>

    <!-- 加载状态 -->
    <div v-if="analyticsStore.loading" class="loading-bar">加载中...</div>
    <div v-if="analyticsStore.error" class="error-bar">{{ analyticsStore.error }}</div>

    <!-- KPI 指标卡片 -->
    <section v-if="analyticsStore.summary" class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-label">展示次数</div>
        <div class="kpi-value">{{ formatNumber(analyticsStore.summary.total_impressions) }}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">浏览量 (PDP)</div>
        <div class="kpi-value">{{ formatNumber(analyticsStore.summary.total_views_pdp) }}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">总浏览量</div>
        <div class="kpi-value">{{ formatNumber(analyticsStore.summary.total_views) }}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">访客数</div>
        <div class="kpi-value">{{ formatNumber(analyticsStore.summary.total_sessions) }}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">加入购物车</div>
        <div class="kpi-value">{{ formatNumber(analyticsStore.summary.total_add_to_cart) }}</div>
      </div>
      <div class="kpi-card kpi-card-accent">
        <div class="kpi-label">成交订单</div>
        <div class="kpi-value">{{ formatNumber(analyticsStore.summary.total_ordered) }}</div>
      </div>
      <div class="kpi-card kpi-card-money">
        <div class="kpi-label">总收入</div>
        <div class="kpi-value">{{ formatCNY(analyticsStore.summary.total_revenue) }}</div>
      </div>
      <div class="kpi-card kpi-card-warn">
        <div class="kpi-label">退货</div>
        <div class="kpi-value">{{ formatNumber(analyticsStore.summary.total_returns) }}</div>
      </div>
      <div class="kpi-card kpi-card-warn">
        <div class="kpi-label">取消</div>
        <div class="kpi-value">{{ formatNumber(analyticsStore.summary.total_cancellations) }}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">有数据天数</div>
        <div class="kpi-value">{{ analyticsStore.summary.days_with_data }}</div>
      </div>
    </section>

    <!-- 空状态 -->
    <section v-else-if="!analyticsStore.loading" class="empty-state">
      <p>暂无分析数据，请先同步店铺数据</p>
    </section>

    <!-- 流量趋势折线图 -->
    <section v-if="trendData.dates.length > 0" class="section-card">
      <h3 class="section-title">流量趋势</h3>
      <LineChart
        :x-data="trendData.dates"
        :series="[
          { name: '展示', data: trendData.impressions, color: '#2563eb' },
          { name: '浏览', data: trendData.views, color: '#10b981' },
          { name: '访客', data: trendData.sessions, color: '#f59e0b' },
        ]"
        :show-data-zoom="trendData.dates.length > 14"
        height="360px"
      />
    </section>

    <!-- 转化趋势折线图 -->
    <section v-if="trendData.dates.length > 0" class="section-card">
      <h3 class="section-title">转化趋势</h3>
      <LineChart
        :x-data="trendData.dates"
        :series="[
          { name: '加购', data: trendData.addToCart, color: '#8b5cf6' },
          { name: '成交', data: trendData.orders, color: '#ef4444' },
        ]"
        :show-data-zoom="trendData.dates.length > 14"
        height="300px"
      />
    </section>

    <!-- 收入趋势 + 转化漏斗 -->
    <section v-if="trendData.dates.length > 0 || funnelData.length > 0" class="chart-grid-2">
      <!-- 收入趋势 -->
      <div v-if="trendData.dates.length > 0" class="section-card">
        <h3 class="section-title">收入趋势</h3>
        <LineChart
          :x-data="trendData.dates"
          :series="[
            { name: '收入', data: trendData.revenue, color: '#10b981' },
          ]"
          :area-style="true"
          :show-data-zoom="trendData.dates.length > 14"
          height="300px"
        />
      </div>

      <!-- 转化漏斗 -->
      <div v-if="funnelData.length > 0" class="section-card">
        <h3 class="section-title">转化漏斗</h3>
        <div class="funnel-chart">
          <div v-for="(item, idx) in funnelData" :key="item.name" class="funnel-step">
            <div class="funnel-bar" :style="{
              width: funnelData.length ? Math.max(20, (item.value / funnelData[0].value) * 100) + '%' : '0%',
              background: ['#2563eb', '#3b82f6', '#60a5fa', '#8b5cf6', '#ef4444'][idx % 5],
            }">
              <span class="funnel-label">{{ item.name }}</span>
              <span class="funnel-value">{{ formatNumber(item.value) }}</span>
            </div>
            <div v-if="idx < funnelData.length - 1" class="funnel-rate">
              {{ funnelData[idx + 1].value > 0 ? formatPct(funnelData[idx + 1].value / item.value) : '0%' }}
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 商品 Top10 柱状图 -->
    <section v-if="productTopData.names.length > 0" class="section-card">
      <h3 class="section-title">商品展示/浏览 Top10</h3>
      <BarChart
        :x-data="productTopData.names"
        :series="[
          { name: '展示', data: productTopData.impressions, color: '#2563eb' },
          { name: '浏览', data: productTopData.views, color: '#10b981' },
        ]"
        height="320px"
      />
    </section>

    <!-- 数据表格 -->
    <section v-if="analyticsStore.items.length > 0" class="section-card">
      <h3 class="section-title">商品明细数据</h3>
      <div class="table-wrapper">
        <table class="data-table">
          <thead>
            <tr>
              <th>商品 ID</th>
              <th>Offer ID</th>
              <th>展示</th>
              <th>浏览量</th>
              <th>访客</th>
              <th>加购</th>
              <th>加购率</th>
              <th>成交</th>
              <th>收入</th>
              <th>退货</th>
              <th>取消</th>
              <th>平均排名</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in analyticsStore.items" :key="row.product_id + row.date">
              <td>{{ row.product_id }}</td>
              <td>{{ row.offer_id }}</td>
              <td>{{ formatNumber(row.impressions_search) }}</td>
              <td>{{ formatNumber(row.views_total) }}</td>
              <td>{{ formatNumber(row.sessions) }}</td>
              <td>{{ formatNumber(row.add_to_cart) }}</td>
              <td>{{ formatPct(row.conversion_to_cart) }}</td>
              <td>{{ formatNumber(row.ordered_units) }}</td>
              <td>{{ formatCNY(row.revenue) }}</td>
              <td>{{ formatNumber(row.returns_count) }}</td>
              <td>{{ formatNumber(row.cancellations) }}</td>
              <td>{{ row.position_avg?.toFixed(1) ?? '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<style scoped>
.dashboard-view {
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

.section-card {
  margin-top: 24px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 12px;
  color: var(--color-text);
}

/* 转化漏斗 */
.funnel-chart {
  padding: 16px 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.funnel-step {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.funnel-bar {
  min-height: 40px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  color: #fff;
  font-size: 13px;
  transition: width 0.5s ease;
}

.funnel-label {
  font-weight: 500;
}

.funnel-value {
  font-weight: 700;
  font-size: 14px;
}

.funnel-rate {
  font-size: 11px;
  color: var(--color-text-tertiary);
  margin-top: 2px;
}
</style>
