<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  title: { type: String, default: '' },
  xData: { type: Array, default: () => [] },
  series: { type: Array, default: () => [] },
  yName: { type: String, default: '' },
  height: { type: String, default: '320px' },
})

const chartRef = ref(null)
let chart = null

function initChart() {
  if (!chartRef.value) return
  if (chart) chart.dispose()

  chart = echarts.init(chartRef.value)
  const option = {
    title: {
      text: props.title,
      textStyle: { fontSize: 14, fontWeight: 600 },
      left: 'center',
    },
    tooltip: { trigger: 'axis' },
    legend: {
      data: props.series.map((s) => s.name),
      bottom: 0,
    },
    grid: { left: 60, right: 30, top: 40, bottom: 40 },
    xAxis: {
      type: 'category',
      data: props.xData,
      axisLabel: { rotate: 30, fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      name: props.yName,
      nameTextStyle: { fontSize: 12 },
    },
    series: props.series.map((s) => ({
      name: s.name,
      type: 'line',
      data: s.data,
      smooth: true,
      symbol: 'none',
      lineStyle: { width: 2 },
    })),
  }
  chart.setOption(option)
}

let resizeTimer = null
function handleResize() {
  clearTimeout(resizeTimer)
  resizeTimer = setTimeout(() => chart?.resize(), 150)
}

watch(() => [props.xData, props.series], initChart, { deep: true })

onMounted(() => {
  initChart()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
})
</script>

<template>
  <div ref="chartRef" :style="{ width: '100%', height }"></div>
</template>
