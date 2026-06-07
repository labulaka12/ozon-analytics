<script setup lang="ts">
</script>

<template>
  <div class="auth-layout">
    <div class="auth-container">
      <div class="auth-brand">
        <span class="brand-icon">📈</span>
        <h1 class="brand-title">Ozon Analytics</h1>
        <p class="brand-desc">多店铺 Ozon 销售数据分析平台</p>
      </div>
      <div class="auth-card">
        <router-view />
      </div>
    </div>
  </div>
</template>

<style scoped>
.auth-layout {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: var(--color-bg);
  padding: 20px;
}

.auth-container {
  width: 100%;
  max-width: 420px;
}

.auth-brand {
  text-align: center;
  margin-bottom: 32px;
}

.brand-icon {
  font-size: 48px;
  display: block;
  margin-bottom: 12px;
}

.brand-title {
  font-size: 28px;
  font-weight: 700;
  color: var(--color-primary);
  margin: 0 0 8px;
}

.brand-desc {
  font-size: 14px;
  color: var(--color-text-secondary);
  margin: 0;
}

.auth-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 32px;
  box-shadow: var(--shadow-md);
}
</style>
