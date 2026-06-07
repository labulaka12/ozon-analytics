/** 账户设置 Store */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { updateProfile, updateEmail, changePassword } from '@/api/account'

export const useAccountStore = defineStore('account', () => {
  // ---- state ----
  const loading = ref(false)
  const error = ref<string | null>(null)
  const successMessage = ref<string | null>(null)

  // ---- actions ----
  async function saveProfile(data: { display_name?: string }) {
    loading.value = true
    error.value = null
    successMessage.value = null
    try {
      await updateProfile(data)
      successMessage.value = '资料更新成功'
    } catch (e: any) {
      error.value = e?.response?.data?.detail || e?.message || '更新失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function saveEmail(newEmail: string, password: string) {
    loading.value = true
    error.value = null
    successMessage.value = null
    try {
      await updateEmail({ new_email: newEmail, password })
      successMessage.value = '邮箱已更新，请验证新邮箱'
    } catch (e: any) {
      error.value = e?.response?.data?.detail || e?.message || '修改邮箱失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function savePassword(oldPassword: string, newPassword: string) {
    loading.value = true
    error.value = null
    successMessage.value = null
    try {
      await changePassword(oldPassword, newPassword)
      successMessage.value = '密码修改成功'
    } catch (e: any) {
      error.value = e?.response?.data?.detail || e?.message || '修改密码失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  function clearMessages() {
    error.value = null
    successMessage.value = null
  }

  return {
    loading, error, successMessage,
    saveProfile, saveEmail, savePassword, clearMessages,
  }
})
