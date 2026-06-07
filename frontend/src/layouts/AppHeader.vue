<script setup lang="ts">
import { computed } from 'vue'
import { useStoreStore } from '@/stores/store'

const storeStore = useStoreStore()

const currentStoreName = computed(() => storeStore.currentStore?.name ?? '未选择店铺')

function onStoreChange(event: Event) {
  const id = Number((event.target as HTMLSelectElement).value)
  if (id) storeStore.setCurrentStore(id)
}
</script>

<template>
  <header class="app-header">
    <div class="header-left">
      <h2 class="page-title">
        <slot name="title">分析看板</slot>
      </h2>
    </div>

    <div class="header-right">
      <div class="store-selector">
        <label class="store-label" for="store-select">店铺：</label>
        <select
          id="store-select"
          class="form-select store-select"
          :value="storeStore.currentStoreId ?? undefined"
          @change="onStoreChange"
        >
          <option v-if="storeStore.stores.length === 0" value="">暂无店铺</option>
          <option
            v-for="s in storeStore.stores"
            :key="s.id"
            :value="s.id"
          >
            {{ s.name }}
          </option>
        </select>
      </div>

      <div v-if="storeStore.currentStore" class="sync-info">
        <span class="last-sync">
          最后同步：{{ storeStore.currentStore.last_sync_at ?? '未同步' }}
        </span>
      </div>
    </div>
  </header>
</template>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  flex-wrap: wrap;
  gap: 12px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--color-text);
  margin: 0;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.store-selector {
  display: flex;
  align-items: center;
  gap: 6px;
}

.store-label {
  font-size: 13px;
  color: var(--color-text-secondary);
  white-space: nowrap;
}

.store-select {
  min-width: 160px;
}

.sync-info {
  font-size: 12px;
  color: var(--color-text-tertiary);
}

@media (max-width: 768px) {
  .app-header {
    padding: 12px 16px;
  }
  .page-title {
    font-size: 16px;
  }
}
</style>
