<template>
  <div class="account-page">
    <h1>账户设置</h1>

    <!-- 提示消息 -->
    <div v-if="accountStore.successMessage" class="alert alert-success">
      {{ accountStore.successMessage }}
    </div>
    <div v-if="accountStore.error" class="alert alert-error">
      {{ accountStore.error }}
    </div>

    <!-- 个人资料 -->
    <section class="section">
      <h3>个人资料</h3>
      <div class="form-group">
        <label>邮箱</label>
        <div class="email-row">
          <span>{{ authStore.user?.email }}</span>
          <span v-if="authStore.user?.email_verified" class="verified-badge">已验证</span>
          <button v-else class="btn-link" @click="resendVerify">发送验证邮件</button>
        </div>
      </div>
      <div class="form-group">
        <label>显示名称</label>
        <input v-model="displayName" type="text" class="input" placeholder="输入显示名称" />
      </div>
      <button class="btn btn-primary" :disabled="accountStore.loading" @click="saveProfile">
        保存
      </button>
    </section>

    <!-- 修改邮箱 -->
    <section class="section">
      <h3>修改邮箱</h3>
      <div class="form-group">
        <label>新邮箱</label>
        <input v-model="newEmail" type="email" class="input" placeholder="输入新邮箱" />
      </div>
      <div class="form-group">
        <label>当前密码</label>
        <input v-model="emailPassword" type="password" class="input" placeholder="输入当前密码" />
      </div>
      <button class="btn btn-primary" :disabled="accountStore.loading" @click="saveEmail">
        修改邮箱
      </button>
    </section>

    <!-- 修改密码 -->
    <section class="section">
      <h3>修改密码</h3>
      <div class="form-group">
        <label>当前密码</label>
        <input v-model="oldPassword" type="password" class="input" placeholder="输入当前密码" />
      </div>
      <div class="form-group">
        <label>新密码</label>
        <input v-model="newPassword" type="password" class="input" placeholder="输入新密码 (至少6位)" />
      </div>
      <div class="form-group">
        <label>确认新密码</label>
        <input v-model="confirmPassword" type="password" class="input" placeholder="再次输入新密码" />
      </div>
      <button class="btn btn-primary" :disabled="accountStore.loading" @click="savePassword">
        修改密码
      </button>
    </section>

    <!-- 数据管理 -->
    <section class="section section--danger">
      <h3>数据管理</h3>
      <p class="section-desc">导出你的所有数据，或永久删除账户（此操作不可恢复）。</p>
      <div class="btn-row">
        <button class="btn btn-outline" @click="handleExport">导出数据</button>
        <button class="btn btn-danger" @click="handleDelete">删除账户</button>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useAccountStore } from '@/stores/account'
import { exportUserData, deleteAccount, resendVerification } from '@/api/account'

const authStore = useAuthStore()
const accountStore = useAccountStore()

const displayName = ref('')
const newEmail = ref('')
const emailPassword = ref('')
const oldPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')

onMounted(() => {
  displayName.value = authStore.user?.display_name || ''
  accountStore.clearMessages()
})

async function saveProfile() {
  try {
    await accountStore.saveProfile({ display_name: displayName.value })
  } catch { /* handled by store */ }
}

async function saveEmail() {
  if (!newEmail.value || !emailPassword.value) {
    accountStore.error = '请填写新邮箱和当前密码'
    return
  }
  try {
    await accountStore.saveEmail(newEmail.value, emailPassword.value)
    newEmail.value = ''
    emailPassword.value = ''
  } catch { /* handled by store */ }
}

async function savePassword() {
  if (!oldPassword.value || !newPassword.value) {
    accountStore.error = '请填写所有密码字段'
    return
  }
  if (newPassword.value !== confirmPassword.value) {
    accountStore.error = '两次输入的新密码不一致'
    return
  }
  if (newPassword.value.length < 6) {
    accountStore.error = '新密码至少6位'
    return
  }
  try {
    await accountStore.savePassword(oldPassword.value, newPassword.value)
    oldPassword.value = ''
    newPassword.value = ''
    confirmPassword.value = ''
  } catch { /* handled by store */ }
}

async function resendVerify() {
  try {
    await resendVerification()
    alert('验证邮件已发送')
  } catch (e: any) {
    alert(e?.response?.data?.detail || '发送失败')
  }
}

async function handleExport() {
  try {
    const blob = await exportUserData()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `ozon_data_${Date.now()}.json`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e: any) {
    alert('导出失败：' + (e?.message || '未知错误'))
  }
}

async function handleDelete() {
  const password = prompt('删除账户不可恢复！请输入密码确认：')
  if (!password) return
  if (!confirm('确定要永久删除账户吗？此操作不可恢复！')) return
  try {
    await deleteAccount(password)
    authStore.logout()
    window.location.href = '/login'
  } catch (e: any) {
    alert(e?.response?.data?.detail || '删除失败')
  }
}
</script>

<style scoped>
.account-page {
  max-width: 640px;
  margin: 0 auto;
  padding: 32px 24px;
}
h1 { font-size: 24px; font-weight: 700; margin-bottom: 24px; }

.alert {
  padding: 12px 16px;
  border-radius: 8px;
  margin-bottom: 16px;
  font-size: 14px;
}
.alert-success { background: #e8f5e9; color: #2e7d32; }
.alert-error { background: #fce4ec; color: #c62828; }

.section {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 20px;
}
.section--danger { border-color: #ffcdd2; }
.section h3 { font-size: 17px; font-weight: 600; margin-bottom: 16px; }
.section-desc { font-size: 14px; color: #666; margin-bottom: 16px; }

.form-group { margin-bottom: 14px; }
.form-group label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: #555;
  margin-bottom: 4px;
}
.input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  transition: border-color 0.2s;
  box-sizing: border-box;
}
.input:focus { outline: none; border-color: #1a73e8; }

.email-row { display: flex; align-items: center; gap: 8px; }
.verified-badge {
  font-size: 12px;
  padding: 2px 8px;
  background: #e8f5e9;
  color: #2e7d32;
  border-radius: 10px;
}
.btn-link {
  background: none;
  border: none;
  color: #1a73e8;
  cursor: pointer;
  font-size: 13px;
  text-decoration: underline;
}

.btn {
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: all 0.2s;
}
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary { background: #1a73e8; color: #fff; }
.btn-primary:hover:not(:disabled) { background: #1558b0; }
.btn-outline { border: 1px solid #1a73e8; background: transparent; color: #1a73e8; }
.btn-danger { background: #e53935; color: #fff; }
.btn-danger:hover { background: #c62828; }
.btn-row { display: flex; gap: 12px; }
</style>
