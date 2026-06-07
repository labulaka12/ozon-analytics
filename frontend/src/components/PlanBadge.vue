<template>
  <span class="plan-badge" :class="`plan-badge--${planName}`">
    {{ displayName }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  planName: string
}>()

const displayName = computed(() => {
  const map: Record<string, string> = {
    free: 'Free',
    pro: 'Pro',
    enterprise: 'Enterprise',
  }
  return map[props.planName] || props.planName
})
</script>

<style scoped>
.plan-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.5px;
}
.plan-badge--free { background: #f5f5f5; color: #757575; }
.plan-badge--pro { background: #e3f2fd; color: #1565c0; }
.plan-badge--enterprise { background: #f3e5f5; color: #7b1fa2; }
</style>
