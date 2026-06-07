import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { fetchStores, createStore, updateStore, deleteStore } from '@/api/stores'
import type { Store, StoreCreate, StoreUpdate } from '@/types/store'

export const useStoreStore = defineStore('store', () => {
  // ---- state ----
  const stores = ref<Store[]>([])
  const currentStoreId = ref<number | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // ---- getters ----
  const currentStore = computed(() =>
    stores.value.find(s => s.id === currentStoreId.value) ?? null
  )
  const activeStores = computed(() => stores.value.filter(s => s.is_active))

  // ---- actions ----
  async function loadStores() {
    loading.value = true
    error.value = null
    try {
      stores.value = await fetchStores()
      // 自动选中第一个店铺
      if (stores.value.length > 0 && !currentStoreId.value) {
        currentStoreId.value = stores.value[0].id
      }
    } catch (e: any) {
      const msg = e?.response?.data?.detail || e?.message || '加载店铺列表失败'
      error.value = msg
    } finally {
      loading.value = false
    }
  }

  async function addStore(data: StoreCreate) {
    loading.value = true
    error.value = null
    try {
      const res = await createStore(data)
      await loadStores()
      if (res.id) currentStoreId.value = res.id
      return res
    } catch (e: any) {
      const msg = e?.response?.data?.detail || e?.message || '添加店铺失败'
      error.value = msg
      throw new Error(msg)
    } finally {
      loading.value = false
    }
  }

  async function editStore(id: number, data: StoreUpdate) {
    loading.value = true
    error.value = null
    try {
      const res = await updateStore(id, data)
      await loadStores()
      return res
    } catch (e: any) {
      const msg = e?.response?.data?.detail || e?.message || '更新店铺失败'
      error.value = msg
      throw new Error(msg)
    } finally {
      loading.value = false
    }
  }

  async function removeStore(id: number) {
    loading.value = true
    error.value = null
    try {
      const res = await deleteStore(id)
      if (currentStoreId.value === id) {
        currentStoreId.value = stores.value.length > 1
          ? stores.value.find(s => s.id !== id)?.id ?? null
          : null
      }
      await loadStores()
      return res
    } catch (e: any) {
      const msg = e?.response?.data?.detail || e?.message || '删除店铺失败'
      error.value = msg
      throw new Error(msg)
    } finally {
      loading.value = false
    }
  }

  function setCurrentStore(id: number) {
    currentStoreId.value = id
  }

  function clearError() {
    error.value = null
  }

  return {
    stores,
    currentStoreId,
    loading,
    error,
    currentStore,
    activeStores,
    loadStores,
    addStore,
    editStore,
    removeStore,
    setCurrentStore,
    clearError,
  }
})
