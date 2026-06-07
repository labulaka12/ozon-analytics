<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const submitting = ref(false)
const validationError = ref('')

async function handleSubmit() {
  validationError.value = ''

  if (!email.value || !password.value) {
    validationError.value = '请填写所有字段'
    return
  }
  if (password.value.length < 6) {
    validationError.value = '密码长度至少为 6 位'
    return
  }
  if (password.value !== confirmPassword.value) {
    validationError.value = '两次密码输入不一致'
    return
  }

  submitting.value = true
  authStore.clearError()
  try {
    await authStore.register({ email: email.value, password: password.value })
  } catch {
    // error is stored in authStore.error
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="register-view">
    <h2 class="form-title">注册</h2>

    <div v-if="validationError" class="form-error">
      {{ validationError }}
    </div>
    <div v-else-if="authStore.error" class="form-error">
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
          placeholder="至少 6 位密码"
          required
          autocomplete="new-password"
        />
      </div>

      <div class="form-group">
        <label for="confirm-password">确认密码</label>
        <input
          id="confirm-password"
          v-model="confirmPassword"
          type="password"
          class="form-input"
          placeholder="再次输入密码"
          required
          autocomplete="new-password"
        />
      </div>

      <button type="submit" class="btn btn-primary btn-block" :disabled="submitting">
        {{ submitting ? '注册中...' : '注册' }}
      </button>
    </form>

    <p class="form-footer">
      已有账号？
      <router-link to="/login" class="link">立即登录</router-link>
    </p>
  </div>
</template>

<style scoped>
.register-view {
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
