<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { PieChart as EPieChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([
  EPieChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  CanvasRenderer,
])

const props = withDefaults(defineProps<{
  title?: string
  data: { name: string; value: number; color?: string }[]
  height?: string
  roseType?: boolean
}>(), {
  title: '',
  height: '340px',
  roseType: false,
})

const defaultColors = ['#2563eb', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899', '#f97316']

const option = computed(() => ({
  title: props.title ? {
    text: props.title,
    left: 0,
    textStyle: { fontSize: 14, fontWeight: 600, color: '#1e293b' },
  } : undefined,
  tooltip: {
    trigger: 'item',
    backgroundColor: 'rgba(255,255,255,0.96)',
    borderColor: '#e2e8f0',
    textStyle: { color: '#1e293b', fontSize: 13 },
    formatter: (params: any) => {
      const val = typeof params.value === 'number' ? params.value.toLocaleString('zh-CN', { minimumFractionDigits: 2 }) : params.value
      return `${params.name}<br/>¥${val} (${params.percent}%)`
    },
  },
  legend: {
    bottom: 0,
    textStyle: { fontSize: 12, color: '#64748b' },
  },
  series: [{
    type: 'pie',
    radius: props.roseType ? ['20%', '65%'] : ['40%', '70%'],
    center: ['50%', '48%'],
    roseType: props.roseType ? 'radius' : undefined,
    itemStyle: {
      borderRadius: 6,
      borderColor: '#fff',
      borderWidth: 2,
    },
    label: {
      show: true,
      formatter: '{b}: {d}%',
      fontSize: 12,
      color: '#64748b',
    },
    data: props.data.map((d, i) => ({
      ...d,
      itemStyle: d.color ? { color: d.color } : { color: defaultColors[i % defaultColors.length] },
    })),
  }],
}))
</script>

<template>
  <div class="chart-container">
    <VChart :option="option" :style="{ height }" autoresize />
  </div>
</template>
