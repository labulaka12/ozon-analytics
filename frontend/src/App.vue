<script setup lang="ts">
import { onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()

onMounted(() => {
  // 应用启动时尝试恢复登录态
  if (authStore.token) {
    authStore.fetchUser().catch(() => authStore.logout())
  }
})
</script>

<template>
  <router-view />
</template>
