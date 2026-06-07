<template>
  <Teleport to="body">
    <div v-if="visible" class="upgrade-overlay" @click.self="close">
      <div class="upgrade-modal">
        <button class="close-btn" @click="close">&times;</button>
        <h2>升级以解锁更多功能</h2>
        <p class="upgrade-desc">
          {{ message || '您已达到当前套餐的限制，升级后即可继续使用。' }}
        </p>

        <div class="compare">
          <div class="compare-col compare-col--current">
            <div class="compare-title">当前套餐</div>
            <div class="compare-plan">{{ currentPlanName }}</div>
            <div class="compare-limit">{{ currentLimit }}</div>
          </div>
          <div class="compare-arrow">→</div>
          <div class="compare-col compare-col--upgrade">
            <div class="compare-title">升级到</div>
            <div class="compare-plan">{{ upgradePlanName }}</div>
            <div class="compare-limit">{{ upgradeLimit }}</div>
          </div>
        </div>

        <button class="btn-upgrade" @click="goPricing">查看套餐</button>
        <button class="btn-later" @click="close">稍后再说</button>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useSubscriptionStore } from '@/stores/subscription'

const props = defineProps<{
  visible: boolean
  resource?: string
  message?: string
}>()

const emit = defineEmits<{
  close: []
}>()

const router = useRouter()
const store = useSubscriptionStore()

const currentPlanName = computed(() => store.planDisplayName)
const upgradePlanName = computed(() => {
  const name = store.subscription?.plan_name
  if (name === 'free') return 'Pro'
  if (name === 'pro') return 'Enterprise'
  return 'Enterprise'
})

const currentLimit = computed(() => {
  if (!store.usage || !props.resource) return '-'
  const r = store.usage[props.resource as keyof typeof store.usage]
  if (typeof r === 'object' && 'limit' in r) return `${(r as { limit: number }).limit}`
  return '-'
})

const upgradeLimit = computed(() => {
  if (!props.resource) return '-'
  const map: Record<string, Record<string, string>> = {
    stores: { free: '5 个', pro: '50 个' },
    alert_rules: { free: '20 条', pro: '无限' },
    products: { free: '1000 个', pro: '无限' },
  }
  const name = store.subscription?.plan_name || 'free'
  return map[props.resource]?.[name] || '更多'
})

function close() {
  emit('close')
}

function goPricing() {
  close()
  router.push('/pricing')
}
</script>

<style scoped>
.upgrade-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.upgrade-modal {
  background: #fff;
  border-radius: 16px;
  padding: 32px;
  max-width: 440px;
  width: 90%;
  position: relative;
  text-align: center;
}
.close-btn {
  position: absolute;
  top: 12px;
  right: 16px;
  background: none;
  border: none;
  font-size: 24px;
  color: #999;
  cursor: pointer;
}
.upgrade-modal h2 { font-size: 20px; margin-bottom: 8px; }
.upgrade-desc { font-size: 14px; color: #666; margin-bottom: 20px; }

.compare {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-bottom: 24px;
}
.compare-col {
  padding: 16px;
  border-radius: 8px;
  text-align: center;
  flex: 1;
}
.compare-col--current { background: #f5f5f5; }
.compare-col--upgrade { background: #e3f2fd; }
.compare-title { font-size: 12px; color: #888; margin-bottom: 4px; }
.compare-plan { font-size: 18px; font-weight: 700; margin-bottom: 4px; }
.compare-limit { font-size: 14px; color: #555; }
.compare-arrow { font-size: 24px; color: #1a73e8; }

.btn-upgrade {
  display: block;
  width: 100%;
  padding: 12px;
  background: #1a73e8;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  margin-bottom: 8px;
}
.btn-upgrade:hover { background: #1558b0; }
.btn-later {
  background: none;
  border: none;
  color: #888;
  cursor: pointer;
  font-size: 13px;
}
</style>
