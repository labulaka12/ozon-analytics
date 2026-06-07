<template>
  <div class="reset-page">
    <h2>重置密码</h2>
    <div v-if="success" class="success-msg">{{ success }}</div>
    <div v-if="error" class="error-msg">{{ error }}</div>

    <form v-if="!success" @submit.prevent="handleSubmit">
      <div class="form-group">
        <label>新密码</label>
        <input v-model="newPassword" type="password" class="input" placeholder="至少6位" required />
      </div>
      <div class="form-group">
        <label>确认新密码</label>
        <input v-model="confirmPassword" type="password" class="input" placeholder="再次输入" required />
      </div>
      <button type="submit" class="btn btn-primary" :disabled="loading">
        {{ loading ? '处理中...' : '重置密码' }}
      </button>
    </form>

    <div v-else class="login-link">
      <router-link to="/login">返回登录</router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { resetPassword } from '@/api/account'

const route = useRoute()
const newPassword = ref('')
const confirmPassword = ref('')
const loading = ref(false)
const error = ref('')
const success = ref('')

async function handleSubmit() {
  error.value = ''
  if (newPassword.value.length < 6) {
    error.value = '密码至少6位'
    return
  }
  if (newPassword.value !== confirmPassword.value) {
    error.value = '两次输入不一致'
    return
  }

  const token = route.query.token as string
  if (!token) {
    error.value = '无效的重置链接'
    return
  }

  loading.value = true
  try {
    await resetPassword(token, newPassword.value)
    success.value = '密码重置成功，请使用新密码登录。'
  } catch (e: any) {
    error.value = e?.response?.data?.detail || '重置失败，链接可能已过期'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.reset-page {
  max-width: 400px;
  margin: 60px auto;
  padding: 32px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.08);
}
h2 { text-align: center; margin-bottom: 24px; }
.form-group { margin-bottom: 16px; }
.form-group label { display: block; font-size: 13px; color: #555; margin-bottom: 4px; }
.input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  box-sizing: border-box;
}
.btn {
  width: 100%;
  padding: 12px;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  cursor: pointer;
}
.btn-primary { background: #1a73e8; color: #fff; }
.btn:disabled { opacity: 0.5; }
.success-msg { color: #2e7d32; text-align: center; margin-bottom: 16px; }
.error-msg { color: #c62828; text-align: center; margin-bottom: 16px; }
.login-link { text-align: center; margin-top: 16px; }
.login-link a { color: #1a73e8; text-decoration: none; }
</style>
