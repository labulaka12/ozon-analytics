<script setup lang="ts">
import { onMounted, watch, computed } from 'vue'
import { useStoreStore } from '@/stores/store'
import { useProfitStore } from '@/stores/profit'
import LineChart from '@/components/charts/LineChart.vue'
import BarChart from '@/components/charts/BarChart.vue'
import PieChart from '@/components/charts/PieChart.vue'

const storeStore = useStoreStore()
const profitStore = useProfitStore()

function loadData() {
  if (!storeStore.currentStoreId) return
  profitStore.loadAll(storeStore.currentStoreId)
}

onMounted(loadData)
watch(() => storeStore.currentStoreId, () => {
  profitStore.clearAll()
  loadData()
})

function formatCNY(amount: number) {
  return '¥' + amount.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function formatPct(pct: number) {
  return pct.toFixed(2) + '%'
}

function confidenceLabel(c: string) {
  const map: Record<string, string> = { high: '高', medium: '中', low: '低' }
  return map[c] ?? c
}

function statusClass(val: number) {
  if (val > 0) return 'tag-success'
  if (val < 0) return 'tag-danger'
  return 'tag-default'
}

// ---- 利润趋势图数据 ----
const profitTrendData = computed(() => ({
  dates: profitStore.trend.map(t => t.date),
  revenue: profitStore.trend.map(t => t.revenue),
  cost: profitStore.trend.map(t => t.cost),
  fees: profitStore.trend.map(t => t.fees),
  profit: profitStore.trend.map(t => t.profit),
}))

// ---- 产品利润排名柱状图 ----
const productRankData = computed(() => {
  const items = profitStore.products.slice(0, 10)
  return {
    names: items.map(p => {
      const name = p.product_name || p.offer_id
      return name.length > 14 ? name.slice(0, 14) + '…' : name
    }),
    profits: items.map(p => p.profit),
    margins: items.map(p => p.margin),
  }
})

// ---- 费用饼图数据 ----
const feePieData = computed(() =>
  profitStore.fees.map(f => ({
    name: f.name,
    value: f.amount,
  }))
)
</script>

<template>
  <div class="profit-view">
    <!-- 加载 & 错误 -->
    <div v-if="profitStore.loading" class="loading-bar">加载中...</div>
    <div v-if="profitStore.error" class="error-bar">{{ profitStore.error }}</div>

    <!-- KPI 汇总卡片 -->
    <section v-if="profitStore.summary" class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-label">总收入</div>
        <div class="kpi-value">{{ formatCNY(profitStore.summary.total_revenue) }}</div>
      </div>
      <div class="kpi-card kpi-card-warn">
        <div class="kpi-label">总成本</div>
        <div class="kpi-value">{{ formatCNY(profitStore.summary.total_cost) }}</div>
      </div>
      <div class="kpi-card kpi-card-warn">
        <div class="kpi-label">总费用</div>
        <div class="kpi-value">{{ formatCNY(profitStore.summary.total_fees) }}</div>
      </div>
      <div class="kpi-card" :class="statusClass(profitStore.summary.total_profit)">
        <div class="kpi-label">总利润</div>
        <div class="kpi-value">{{ formatCNY(profitStore.summary.total_profit) }}</div>
      </div>
      <div class="kpi-card" :class="statusClass(profitStore.summary.profit_margin)">
        <div class="kpi-label">利润率</div>
        <div class="kpi-value">{{ formatPct(profitStore.summary.profit_margin) }}</div>
      </div>
    </section>

    <!-- 空状态 -->
    <section v-else-if="!profitStore.loading" class="empty-state">
      <p>暂无利润数据，请先同步数据</p>
    </section>

    <!-- 利润趋势折线图 -->
    <section v-if="profitTrendData.dates.length > 0" class="section-card">
      <h3 class="section-title">利润趋势</h3>
      <LineChart
        :x-data="profitTrendData.dates"
        :series="[
          { name: '收入', data: profitTrendData.revenue, color: '#10b981' },
          { name: '成本', data: profitTrendData.cost, color: '#f59e0b' },
          { name: '费用', data: profitTrendData.fees, color: '#8b5cf6' },
          { name: '利润', data: profitTrendData.profit, color: '#2563eb' },
        ]"
        :show-data-zoom="profitTrendData.dates.length > 14"
        height="380px"
      />
    </section>

    <!-- 利润趋势表格 (可折叠) -->
    <section v-if="profitStore.trend.length > 0" class="section-card">
      <details class="collapsible-section">
        <summary class="section-title collapsible-toggle">
          利润趋势明细
          <span class="collapse-hint">点击展开</span>
        </summary>
        <div class="trend-table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>日期</th>
                <th>收入</th>
                <th>费用</th>
                <th>成本</th>
                <th>利润</th>
                <th>利润率</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in profitStore.trend" :key="item.date">
                <td>{{ item.date }}</td>
                <td>{{ formatCNY(item.revenue) }}</td>
                <td>{{ formatCNY(item.fees) }}</td>
                <td>{{ formatCNY(item.cost) }}</td>
                <td :class="item.profit >= 0 ? 'text-success' : 'text-danger'">{{ formatCNY(item.profit) }}</td>
                <td>{{ formatPct(item.margin) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </details>
    </section>

    <!-- 产品利润排名柱状图 + 费用构成饼图 -->
    <section v-if="productRankData.names.length > 0 || feePieData.length > 0" class="chart-grid-2">
      <div v-if="productRankData.names.length > 0" class="section-card">
        <h3 class="section-title">产品利润排名 Top10</h3>
        <BarChart
          :x-data="productRankData.names"
          :series="[
            { name: '利润', data: productRankData.profits, color: '#2563eb' },
          ]"
          height="340px"
        />
      </div>

      <div v-if="feePieData.length > 0" class="section-card">
        <h3 class="section-title">费用构成</h3>
        <PieChart
          :data="feePieData"
          height="340px"
        />
      </div>
    </section>

    <!-- 产品利润排名表格 -->
    <section v-if="profitStore.products.length > 0" class="section-card">
      <details class="collapsible-section" open>
        <summary class="section-title collapsible-toggle">
          产品利润排名
          <span class="collapse-hint">点击收起</span>
        </summary>
        <div class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>#</th>
                <th>商品</th>
                <th>销量</th>
                <th>收入</th>
                <th>利润</th>
                <th>利润率</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(item, idx) in profitStore.products" :key="item.product_id">
                <td>{{ idx + 1 }}</td>
                <td>{{ item.product_name || item.offer_id }}</td>
                <td>{{ item.sold_units }}</td>
                <td>{{ formatCNY(item.revenue) }}</td>
                <td :class="item.profit >= 0 ? 'text-success' : 'text-danger'">{{ formatCNY(item.profit) }}</td>
                <td>{{ formatPct(item.margin) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </details>
    </section>

    <!-- 费用明细表格 -->
    <section v-if="profitStore.fees.length > 0" class="section-card">
      <details class="collapsible-section">
        <summary class="section-title collapsible-toggle">
          费用明细 <span class="section-subtitle">合计：{{ formatCNY(profitStore.feeTotal) }}</span>
          <span class="collapse-hint">点击展开</span>
        </summary>
        <div class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>费用项</th>
                <th>金额</th>
                <th>占比</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="fee in profitStore.fees" :key="fee.name">
                <td>{{ fee.name }}</td>
                <td>{{ formatCNY(fee.amount) }}</td>
                <td>{{ formatPct(fee.pct) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </details>
    </section>

    <!-- V2 完整费用分解 -->
    <section v-if="profitStore.v2Summary" class="section-card">
      <details class="collapsible-section" open>
        <summary class="section-title collapsible-toggle">
          完整费用分解（V2）
          <span class="section-subtitle">利润率 {{ formatPct(profitStore.v2Summary.profit_margin) }} | ROI {{ formatPct(profitStore.v2Summary.roi) }}</span>
          <span class="collapse-hint">点击收起</span>
        </summary>
        <div class="v2-breakdown-grid">
          <div class="v2-card">
            <h4 class="v2-card-title">收入</h4>
            <div class="v2-row"><span>销售收入</span><span>{{ formatCNY(profitStore.v2Summary.revenue) }}</span></div>
            <div class="v2-row"><span>退货损失</span><span class="text-danger">-{{ formatCNY(profitStore.v2Summary.returns_loss) }}</span></div>
            <div class="v2-row v2-row-total"><span>净收入</span><span>{{ formatCNY(profitStore.v2Summary.net_revenue) }}</span></div>
          </div>
          <div class="v2-card">
            <h4 class="v2-card-title">平台费用</h4>
            <div class="v2-row"><span>佣金</span><span>{{ formatCNY(profitStore.v2Summary.commission) }}</span></div>
            <div class="v2-row"><span>物流费</span><span>{{ formatCNY(profitStore.v2Summary.logistics) }}</span></div>
            <div class="v2-row"><span>广告费</span><span>{{ formatCNY(profitStore.v2Summary.advertising) }}</span></div>
            <div class="v2-row"><span>罚款</span><span>{{ formatCNY(profitStore.v2Summary.penalty) }}</span></div>
            <div class="v2-row"><span>其他平台费</span><span>{{ formatCNY(profitStore.v2Summary.other_platform_fees) }}</span></div>
            <div class="v2-row v2-row-total"><span>平台费用合计</span><span class="text-danger">-{{ formatCNY(profitStore.v2Summary.total_platform_fees) }}</span></div>
          </div>
          <div class="v2-card">
            <h4 class="v2-card-title">采购成本（CNY → RUB）</h4>
            <div class="v2-row"><span>采购成本</span><span>¥{{ profitStore.v2Summary.purchase_cost_cny?.toFixed(2) }}</span></div>
            <div class="v2-row"><span>头程物流</span><span>¥{{ profitStore.v2Summary.freight_cost_cny?.toFixed(2) }}</span></div>
            <div class="v2-row"><span>关税</span><span>¥{{ profitStore.v2Summary.customs_cost_cny?.toFixed(2) }}</span></div>
            <div class="v2-row"><span>其他手动费用</span><span>¥{{ profitStore.v2Summary.other_manual_cost_cny?.toFixed(2) }}</span></div>
            <div class="v2-row"><span>折合 RUB（汇率 {{ profitStore.v2Summary.exchange_rate }}）</span><span class="text-danger">-{{ formatCNY(profitStore.v2Summary.total_manual_cost_rub) }}</span></div>
          </div>
          <div class="v2-card v2-card-result">
            <h4 class="v2-card-title">利润结果</h4>
            <div class="v2-row"><span>总成本 (RUB)</span><span class="text-danger">-{{ formatCNY(profitStore.v2Summary.total_cost) }}</span></div>
            <div class="v2-row v2-row-total"><span>净利润 (RUB)</span><span :class="profitStore.v2Summary.net_profit >= 0 ? 'text-success' : 'text-danger'">{{ formatCNY(profitStore.v2Summary.net_profit) }}</span></div>
            <div class="v2-row"><span>净利润 (CNY)</span><span :class="profitStore.v2Summary.net_profit_cny >= 0 ? 'text-success' : 'text-danger'">¥{{ profitStore.v2Summary.net_profit_cny?.toFixed(2) }}</span></div>
            <div class="v2-row"><span>利润率</span><span>{{ formatPct(profitStore.v2Summary.profit_margin) }}</span></div>
            <div class="v2-row"><span>ROI</span><span>{{ formatPct(profitStore.v2Summary.roi) }}</span></div>
          </div>
        </div>
      </details>
    </section>

    <!-- 利润预测 & 盈亏平衡 -->
    <section v-if="profitStore.prediction || profitStore.breakeven" class="section-card">
      <h3 class="section-title">预测分析</h3>
      <div class="predict-grid">
        <div v-if="profitStore.prediction" class="predict-card">
          <h4 class="predict-card-title">利润预测</h4>
          <div class="predict-row">
            <span class="predict-label">日均利润</span>
            <span class="predict-value">{{ formatCNY(profitStore.prediction.avg_daily_profit) }}</span>
          </div>
          <div class="predict-row">
            <span class="predict-label">趋势方向</span>
            <span class="predict-value">{{ profitStore.prediction.trend_direction === 'up' ? '↑ 上升' : '↓ 下降' }}</span>
          </div>
          <div class="predict-row">
            <span class="predict-label">趋势幅度</span>
            <span class="predict-value">{{ formatCNY(profitStore.prediction.trend_amount) }}</span>
          </div>
          <div class="predict-row">
            <span class="predict-label">预测日均利润</span>
            <span class="predict-value">{{ formatCNY(profitStore.prediction.predicted_daily_profit) }}</span>
          </div>
          <div class="predict-row">
            <span class="predict-label">{{ profitStore.prediction.days_ahead }} 天预测总额</span>
            <span class="predict-value">{{ formatCNY(profitStore.prediction.predicted_total) }}</span>
          </div>
          <div class="predict-row">
            <span class="predict-label">置信度</span>
            <span class="predict-value" :class="profitStore.prediction.confidence === 'high' ? 'text-success' : profitStore.prediction.confidence === 'low' ? 'text-danger' : ''">
              {{ confidenceLabel(profitStore.prediction.confidence) }}
            </span>
          </div>
        </div>

        <div v-if="profitStore.breakeven" class="predict-card">
          <h4 class="predict-card-title">盈亏平衡分析</h4>
          <div class="predict-row">
            <span class="predict-label">盈亏平衡销量</span>
            <span class="predict-value">{{ profitStore.breakeven.breakeven_units }}</span>
          </div>
          <div class="predict-row">
            <span class="predict-label">当前销量</span>
            <span class="predict-value">{{ profitStore.breakeven.current_sold_units }}</span>
          </div>
          <div class="predict-row">
            <span class="predict-label">固定成本</span>
            <span class="predict-value">{{ formatCNY(profitStore.breakeven.fixed_cost_rub) }}</span>
          </div>
          <div class="predict-row">
            <span class="predict-label">平均单价</span>
            <span class="predict-value">{{ formatCNY(profitStore.breakeven.avg_price) }}</span>
          </div>
          <div class="predict-row">
            <span class="predict-label">单位贡献</span>
            <span class="predict-value">{{ formatCNY(profitStore.breakeven.unit_contribution) }}</span>
          </div>
          <div class="predict-row">
            <span class="predict-label">是否盈利</span>
            <span class="predict-value" :class="profitStore.breakeven.is_profitable ? 'text-success' : 'text-danger'">
              {{ profitStore.breakeven.is_profitable ? '是' : '否' }}
            </span>
          </div>
        </div>
      </div>
    </section>

    <!-- 空状态 -->
    <section v-if="!profitStore.loading && !profitStore.summary && !profitStore.prediction && !profitStore.breakeven" class="empty-state">
      <p>暂无预测数据</p>
    </section>
  </div>
</template>

<style scoped>
.profit-view {
  max-width: 1400px;
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
  margin-top: 28px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 12px;
  color: var(--color-text);
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-subtitle {
  font-size: 13px;
  font-weight: 400;
  color: var(--color-text-secondary);
}

.text-success {
  color: var(--color-success) !important;
  font-weight: 600;
}

.text-danger {
  color: var(--color-danger) !important;
  font-weight: 600;
}

/* 可折叠区块 */
.collapsible-section {
  border: none;
}

.collapsible-toggle {
  cursor: pointer;
  user-select: none;
}

.collapsible-toggle::-webkit-details-marker {
  display: none;
}

.collapsible-toggle::before {
  content: '▸';
  display: inline-block;
  margin-right: 6px;
  font-size: 12px;
  transition: transform 0.2s;
}

details[open] > .collapsible-toggle::before {
  transform: rotate(90deg);
}

.collapse-hint {
  font-size: 12px;
  font-weight: 400;
  color: var(--color-text-tertiary);
  margin-left: 4px;
}

/* 预测卡片 */
.predict-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 16px;
}

.predict-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 10px;
  padding: 20px;
}

.predict-card-title {
  font-size: 14px;
  font-weight: 600;
  margin: 0 0 16px;
  color: var(--color-text);
}

.predict-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0;
}

.predict-label {
  font-size: 13px;
  color: var(--color-text-secondary);
}

.predict-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text);
}

.trend-table-wrapper {
  max-height: 360px;
  overflow-y: auto;
  border: 1px solid var(--color-border);
  border-radius: 8px;
}

/* V2 完整费用分解 */
.v2-breakdown-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 16px;
  margin-top: 12px;
}

.v2-card {
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: 10px;
  padding: 16px;
}

.v2-card-result {
  border-color: var(--color-primary);
  background: var(--color-primary-bg, #eff6ff);
}

.v2-card-title {
  font-size: 14px;
  font-weight: 600;
  margin: 0 0 12px;
  color: var(--color-text);
}

.v2-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
  font-size: 13px;
  color: var(--color-text-secondary);
}

.v2-row span:last-child {
  font-weight: 600;
  color: var(--color-text);
  font-size: 14px;
}

.v2-row-total {
  padding-top: 8px;
  margin-top: 6px;
  border-top: 1px dashed var(--color-border);
}

.v2-row-total span {
  font-weight: 700;
  font-size: 14px;
}
</style>
