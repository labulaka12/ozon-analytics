<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { BarChart as EBarChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([
  EBarChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  CanvasRenderer,
])

const props = withDefaults(defineProps<{
  title?: string
  xData: string[]
  series: { name: string; data: number[]; color?: string }[]
  height?: string
  horizontal?: boolean
}>(), {
  title: '',
  height: '340px',
  horizontal: false,
})

const option = computed(() => ({
  title: props.title ? {
    text: props.title,
    left: 0,
    textStyle: { fontSize: 14, fontWeight: 600, color: '#1e293b' },
  } : undefined,
  tooltip: {
    trigger: 'axis',
    axisPointer: { type: 'shadow' },
    backgroundColor: 'rgba(255,255,255,0.96)',
    borderColor: '#e2e8f0',
    textStyle: { color: '#1e293b', fontSize: 13 },
  },
  grid: {
    left: props.horizontal ? 100 : 60,
    right: 20,
    top: props.title ? 40 : 20,
    bottom: 36,
  },
  xAxis: {
    type: props.horizontal ? 'value' : 'category',
    data: props.horizontal ? undefined : props.xData,
    axisLine: { lineStyle: { color: '#e2e8f0' } },
    axisTick: { show: false },
    axisLabel: { color: '#64748b', fontSize: 11 },
  },
  yAxis: {
    type: props.horizontal ? 'category' : 'value',
    data: props.horizontal ? props.xData : undefined,
    axisLine: { show: false },
    axisTick: { show: false },
    splitLine: props.horizontal ? undefined : { lineStyle: { color: '#f1f5f9' } },
    axisLabel: { color: '#64748b', fontSize: 11 },
  },
  series: props.series.map((s) => ({
    name: s.name,
    type: 'bar',
    data: s.data,
    barMaxWidth: 36,
    itemStyle: {
      color: s.color,
      borderRadius: props.horizontal ? [0, 4, 4, 0] : [4, 4, 0, 0],
    },
  })),
}))
</script>

<template>
  <div class="chart-container">
    <VChart :option="option" :style="{ height }" autoresize />
  </div>
</template>
