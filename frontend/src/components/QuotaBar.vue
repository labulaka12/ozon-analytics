<template>
  <div class="quota-bar">
    <div class="quota-bar-track">
      <div
        class="quota-bar-fill"
        :class="{ 'quota-bar-fill--warn': isNearLimit, 'quota-bar-fill--full': isAtLimit }"
        :style="{ width: percentage + '%' }"
      ></div>
    </div>
    <div class="quota-bar-label">
      {{ current }} / {{ limit === 99999 ? '∞' : limit }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  current: number
  limit: number
}>()

const percentage = computed(() => {
  if (props.limit === 99999 || props.limit >= 99999) return Math.min(props.current / 100 * 100, 100)
  return Math.min((props.current / props.limit) * 100, 100)
})

const isNearLimit = computed(() => {
  if (props.limit >= 99999) return false
  return props.current / props.limit >= 0.8
})

const isAtLimit = computed(() => {
  if (props.limit >= 99999) return false
  return props.current >= props.limit
})
</script>

<style scoped>
.quota-bar {
  display: flex;
  align-items: center;
  gap: 10px;
}
.quota-bar-track {
  flex: 1;
  height: 8px;
  background: #f0f0f0;
  border-radius: 4px;
  overflow: hidden;
}
.quota-bar-fill {
  height: 100%;
  background: #1a73e8;
  border-radius: 4px;
  transition: width 0.3s, background 0.3s;
}
.quota-bar-fill--warn { background: #fbbc04; }
.quota-bar-fill--full { background: #e53935; }
.quota-bar-label {
  font-size: 13px;
  color: #666;
  white-space: nowrap;
  min-width: 60px;
  text-align: right;
}
</style>
