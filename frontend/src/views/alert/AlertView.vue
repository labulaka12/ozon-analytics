<script setup lang="ts">
import { onMounted, watch, ref, computed } from 'vue'
import { useStoreStore } from '@/stores/store'
import { useAlertStore } from '@/stores/alert'
import { RULE_TYPE_LABELS, CHANNEL_LABELS } from '@/types/alert'
import type { AlertRuleCreate, RuleType, ChannelType } from '@/types/alert'

const storeStore = useStoreStore()
const alertStore = useAlertStore()

// ---- 表单状态 ----
const showDialog = ref(false)
const editingId = ref<number | null>(null)
const form = ref<AlertRuleCreate>({
  name: '',
  rule_type: 'sales_drop',
  threshold: 20,
  channel: 'email',
  target: '',
  enabled: true,
  description: '',
})

// ---- 测试告警 ----
const testDialog = ref(false)
const testChannel = ref<ChannelType>('email')
const testTarget = ref('')
const testResult = ref<string | null>(null)

// ---- 告警检查结果 ----
const showCheckResult = ref(false)

const currentStoreId = computed(() => storeStore.currentStoreId)

function loadData() {
  alertStore.loadRules(currentStoreId.value || undefined)
}

onMounted(loadData)
watch(currentStoreId, () => {
  alertStore.loadRules(currentStoreId.value || undefined)
})

// ---- 表单操作 ----
function openCreate() {
  editingId.value = null
  form.value = {
    name: '',
    rule_type: 'sales_drop',
    threshold: 20,
    channel: 'email',
    target: '',
    enabled: true,
    description: '',
    store_id: currentStoreId.value,
  }
  showDialog.value = true
}

function openEdit(rule: any) {
  editingId.value = rule.id
  form.value = {
    store_id: rule.store_id,
    name: rule.name,
    rule_type: rule.rule_type,
    threshold: rule.threshold,
    channel: rule.channel,
    target: rule.target,
    enabled: rule.enabled,
    description: rule.description,
  }
  showDialog.value = true
}

async function submitForm() {
  if (editingId.value) {
    await alertStore.editRule(editingId.value, form.value)
  } else {
    await alertStore.addRule(form.value)
  }
  if (!alertStore.error) {
    showDialog.value = false
  }
}

async function handleToggle(ruleId: number) {
  await alertStore.toggleRule(ruleId)
}

async function handleDelete(ruleId: number) {
  if (confirm('确定要删除这条告警规则吗？')) {
    await alertStore.removeRule(ruleId)
  }
}

async function handleCheck() {
  await alertStore.runCheck(currentStoreId.value || undefined)
  showCheckResult.value = true
}

async function handleTestAlert() {
  testResult.value = null
  const res = await alertStore.testAlert(testChannel.value, testTarget.value)
  if (res) {
    testResult.value = 'success'
  } else {
    testResult.value = 'failed'
  }
}

function severityClass(s: string) {
  if (s === 'error') return 'tag-danger'
  if (s === 'warning') return 'tag-warn'
  return 'tag-default'
}

function severityLabel(s: string) {
  const m: Record<string, string> = { error: '严重', warning: '警告', info: '信息' }
  return m[s] ?? s
}
</script>

<template>
  <div class="alert-view">
    <!-- 顶部操作栏 -->
    <div class="page-header">
      <h2 class="page-title">告警通知</h2>
      <div class="header-actions">
        <button class="btn btn-outline" @click="handleCheck" :disabled="alertStore.loading">
          手动检查
        </button>
        <button class="btn btn-outline" @click="testDialog = true" :disabled="alertStore.loading">
          发送测试
        </button>
        <button class="btn btn-primary" @click="openCreate">
          新建规则
        </button>
      </div>
    </div>

    <!-- 加载 & 错误 -->
    <div v-if="alertStore.loading" class="loading-bar">加载中...</div>
    <div v-if="alertStore.error" class="error-bar">{{ alertStore.error }}</div>

    <!-- 告警检查结果弹窗 -->
    <div v-if="showCheckResult && alertStore.checkResult" class="modal-overlay" @click.self="showCheckResult = false">
      <div class="modal">
        <div class="modal-header">
          <h3>告警检查结果</h3>
          <button class="btn-close" @click="showCheckResult = false">&times;</button>
        </div>
        <div class="modal-body">
          <p>触发告警数：<strong>{{ alertStore.checkResult.triggered_count }}</strong></p>
          <div v-if="alertStore.checkResult.alerts.length > 0" class="check-results">
            <div v-for="(a, i) in alertStore.checkResult.alerts" :key="i" class="check-item" :class="severityClass(a.severity)">
              <div class="check-item-header">
                <span class="tag" :class="severityClass(a.severity)">{{ severityLabel(a.severity) }}</span>
                <span class="check-item-name">{{ a.rule_name }}</span>
              </div>
              <p class="check-item-msg">{{ a.message }}</p>
              <span class="check-item-time">{{ a.triggered_at }}</span>
            </div>
          </div>
          <p v-else class="empty-hint">所有规则均未触发，一切正常。</p>
        </div>
      </div>
    </div>

    <!-- 测试告警弹窗 -->
    <div v-if="testDialog" class="modal-overlay" @click.self="testDialog = false">
      <div class="modal">
        <div class="modal-header">
          <h3>发送测试告警</h3>
          <button class="btn-close" @click="testDialog = false">&times;</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label class="form-label">通知渠道</label>
            <select v-model="testChannel" class="form-input">
              <option v-for="(label, key) in CHANNEL_LABELS" :key="key" :value="key">{{ label }}</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">接收地址</label>
            <input v-model="testTarget" class="form-input" placeholder="邮箱或 Webhook URL" />
          </div>
          <button class="btn btn-primary" @click="handleTestAlert" :disabled="!testTarget || alertStore.loading">
            发送
          </button>
          <p v-if="testResult === 'success'" class="text-success" style="margin-top: 8px;">测试通知发送成功</p>
          <p v-if="testResult === 'failed'" class="text-danger" style="margin-top: 8px;">测试通知发送失败，请检查配置</p>
        </div>
      </div>
    </div>

    <!-- 新建/编辑规则弹窗 -->
    <div v-if="showDialog" class="modal-overlay" @click.self="showDialog = false">
      <div class="modal">
        <div class="modal-header">
          <h3>{{ editingId ? '编辑规则' : '新建规则' }}</h3>
          <button class="btn-close" @click="showDialog = false">&times;</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label class="form-label">规则名称 *</label>
            <input v-model="form.name" class="form-input" placeholder="如：销量大幅下降" />
          </div>
          <div class="form-group">
            <label class="form-label">规则类型 *</label>
            <select v-model="form.rule_type" class="form-input">
              <option v-for="(label, key) in RULE_TYPE_LABELS" :key="key" :value="key">{{ label }}</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">阈值</label>
            <input v-model.number="form.threshold" type="number" class="form-input" placeholder="如 20 表示 20%" />
          </div>
          <div class="form-group">
            <label class="form-label">通知渠道</label>
            <select v-model="form.channel" class="form-input">
              <option v-for="(label, key) in CHANNEL_LABELS" :key="key" :value="key">{{ label }}</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">接收地址</label>
            <input v-model="form.target" class="form-input" placeholder="邮箱或 Webhook URL" />
          </div>
          <div class="form-group">
            <label class="form-label">描述</label>
            <textarea v-model="form.description" class="form-input" rows="2" placeholder="规则说明（可选）"></textarea>
          </div>
          <div class="form-actions">
            <button class="btn btn-outline" @click="showDialog = false">取消</button>
            <button class="btn btn-primary" @click="submitForm" :disabled="!form.name || alertStore.loading">
              {{ editingId ? '保存' : '创建' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 规则列表 -->
    <section v-if="alertStore.rules.length > 0" class="section-card">
      <div class="table-wrapper">
        <table class="data-table">
          <thead>
            <tr>
              <th>规则名称</th>
              <th>类型</th>
              <th>阈值</th>
              <th>渠道</th>
              <th>接收地址</th>
              <th>状态</th>
              <th>上次触发</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="rule in alertStore.rules" :key="rule.id">
              <td>{{ rule.name }}</td>
              <td><span class="tag tag-default">{{ RULE_TYPE_LABELS[rule.rule_type] || rule.rule_type }}</span></td>
              <td>{{ rule.threshold }}{{ rule.rule_type === 'sales_drop' || rule.rule_type === 'price_change' ? '%' : '' }}</td>
              <td>{{ CHANNEL_LABELS[rule.channel] || rule.channel }}</td>
              <td class="cell-ellipsis">{{ rule.target || '-' }}</td>
              <td>
                <button
                  class="toggle-btn"
                  :class="rule.enabled ? 'toggle-on' : 'toggle-off'"
                  @click="handleToggle(rule.id)"
                  :title="rule.enabled ? '点击禁用' : '点击启用'"
                >
                  {{ rule.enabled ? '启用' : '禁用' }}
                </button>
              </td>
              <td>{{ rule.last_triggered ? new Date(rule.last_triggered).toLocaleString('zh-CN') : '-' }}</td>
              <td class="actions-cell">
                <button class="btn-icon" title="编辑" @click="openEdit(rule)">✏️</button>
                <button class="btn-icon" title="删除" @click="handleDelete(rule.id)">🗑️</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- 空状态 -->
    <section v-else-if="!alertStore.loading" class="empty-state">
      <p>暂无告警规则，点击「新建规则」创建第一条告警</p>
    </section>
  </div>
</template>

<style scoped>
.alert-view {
  max-width: 1200px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-title {
  font-size: 20px;
  font-weight: 700;
  margin: 0;
  color: var(--color-text);
}

.header-actions {
  display: flex;
  gap: 8px;
}

.loading-bar {
  text-align: center;
  padding: 12px;
  color: var(--color-text-tertiary);
  font-size: 14px;
}

.error-bar {
  background: var(--color-danger-bg);
  color: var(--color-danger);
  padding: 10px 14px;
  border-radius: 8px;
  margin-bottom: 16px;
  font-size: 13px;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--color-text-tertiary);
  font-size: 15px;
}

.empty-hint {
  color: var(--color-text-tertiary);
  font-size: 14px;
  text-align: center;
  padding: 20px;
}

.section-card {
  margin-top: 16px;
}

/* 弹窗 */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: var(--color-surface);
  border-radius: 12px;
  width: 90%;
  max-width: 520px;
  max-height: 85vh;
  overflow-y: auto;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--color-border);
}

.modal-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.btn-close {
  background: none;
  border: none;
  font-size: 22px;
  cursor: pointer;
  color: var(--color-text-tertiary);
  padding: 0 4px;
  line-height: 1;
}

.modal-body {
  padding: 20px;
}

/* 表单 */
.form-group {
  margin-bottom: 14px;
}

.form-label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-secondary);
  margin-bottom: 4px;
}

.form-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  font-size: 14px;
  background: var(--color-bg);
  color: var(--color-text);
  box-sizing: border-box;
}

.form-input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px var(--color-primary-bg);
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 16px;
}

/* 按钮 */
.btn {
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid var(--color-border);
  transition: all 0.15s;
}

.btn-primary {
  background: var(--color-primary);
  color: #fff;
  border-color: var(--color-primary);
}

.btn-primary:hover {
  opacity: 0.9;
}

.btn-outline {
  background: transparent;
  color: var(--color-text-secondary);
}

.btn-outline:hover {
  background: var(--color-bg-hover);
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-icon {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 16px;
  padding: 2px 4px;
  border-radius: 4px;
}

.btn-icon:hover {
  background: var(--color-bg-hover);
}

/* 标签 */
.tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.tag-default {
  background: var(--color-bg-hover);
  color: var(--color-text-secondary);
}

.tag-warn {
  background: #fef3c7;
  color: #d97706;
}

.tag-danger {
  background: #fef2f2;
  color: #dc2626;
}

.tag-success {
  background: #ecfdf5;
  color: #059669;
}

/* 切换按钮 */
.toggle-btn {
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  border: none;
  cursor: pointer;
}

.toggle-on {
  background: #ecfdf5;
  color: #059669;
}

.toggle-off {
  background: #f3f4f6;
  color: #9ca3af;
}

/* 检查结果 */
.check-results {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 12px;
}

.check-item {
  padding: 10px 12px;
  border-radius: 8px;
  border-left: 3px solid;
}

.check-item.error {
  border-color: #dc2626;
  background: #fef2f2;
}

.check-item.warning {
  border-color: #d97706;
  background: #fef3c7;
}

.check-item.info {
  border-color: #2563eb;
  background: #eff6ff;
}

.check-item-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.check-item-name {
  font-weight: 600;
  font-size: 14px;
}

.check-item-msg {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin: 4px 0;
}

.check-item-time {
  font-size: 11px;
  color: var(--color-text-tertiary);
}

/* 表格 */
.table-wrapper {
  overflow-x: auto;
  border: 1px solid var(--color-border);
  border-radius: 8px;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.data-table th {
  text-align: left;
  padding: 10px 12px;
  font-weight: 600;
  color: var(--color-text-secondary);
  background: var(--color-bg);
  border-bottom: 1px solid var(--color-border);
  white-space: nowrap;
}

.data-table td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--color-border);
  vertical-align: middle;
}

.data-table tr:last-child td {
  border-bottom: none;
}

.cell-ellipsis {
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.actions-cell {
  white-space: nowrap;
}

.text-success {
  color: var(--color-success) !important;
  font-weight: 600;
}

.text-danger {
  color: var(--color-danger) !important;
  font-weight: 600;
}
</style>
