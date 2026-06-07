<template>
  <div class="verify-page">
    <div v-if="loading" class="loading">验证中...</div>
    <div v-else-if="success" class="result success">
      <h2>✓ 邮箱验证成功</h2>
      <p>您的邮箱已验证，现在可以使用全部功能。</p>
      <router-link to="/dashboard" class="btn">进入控制台</router-link>
    </div>
    <div v-else class="result error">
      <h2>✗ 验证失败</h2>
      <p>{{ error }}</p>
      <router-link to="/account" class="btn">返回账户设置</router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { verifyEmail } from '@/api/account'

const route = useRoute()
const loading = ref(true)
const success = ref(false)
const error = ref('')

onMounted(async () => {
  const token = route.query.token as string
  if (!token) {
    error.value = '缺少验证令牌'
    loading.value = false
    return
  }

  try {
    await verifyEmail(token)
    success.value = true
  } catch (e: any) {
    error.value = e?.response?.data?.detail || '验证链接无效或已过期'
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.verify-page {
  max-width: 440px;
  margin: 80px auto;
  padding: 40px 32px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.08);
  text-align: center;
}
.loading { color: #888; font-size: 16px; }
.result h2 { font-size: 20px; margin-bottom: 12px; }
.result p { color: #666; margin-bottom: 20px; }
.result.success h2 { color: #2e7d32; }
.result.error h2 { color: #c62828; }
.btn {
  display: inline-block;
  padding: 10px 24px;
  background: #1a73e8;
  color: #fff;
  text-decoration: none;
  border-radius: 8px;
  font-size: 14px;
}
.btn:hover { background: #1558b0; }
</style>
