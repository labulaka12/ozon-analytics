<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart as ELineChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  DataZoomComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([
  ELineChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  DataZoomComponent,
  CanvasRenderer,
])

const props = withDefaults(defineProps<{
  title?: string
  xData: string[]
  series: { name: string; data: number[]; color?: string }[]
  height?: string
  smooth?: boolean
  areaStyle?: boolean
  showDataZoom?: boolean
}>(), {
  title: '',
  height: '340px',
  smooth: true,
  areaStyle: false,
  showDataZoom: false,
})

const option = computed(() => ({
  title: props.title ? {
    text: props.title,
    left: 0,
    textStyle: { fontSize: 14, fontWeight: 600, color: '#1e293b' },
  } : undefined,
  tooltip: {
    trigger: 'axis',
    backgroundColor: 'rgba(255,255,255,0.96)',
    borderColor: '#e2e8f0',
    textStyle: { color: '#1e293b', fontSize: 13 },
  },
  legend: {
    bottom: props.showDataZoom ? 36 : 0,
    textStyle: { fontSize: 12, color: '#64748b' },
  },
  grid: {
    left: 60,
    right: 20,
    top: props.title ? 40 : 20,
    bottom: props.showDataZoom ? 60 : 36,
  },
  xAxis: {
    type: 'category',
    data: props.xData,
    axisLine: { lineStyle: { color: '#e2e8f0' } },
    axisTick: { show: false },
    axisLabel: { color: '#64748b', fontSize: 11 },
  },
  yAxis: {
    type: 'value',
    axisLine: { show: false },
    axisTick: { show: false },
    splitLine: { lineStyle: { color: '#f1f5f9' } },
    axisLabel: { color: '#64748b', fontSize: 11 },
  },
  dataZoom: props.showDataZoom ? [{
    type: 'inside',
    start: 0,
    end: 100,
  }] : undefined,
  series: props.series.map((s) => ({
    name: s.name,
    type: 'line',
    data: s.data,
    smooth: props.smooth,
    symbol: 'circle',
    symbolSize: 6,
    lineStyle: { width: 2.5, color: s.color },
    itemStyle: { color: s.color },
    areaStyle: props.areaStyle ? {
      color: {
        type: 'linear',
        x: 0, y: 0, x2: 0, y2: 1,
        colorStops: [
          { offset: 0, color: s.color ? s.color + '30' : '#2563eb30' },
          { offset: 1, color: s.color ? s.color + '05' : '#2563eb05' },
        ],
      },
    } : undefined,
  })),
}))
</script>

<template>
  <div class="chart-container">
    <VChart :option="option" :style="{ height }" autoresize />
  </div>
</template>
