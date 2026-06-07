<script setup lang="ts">
import { onMounted } from 'vue'
import { useStoreStore } from '@/stores/store'
import AppSidebar from './AppSidebar.vue'
import AppHeader from './AppHeader.vue'

const storeStore = useStoreStore()

onMounted(() => {
  if (storeStore.stores.length === 0) {
    storeStore.loadStores()
  }
})
</script>

<template>
  <div class="app-layout">
    <AppSidebar />
    <div class="app-main">
      <AppHeader />
      <main class="app-content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  min-height: 100vh;
}

.app-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: var(--color-bg);
}

.app-content {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
}

@media (max-width: 768px) {
  .app-content {
    padding: 16px;
  }
}
</style>
