<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  data: { type: Array, default: () => [] },
  title: { type: String, default: '' },
  xLabel: { type: String, default: '' },
  yLabel: { type: String, default: '' },
  height: { type: String, default: '400px' },
})

const chartRef = ref(null)
let chart = null

function initChart() {
  if (!chartRef.value) return
  if (chart) chart.dispose()
  chart = echarts.init(chartRef.value)

  const clusters = {}
  props.data.forEach((d) => {
    const cid = d.cluster_id ?? 0
    if (!clusters[cid]) clusters[cid] = []
    clusters[cid].push(d)
  })

  const colors = ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de']
  const series = Object.keys(clusters).map((cid) => ({
    name: `模式 ${parseInt(cid) + 1}`,
    type: 'scatter',
    data: clusters[cid].map((d) => [d.x, d.y]),
    symbolSize: 8,
    itemStyle: { color: colors[parseInt(cid) % colors.length] },
  }))

  chart.setOption({
    title: { text: props.title, left: 'center', textStyle: { fontSize: 14 } },
    tooltip: { formatter: (p) => `聚类${parseInt(p.seriesIndex) + 1}<br/>${p.value[0]}, ${p.value[1]}` },
    legend: { bottom: 0 },
    grid: { left: 50, right: 20, top: 40, bottom: 40 },
    xAxis: { type: 'value', name: props.xLabel },
    yAxis: { type: 'value', name: props.yLabel },
    series,
  })
}

let timer = null
function handleResize() { clearTimeout(timer); timer = setTimeout(() => chart?.resize(), 150) }

watch(() => props.data, initChart, { deep: true })
onMounted(() => { initChart(); window.addEventListener('resize', handleResize) })
onUnmounted(() => { window.removeEventListener('resize', handleResize); chart?.dispose() })
</script>

<template>
  <div ref="chartRef" :style="{ width: '100%', height }"></div>
</template>
