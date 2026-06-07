<script setup lang="ts">
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { computed } from 'vue'

const route = useRoute()
const authStore = useAuthStore()

const isAdmin = computed(() => authStore.user?.role === 'admin')

interface NavItem {
  name: string
  path: string
  label: string
  icon: string
}

const navItems: NavItem[] = [
  { name: 'Dashboard', path: '/dashboard', label: '分析看板', icon: '📊' },
  { name: 'Orders', path: '/orders', label: '订单管理', icon: '📦' },
  { name: 'Profit', path: '/profit', label: '利润看板', icon: '💰' },
  { name: 'Settings', path: '/settings', label: '设置', icon: '⚙️' },
  { name: 'Alerts', path: '/alerts', label: '告警通知', icon: '🔔' },
  { name: 'Pricing', path: '/pricing', label: '套餐定价', icon: '🏷️' },
  { name: 'Subscription', path: '/subscription', label: '订阅管理', icon: '🔑' },
  { name: 'Account', path: '/account', label: '账户设置', icon: '👤' },
]

function isActive(path: string) {
  return route.path.startsWith(path)
}
</script>

<template>
  <aside class="sidebar">
    <div class="sidebar-brand">
      <span class="brand-icon">📈</span>
      <span class="brand-text">Ozon Analytics</span>
    </div>

    <nav class="sidebar-nav">
      <router-link
        v-for="item in navItems"
        :key="item.name"
        :to="item.path"
        class="nav-item"
        :class="{ active: isActive(item.path) }"
      >
        <span class="nav-icon">{{ item.icon }}</span>
        <span class="nav-label">{{ item.label }}</span>
      </router-link>
    </nav>

    <nav v-if="isAdmin" class="sidebar-nav sidebar-nav--admin">
      <div class="nav-section-title">管理</div>
      <router-link to="/admin" class="nav-item" :class="{ active: isActive('/admin') }">
        <span class="nav-icon">🛡️</span>
        <span class="nav-label">管理后台</span>
      </router-link>
    </nav>

    <div class="sidebar-footer">
      <div class="user-info">
        <span class="user-email">{{ authStore.user?.email }}</span>
      </div>
      <button class="btn-ghost btn-logout" @click="authStore.logout()">
        退出登录
      </button>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 220px;
  min-height: 100vh;
  background: var(--color-surface);
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 20px 16px;
  border-bottom: 1px solid var(--color-border);
}

.brand-icon {
  font-size: 24px;
}

.brand-text {
  font-size: 16px;
  font-weight: 700;
  color: var(--color-primary);
}

.sidebar-nav {
  flex: 1;
  padding: 12px 8px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  color: var(--color-text-secondary);
  text-decoration: none;
  font-size: 14px;
  transition: all 0.15s ease;
}

.nav-item:hover {
  background: var(--color-bg-hover);
  color: var(--color-text);
}

.nav-item.active {
  background: var(--color-primary-bg);
  color: var(--color-primary);
  font-weight: 600;
}

.nav-icon {
  font-size: 18px;
  width: 24px;
  text-align: center;
  flex-shrink: 0;
}

.sidebar-nav--admin {
  flex: 0;
  padding-top: 0;
  border-top: 1px solid var(--color-border);
}

.nav-section-title {
  padding: 8px 12px 4px;
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.sidebar-footer {
  padding: 12px 8px;
  border-top: 1px solid var(--color-border);
}

.user-info {
  padding: 4px 12px 8px;
  font-size: 12px;
  color: var(--color-text-tertiary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.btn-logout {
  width: 100%;
  padding: 8px 12px;
  font-size: 13px;
  justify-content: center;
  color: var(--color-danger);
}

.btn-logout:hover {
  background: var(--color-danger-bg);
}

@media (max-width: 768px) {
  .sidebar {
    width: 60px;
  }
  .brand-text,
  .nav-label,
  .user-info,
  .btn-logout {
    display: none;
  }
  .sidebar-brand {
    justify-content: center;
    padding: 16px 8px;
  }
  .nav-item {
    justify-content: center;
    padding: 10px;
  }
  .nav-icon {
    margin: 0;
  }
}
</style>
