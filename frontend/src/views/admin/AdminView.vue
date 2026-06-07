<template>
  <div class="admin-page">
    <h1>管理后台</h1>

    <!-- 标签页切换 -->
    <div class="tabs">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        class="tab-btn"
        :class="{ 'tab-btn--active': activeTab === tab.key }"
        @click="activeTab = tab.key"
      >
        {{ tab.label }}
      </button>
    </div>

    <!-- 系统统计 -->
    <div v-if="activeTab === 'stats'" class="tab-content">
      <div v-if="stats" class="stats-grid">
        <div class="stat-card">
          <div class="stat-value">{{ stats.users.total }}</div>
          <div class="stat-label">总用户数</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ stats.users.active }}</div>
          <div class="stat-label">活跃用户</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ stats.stores.total }}</div>
          <div class="stat-label">店铺总数</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ stats.subscriptions.by_plan.pro || 0 }}</div>
          <div class="stat-label">Pro 用户</div>
        </div>
      </div>

      <!-- 健康状态 -->
      <div v-if="health" class="health-section">
        <h3>系统状态</h3>
        <div class="health-row">
          <span>数据库</span>
          <span class="health-dot" :class="`health-dot--${health.database}`"></span>
          {{ health.database === 'ok' ? '正常' : '异常' }}
        </div>
        <div class="health-row">
          <span>Redis</span>
          <span class="health-dot" :class="`health-dot--${health.redis === 'ok' ? 'ok' : 'warn'}`"></span>
          {{ health.redis === 'ok' ? '正常' : health.redis === 'not_configured' ? '未配置' : '异常' }}
        </div>
      </div>
    </div>

    <!-- 用户管理 -->
    <div v-if="activeTab === 'users'" class="tab-content">
      <div class="toolbar">
        <input v-model="userSearch" class="input" placeholder="搜索邮箱..." @keyup.enter="loadUsers" />
        <button class="btn btn-primary" @click="loadUsers">搜索</button>
      </div>
      <table class="data-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>邮箱</th>
            <th>状态</th>
            <th>角色</th>
            <th>注册时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in users" :key="u.id">
            <td>{{ u.id }}</td>
            <td>{{ u.email }}</td>
            <td>
              <span class="status-dot" :class="u.is_active ? 'status-dot--active' : 'status-dot--inactive'"></span>
              {{ u.is_active ? '启用' : '禁用' }}
            </td>
            <td>{{ u.role }}</td>
            <td>{{ formatDate(u.created_at) }}</td>
            <td>
              <button class="btn-sm" @click="toggleStatus(u.id)">{{ u.is_active ? '禁用' : '启用' }}</button>
              <button class="btn-sm" @click="toggleRole(u.id, u.role)">{{ u.role === 'admin' ? '降为用户' : '升为管理员' }}</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 订阅管理 -->
    <div v-if="activeTab === 'subscriptions'" class="tab-content">
      <table class="data-table">
        <thead>
          <tr>
            <th>用户</th>
            <th>套餐</th>
            <th>状态</th>
            <th>到期时间</th>
            <th>创建时间</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="s in subscriptions" :key="s.id">
            <td>{{ s.user_email }}</td>
            <td>{{ s.plan_name }}</td>
            <td>{{ s.status }}</td>
            <td>{{ formatDate(s.current_period_end || s.trial_end) }}</td>
            <td>{{ formatDate(s.created_at) }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 审计日志 -->
    <div v-if="activeTab === 'audit'" class="tab-content">
      <table class="data-table">
        <thead>
          <tr>
            <th>时间</th>
            <th>用户ID</th>
            <th>操作</th>
            <th>IP</th>
            <th>详情</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="l in auditLogs" :key="l.id">
            <td>{{ formatDate(l.created_at) }}</td>
            <td>{{ l.user_id || '-' }}</td>
            <td>{{ l.action }}</td>
            <td>{{ l.ip_address || '-' }}</td>
            <td>{{ l.detail ? JSON.stringify(l.detail).slice(0, 80) : '-' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import {
  fetchUsers, fetchSubscriptions, fetchSystemStats,
  fetchAuditLogs, fetchHealth, toggleUserStatus, changeUserRole,
} from '@/api/admin'
import type { AdminUser, AdminSubscription, SystemStats, AuditLogEntry, HealthStatus } from '@/types/admin'

const activeTab = ref('stats')
const tabs = [
  { key: 'stats', label: '系统统计' },
  { key: 'users', label: '用户管理' },
  { key: 'subscriptions', label: '订阅管理' },
  { key: 'audit', label: '审计日志' },
]

const stats = ref<SystemStats | null>(null)
const health = ref<HealthStatus | null>(null)
const users = ref<AdminUser[]>([])
const userSearch = ref('')
const subscriptions = ref<AdminSubscription[]>([])
const auditLogs = ref<AuditLogEntry[]>([])

function formatDate(d: string | null): string {
  if (!d) return '-'
  return new Date(d).toLocaleString('zh-CN')
}

async function loadUsers() {
  try {
    const data = await fetchUsers(1, 50, userSearch.value || undefined)
    users.value = data.items
  } catch { /* admin only */ }
}

async function loadSubscriptions() {
  try {
    const data = await fetchSubscriptions()
    subscriptions.value = data.items
  } catch { /* */ }
}

async function loadAuditLogs() {
  try {
    const data = await fetchAuditLogs()
    auditLogs.value = data.items
  } catch { /* */ }
}

async function toggleStatus(userId: number) {
  try {
    await toggleUserStatus(userId)
    loadUsers()
  } catch (e: any) {
    alert(e?.response?.data?.detail || '操作失败')
  }
}

async function toggleRole(userId: number, currentRole: string) {
  const newRole = currentRole === 'admin' ? 'user' : 'admin'
  try {
    await changeUserRole(userId, newRole)
    loadUsers()
  } catch (e: any) {
    alert(e?.response?.data?.detail || '操作失败')
  }
}

watch(activeTab, (tab) => {
  if (tab === 'users') loadUsers()
  else if (tab === 'subscriptions') loadSubscriptions()
  else if (tab === 'audit') loadAuditLogs()
})

onMounted(async () => {
  try {
    stats.value = await fetchSystemStats()
    health.value = await fetchHealth()
  } catch { /* admin only */ }
})
</script>

<style scoped>
.admin-page {
  max-width: 1100px;
  margin: 0 auto;
  padding: 32px 24px;
}
h1 { font-size: 24px; font-weight: 700; margin-bottom: 24px; }

.tabs { display: flex; gap: 4px; margin-bottom: 24px; border-bottom: 2px solid #f0f0f0; }
.tab-btn {
  padding: 10px 20px;
  background: none;
  border: none;
  font-size: 14px;
  color: #666;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  transition: all 0.2s;
}
.tab-btn--active { color: #1a73e8; border-bottom-color: #1a73e8; font-weight: 600; }

.stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }
@media (max-width: 700px) { .stats-grid { grid-template-columns: repeat(2, 1fr); } }
.stat-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 20px;
  text-align: center;
}
.stat-value { font-size: 32px; font-weight: 700; color: #1a73e8; }
.stat-label { font-size: 13px; color: #888; margin-top: 4px; }

.health-section { background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px; }
.health-section h3 { font-size: 16px; margin-bottom: 12px; }
.health-row { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; font-size: 14px; }
.health-dot {
  width: 10px; height: 10px; border-radius: 50%;
}
.health-dot--ok { background: #34a853; }
.health-dot--warn { background: #fbbc04; }
.health-dot--error { background: #e53935; }

.toolbar { display: flex; gap: 8px; margin-bottom: 16px; }
.input {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  flex: 1;
}

.data-table { width: 100%; border-collapse: collapse; background: #fff; border-radius: 8px; overflow: hidden; }
.data-table th, .data-table td { padding: 10px 12px; text-align: left; border-bottom: 1px solid #f0f0f0; font-size: 13px; }
.data-table th { background: #f8f9fa; font-weight: 600; color: #555; }

.status-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 4px; }
.status-dot--active { background: #34a853; }
.status-dot--inactive { background: #e53935; }

.btn { padding: 8px 16px; border-radius: 6px; font-size: 13px; cursor: pointer; border: none; }
.btn-primary { background: #1a73e8; color: #fff; }
.btn-sm {
  padding: 4px 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
  font-size: 12px;
  margin-right: 4px;
}
.btn-sm:hover { background: #f5f5f5; }
</style>
