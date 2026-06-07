<template>
  <div class="subscription-page">
    <h1>订阅管理</h1>

    <div v-if="store.loading" class="loading">加载中...</div>

    <template v-else>
      <!-- 当前套餐 -->
      <div class="current-plan-card">
        <div class="plan-info">
          <div class="plan-name-row">
            <h2>{{ store.planDisplayName }}</h2>
            <span class="status-badge" :class="`status-badge--${store.subscription?.status || 'none'}`">
              {{ statusLabel }}
            </span>
          </div>
          <p v-if="store.subscription?.trial_end" class="plan-detail">
            试用到期: {{ formatDate(store.subscription.trial_end) }}
          </p>
          <p v-if="store.subscription?.current_period_end" class="plan-detail">
            计费周期到期: {{ formatDate(store.subscription.current_period_end) }}
          </p>
        </div>
        <div class="plan-actions">
          <button v-if="store.isFreePlan" class="btn btn-primary" @click="$router.push('/pricing')">升级套餐</button>
          <button v-else class="btn btn-outline" @click="openPortal">管理支付</button>
          <button v-if="store.isActive && !store.isFreePlan" class="btn btn-danger-outline" @click="handleCancel">
            取消订阅
          </button>
        </div>
      </div>

      <!-- 用量统计 -->
      <div v-if="store.usage" class="usage-section">
        <h3>用量统计</h3>
        <div class="usage-grid">
          <div class="usage-card">
            <div class="usage-label">店铺数</div>
            <QuotaBar :current="store.usage.stores.current" :limit="store.usage.stores.limit" />
          </div>
          <div class="usage-card">
            <div class="usage-label">告警规则</div>
            <QuotaBar :current="store.usage.alert_rules.current" :limit="store.usage.alert_rules.limit" />
          </div>
          <div class="usage-card">
            <div class="usage-label">商品数</div>
            <QuotaBar :current="store.usage.products.current" :limit="store.usage.products.limit" />
          </div>
        </div>
      </div>

      <!-- 支付历史 -->
      <div class="payments-section">
        <h3>支付历史</h3>
        <div v-if="payments.length === 0" class="empty-state">暂无支付记录</div>
        <table v-else class="data-table">
          <thead>
            <tr>
              <th>日期</th>
              <th>金额</th>
              <th>状态</th>
              <th>描述</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in payments" :key="p.id">
              <td>{{ formatDate(p.paid_at || p.created_at) }}</td>
              <td>${{ (p.amount_cents / 100).toFixed(2) }}</td>
              <td>
                <span class="payment-status" :class="`payment-status--${p.status}`">{{ p.status }}</span>
              </td>
              <td>{{ p.description || '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useSubscriptionStore } from '@/stores/subscription'
import { fetchPaymentHistory, createPortal, cancelSubscription } from '@/api/subscription'
import type { PaymentRecord } from '@/types/subscription'
import QuotaBar from '@/components/QuotaBar.vue'

const store = useSubscriptionStore()
const payments = ref<PaymentRecord[]>([])

const statusLabel = computed(() => {
  const map: Record<string, string> = {
    trialing: '试用中',
    active: '已激活',
    past_due: '逾期',
    cancelled: '已取消',
    expired: '已过期',
    none: '未订阅',
  }
  return map[store.subscription?.status || 'none'] || store.subscription?.status
})

function formatDate(d: string | null): string {
  if (!d) return '-'
  return new Date(d).toLocaleDateString('zh-CN')
}

async function openPortal() {
  try {
    const { portal_url } = await createPortal()
    window.location.href = portal_url
  } catch (e: any) {
    alert(e?.response?.data?.detail || '打开管理页面失败')
  }
}

async function handleCancel() {
  if (!confirm('确定要取消订阅吗？取消后当前计费周期内仍可使用。')) return
  try {
    await cancelSubscription()
    store.loadCurrentSubscription()
  } catch (e: any) {
    alert(e?.response?.data?.detail || '取消订阅失败')
  }
}

onMounted(async () => {
  await store.loadAll()
  try {
    payments.value = await fetchPaymentHistory()
  } catch { /* ignore */ }
})
</script>

<style scoped>
.subscription-page {
  max-width: 900px;
  margin: 0 auto;
  padding: 32px 24px;
}
h1 { font-size: 24px; font-weight: 700; margin-bottom: 24px; }
.loading { text-align: center; padding: 48px; color: #888; }

.current-plan-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 24px 28px;
  margin-bottom: 32px;
}
.plan-name-row { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
.plan-name-row h2 { font-size: 22px; margin: 0; }
.status-badge {
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}
.status-badge--trialing { background: #e8f5e9; color: #2e7d32; }
.status-badge--active { background: #e3f2fd; color: #1565c0; }
.status-badge--past_due { background: #fff3e0; color: #e65100; }
.status-badge--cancelled { background: #fce4ec; color: #c62828; }
.status-badge--expired { background: #f5f5f5; color: #757575; }
.plan-detail { font-size: 14px; color: #666; margin: 4px 0; }

.plan-actions { display: flex; gap: 8px; flex-shrink: 0; }
.btn {
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: all 0.2s;
}
.btn-primary { background: #1a73e8; color: #fff; }
.btn-primary:hover { background: #1558b0; }
.btn-outline { border: 1px solid #1a73e8; background: transparent; color: #1a73e8; }
.btn-outline:hover { background: #f0f7ff; }
.btn-danger-outline { border: 1px solid #e53935; background: transparent; color: #e53935; }
.btn-danger-outline:hover { background: #fff5f5; }

.usage-section { margin-bottom: 32px; }
.usage-section h3 { font-size: 18px; margin-bottom: 16px; }
.usage-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
@media (max-width: 700px) { .usage-grid { grid-template-columns: 1fr; } }
.usage-card { background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; }
.usage-label { font-size: 14px; color: #666; margin-bottom: 8px; }

.payments-section { margin-bottom: 32px; }
.payments-section h3 { font-size: 18px; margin-bottom: 16px; }
.empty-state { text-align: center; padding: 32px; color: #999; background: #f9f9f9; border-radius: 8px; }
.data-table { width: 100%; border-collapse: collapse; background: #fff; border-radius: 8px; overflow: hidden; }
.data-table th, .data-table td { padding: 12px 16px; text-align: left; border-bottom: 1px solid #f0f0f0; }
.data-table th { background: #f8f9fa; font-size: 13px; color: #666; font-weight: 600; }
.payment-status {
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 500;
}
.payment-status--paid { background: #e8f5e9; color: #2e7d32; }
.payment-status--failed { background: #fce4ec; color: #c62828; }
.payment-status--refunded { background: #fff3e0; color: #e65100; }
</style>
