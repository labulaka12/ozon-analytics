import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  fetchAlertRules,
  createAlertRule,
  updateAlertRule,
  deleteAlertRule,
  toggleAlertRule,
  checkAlerts,
  sendTestAlert,
} from '@/api/alerts'
import type { AlertRule, AlertRuleCreate, AlertRuleUpdate, AlertCheckResult } from '@/types/alert'

export const useAlertStore = defineStore('alert', () => {
  // ---- state ----
  const rules = ref<AlertRule[]>([])
  const checkResult = ref<AlertCheckResult | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // ---- actions ----
  async function loadRules(storeId?: number) {
    loading.value = true
    error.value = null
    try {
      const res = await fetchAlertRules(storeId)
      rules.value = res.rules ?? []
    } catch (e: any) {
      error.value = e?.response?.data?.detail || e?.message || '加载告警规则失败'
    } finally {
      loading.value = false
    }
  }

  async function addRule(data: AlertRuleCreate) {
    loading.value = true
    error.value = null
    try {
      const res = await createAlertRule(data)
      rules.value.push(res.rule)
      return res.rule
    } catch (e: any) {
      error.value = e?.response?.data?.detail || e?.message || '创建告警规则失败'
      return null
    } finally {
      loading.value = false
    }
  }

  async function editRule(ruleId: number, data: AlertRuleUpdate) {
    loading.value = true
    error.value = null
    try {
      const res = await updateAlertRule(ruleId, data)
      const idx = rules.value.findIndex(r => r.id === ruleId)
      if (idx >= 0) rules.value[idx] = res.rule
      return res.rule
    } catch (e: any) {
      error.value = e?.response?.data?.detail || e?.message || '更新告警规则失败'
      return null
    } finally {
      loading.value = false
    }
  }

  async function removeRule(ruleId: number) {
    loading.value = true
    error.value = null
    try {
      await deleteAlertRule(ruleId)
      rules.value = rules.value.filter(r => r.id !== ruleId)
    } catch (e: any) {
      error.value = e?.response?.data?.detail || e?.message || '删除告警规则失败'
    } finally {
      loading.value = false
    }
  }

  async function toggleRule(ruleId: number) {
    loading.value = true
    error.value = null
    try {
      const res = await toggleAlertRule(ruleId)
      const idx = rules.value.findIndex(r => r.id === ruleId)
      if (idx >= 0) rules.value[idx] = res.rule
      return res.rule
    } catch (e: any) {
      error.value = e?.response?.data?.detail || e?.message || '切换告警规则失败'
      return null
    } finally {
      loading.value = false
    }
  }

  async function runCheck(storeId?: number) {
    loading.value = true
    error.value = null
    try {
      checkResult.value = await checkAlerts(storeId)
    } catch (e: any) {
      error.value = e?.response?.data?.detail || e?.message || '告警检查失败'
    } finally {
      loading.value = false
    }
  }

  async function testAlert(channel: string, target: string) {
    loading.value = true
    error.value = null
    try {
      return await sendTestAlert(channel, target)
    } catch (e: any) {
      error.value = e?.response?.data?.detail || e?.message || '发送测试告警失败'
      return null
    } finally {
      loading.value = false
    }
  }

  function clearError() {
    error.value = null
  }

  return {
    rules,
    checkResult,
    loading,
    error,
    loadRules,
    addRule,
    editRule,
    removeRule,
    toggleRule,
    runCheck,
    testAlert,
    clearError,
  }
})
