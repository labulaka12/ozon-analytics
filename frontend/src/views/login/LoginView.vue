<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'

const authStore = useAuthStore()
const router = useRouter()

const email = ref('')
const password = ref('')
const submitting = ref(false)

async function handleSubmit() {
  if (!email.value || !password.value) return
  submitting.value = true
  authStore.clearError()
  try {
    await authStore.login({ email: email.value, password: password.value })
  } catch {
    // error is stored in authStore.error
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="login-view">
    <h2 class="form-title">登录</h2>

    <div v-if="authStore.error" class="form-error">
      {{ authStore.error }}
    </div>

    <form @submit.prevent="handleSubmit" class="auth-form">
      <div class="form-group">
        <label for="email">邮箱</label>
        <input
          id="email"
          v-model="email"
          type="email"
          class="form-input"
          placeholder="请输入邮箱"
          required
          autocomplete="email"
        />
      </div>

      <div class="form-group">
        <label for="password">密码</label>
        <input
          id="password"
          v-model="password"
          type="password"
          class="form-input"
          placeholder="请输入密码"
          required
          autocomplete="current-password"
        />
      </div>

      <button type="submit" class="btn btn-primary btn-block" :disabled="submitting">
        {{ submitting ? '登录中...' : '登录' }}
      </button>
    </form>

    <p class="form-footer">
      还没有账号？
      <router-link to="/register" class="link">立即注册</router-link>
    </p>
  </div>
</template>

<style scoped>
.login-view {
  width: 100%;
}

.form-title {
  font-size: 22px;
  font-weight: 600;
  color: var(--color-text);
  margin: 0 0 24px;
  text-align: center;
}

.form-error {
  background: var(--color-danger-bg);
  color: var(--color-danger);
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 13px;
  margin-bottom: 16px;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-footer {
  text-align: center;
  margin: 20px 0 0;
  font-size: 14px;
  color: var(--color-text-secondary);
}

.link {
  color: var(--color-primary);
  text-decoration: none;
  font-weight: 500;
}

.link:hover {
  text-decoration: underline;
}
</style>
