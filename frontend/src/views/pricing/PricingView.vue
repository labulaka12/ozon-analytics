<template>
  <div class="pricing-page">
    <div class="pricing-header">
      <h1>选择适合你的套餐</h1>
      <p class="subtitle">从小卖家到大型企业，我们为每个阶段提供合适的工具</p>
    </div>

    <div class="plans-grid">
      <div
        v-for="plan in sortedPlans"
        :key="plan.name"
        class="plan-card"
        :class="{ 'plan-card--featured': plan.name === 'pro', 'plan-card--current': isCurrentPlan(plan.name) }"
      >
        <div v-if="plan.name === 'pro'" class="plan-badge">推荐</div>
        <div class="plan-header">
          <h2>{{ plan.display_name }}</h2>
          <div class="plan-price">
            <span v-if="plan.price_cents === 0" class="price-free">免费</span>
            <span v-else>
              <span class="price-amount">${{ (plan.price_cents / 100).toFixed(0) }}</span>
              <span class="price-period">/月</span>
            </span>
          </div>
        </div>

        <ul class="plan-features">
          <li><span class="check">✓</span> 最多 {{ plan.limits.max_stores }} 个店铺</li>
          <li><span class="check">✓</span> 每店铺 {{ plan.limits.max_products_per_store }} 个商品</li>
          <li><span class="check">✓</span> 数据保留 {{ plan.limits.data_retention_days }} 天</li>
          <li><span class="check">✓</span> {{ plan.limits.max_alert_rules }} 条告警规则</li>
          <li><span class="check">✓</span> 同步频率: {{ syncFrequencyLabel(plan.limits.sync_frequency) }}</li>
          <li v-if="plan.limits.profit_analysis"><span class="check">✓</span> 利润分析</li>
          <li v-else><span class="cross">✗</span> 利润分析</li>
          <li v-if="plan.limits.profit_prediction"><span class="check">✓</span> 利润预测</li>
          <li v-else><span class="cross">✗</span> 利润预测</li>
          <li><span class="check">✓</span> CSV 导出</li>
        </ul>

        <button
          class="plan-cta"
          :class="{ 'plan-cta--featured': plan.name === 'pro', 'plan-cta--current': isCurrentPlan(plan.name) }"
          :disabled="isCurrentPlan(plan.name) || !!upgrading"
          @click="handleSelectPlan(plan)"
        >
          <span v-if="isCurrentPlan(plan.name)">当前套餐</span>
          <span v-else-if="upgrading === plan.name">处理中...</span>
          <span v-else>选择此套餐</span>
        </button>
      </div>
    </div>

    <!-- FAQ -->
    <div class="faq-section">
      <h2>常见问题</h2>
      <div class="faq-list">
        <div v-for="(faq, i) in faqs" :key="i" class="faq-item" @click="toggleFaq(i)">
          <div class="faq-question">
            {{ faq.q }}
            <span class="faq-arrow" :class="{ 'faq-arrow--open': openFaq === i }">▸</span>
          </div>
          <div v-if="openFaq === i" class="faq-answer">{{ faq.a }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useSubscriptionStore } from '@/stores/subscription'
import { createCheckout } from '@/api/subscription'
import type { Plan } from '@/types/subscription'

const store = useSubscriptionStore()
const upgrading = ref<string | null>(null)
const openFaq = ref<number | null>(null)

const sortedPlans = computed(() => {
  return [...store.plans].sort((a, b) => (a.price_cents || 0) - (b.price_cents || 0))
})

function isCurrentPlan(name: string): boolean {
  return store.subscription?.plan_name === name
}

function syncFrequencyLabel(f: string): string {
  const map: Record<string, string> = {
    daily: '每日',
    every_8_hours: '每8小时',
    hourly: '每小时',
  }
  return map[f] || f
}

async function handleSelectPlan(plan: Plan) {
  if (plan.price_cents === 0) {
    // Free plan - no checkout needed
    return
  }
  upgrading.value = plan.name
  try {
    const { checkout_url } = await createCheckout(plan.name)
    window.location.href = checkout_url
  } catch (e: any) {
    alert(e?.response?.data?.detail || '创建支付会话失败，请稍后重试')
  } finally {
    upgrading.value = null
  }
}

function toggleFaq(i: number) {
  openFaq.value = openFaq.value === i ? null : i
}

const faqs = [
  { q: '可以随时更换套餐吗？', a: '可以。升级立即生效，降级在当前计费周期结束后生效。' },
  { q: '免费套餐有什么限制？', a: '免费套餐支持1个店铺、100个商品、每日同步、3条告警规则，不含利润分析。' },
  { q: '如何取消订阅？', a: '在订阅管理页面可以一键取消，取消后当前计费周期内仍可使用全部功能。' },
  { q: '支持哪些支付方式？', a: '我们通过 Stripe 安全处理支付，支持 Visa、Mastercard 等主流信用卡。' },
  { q: '数据安全吗？', a: '所有数据通过加密传输和存储，支付信息由 Stripe 处理，我们不存储信用卡信息。' },
]

onMounted(() => {
  store.loadAll()
})
</script>

<style scoped>
.pricing-page {
  max-width: 1100px;
  margin: 0 auto;
  padding: 40px 24px;
}
.pricing-header {
  text-align: center;
  margin-bottom: 48px;
}
.pricing-header h1 {
  font-size: 32px;
  font-weight: 700;
  color: #1a1a2e;
  margin-bottom: 12px;
}
.subtitle {
  font-size: 16px;
  color: #666;
}
.plans-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
  margin-bottom: 64px;
}
@media (max-width: 800px) {
  .plans-grid { grid-template-columns: 1fr; }
}
.plan-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 32px 24px;
  position: relative;
  transition: box-shadow 0.2s, transform 0.2s;
}
.plan-card:hover {
  box-shadow: 0 8px 24px rgba(0,0,0,0.08);
  transform: translateY(-2px);
}
.plan-card--featured {
  border-color: #1a73e8;
  box-shadow: 0 4px 16px rgba(26,115,232,0.15);
  transform: scale(1.03);
}
.plan-badge {
  position: absolute;
  top: -12px;
  left: 50%;
  transform: translateX(-50%);
  background: linear-gradient(135deg, #1a73e8, #4285f4);
  color: #fff;
  padding: 4px 16px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;
}
.plan-header { text-align: center; margin-bottom: 24px; }
.plan-header h2 { font-size: 22px; color: #1a1a2e; margin-bottom: 8px; }
.price-free { font-size: 28px; font-weight: 700; color: #34a853; }
.price-amount { font-size: 40px; font-weight: 700; color: #1a1a2e; }
.price-period { font-size: 14px; color: #888; }
.plan-features {
  list-style: none;
  padding: 0;
  margin: 0 0 28px 0;
  font-size: 14px;
  line-height: 2;
}
.plan-features li { color: #444; }
.check { color: #34a853; font-weight: 700; margin-right: 6px; }
.cross { color: #ccc; margin-right: 6px; }
.plan-cta {
  display: block;
  width: 100%;
  padding: 12px;
  border: 2px solid #1a73e8;
  background: transparent;
  color: #1a73e8;
  font-size: 15px;
  font-weight: 600;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}
.plan-cta:hover:not(:disabled) { background: #1a73e8; color: #fff; }
.plan-cta--featured { background: #1a73e8; color: #fff; }
.plan-cta--featured:hover:not(:disabled) { background: #1558b0; }
.plan-cta--current {
  border-color: #34a853;
  color: #34a853;
  cursor: default;
  background: transparent;
}
.plan-cta:disabled { opacity: 0.6; cursor: not-allowed; }
.faq-section { max-width: 700px; margin: 0 auto; }
.faq-section h2 { text-align: center; font-size: 24px; margin-bottom: 24px; }
.faq-item {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  margin-bottom: 8px;
  cursor: pointer;
  overflow: hidden;
}
.faq-question {
  padding: 16px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 500;
  color: #333;
}
.faq-arrow { transition: transform 0.2s; }
.faq-arrow--open { transform: rotate(90deg); }
.faq-answer { padding: 0 20px 16px; color: #666; font-size: 14px; line-height: 1.6; }
</style>
