<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../store/user'
import ScatterPlot from '../components/ScatterPlot.vue'
import RadarChart from '../components/RadarChart.vue'
import { mlApi } from '../api/ml'

const userStore = useUserStore()
const loading = ref(false)
const clusterData = ref(null)
const error = ref('')

const scatterData = computed(() => {
  // 简化：用 head_angle 作为 x，hunchback_score 作为 y 来可视化
  // 实际聚类用的是5维，这里展示2维投影
  return []
})

async function train() {
  loading.value = true
  error.value = ''
  try {
    const uid = userStore.userInfo?.user_id || 1
    const { data } = await mlApi.getCluster(uid, 7)
    clusterData.value = data
  } catch (e) {
    error.value = e?.response?.data?.detail || '训练失败，请确认有足够的历史数据'
    ElMessage.error(error.value)
  } finally {
    loading.value = false
  }
}

const severityColor = (percentage) => {
  if (percentage < 25) return 'success'
  if (percentage < 50) return 'warning'
  return 'danger'
}

const clusterColors = ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de', '#fc8452']

onMounted(train)
</script>

<template>
  <div class="cluster-page">
    <div class="page-header">
      <h3>坐姿模式聚类分析</h3>
      <el-button type="primary" :loading="loading" @click="train">
        {{ clusterData ? '重新分析' : '开始分析' }}
      </el-button>
    </div>

    <!-- 总览 -->
    <el-row :gutter="16" v-if="clusterData && !clusterData.error">
      <el-col :span="6">
        <el-card>
          <template #header>聚类数</template>
          <div class="stat-value">{{ clusterData.k }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card>
          <template #header>样本总数</template>
          <div class="stat-value">{{ clusterData.n_samples }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card>
          <template #header>惯性值</template>
          <div class="stat-value">{{ clusterData.inertia }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card>
          <template #header>模型状态</template>
          <div class="stat-value" style="color: #67c23a">已训练</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 聚类详情 -->
    <el-row :gutter="16" style="margin-top: 16px" v-if="clusterData && clusterData.clusters">
      <el-col
        :span="24 / clusterData.clusters.length"
        v-for="(c, idx) in clusterData.clusters"
        :key="c.cluster_id"
      >
        <el-card
          class="cluster-card"
          :style="{ borderTop: `3px solid ${clusterColors[idx % clusterColors.length]}` }"
        >
          <template #header>
            <div class="cluster-header">
              <span>{{ c.label }}</span>
              <el-tag :type="severityColor(c.percentage)">{{ c.percentage }}%</el-tag>
            </div>
          </template>

          <div class="cluster-detail">
            <div class="cluster-row">记录数：<b>{{ c.count }}</b></div>
            <div class="cluster-row">头部前倾：<b>{{ c.center.head_angle }}°</b></div>
            <div class="cluster-row">高低肩：<b>{{ (c.center.shoulder_diff * 100).toFixed(1) }}%</b></div>
            <div class="cluster-row">驼背比例：<b>{{ (c.center.hunchback_score * 100).toFixed(1) }}%</b></div>
            <div class="cluster-row">身体倾斜：<b>{{ c.center.body_tilt }}°</b></div>
            <div class="cluster-row">圆肩比例：<b>{{ (c.center.round_shoulder * 100).toFixed(1) }}%</b></div>
          </div>

          <div class="cluster-profile">
            <el-tag
              v-for="(v, k) in c.profile"
              :key="k"
              size="small"
              class="profile-tag"
              :type="v.includes('正常') ? 'success' : v.includes('轻微') ? 'warning' : 'danger'"
            >
              {{ v }}
            </el-tag>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 加载中 / 空 -->
    <el-empty v-if="!loading && !clusterData" description="点击「开始分析」进行坐姿模式聚类" />
    <div v-if="loading" style="text-align: center; padding: 40px">
      <el-icon class="is-loading" :size="32"><Loading /></el-icon>
      <p>正在分析坐姿数据...</p>
    </div>
  </div>
</template>

<style scoped>
.cluster-page { padding: 20px; min-height: 100vh; background: #f0f2f5; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-header h3 { margin: 0; }
.stat-value { font-size: 28px; font-weight: 700; text-align: center; color: #303133; }
.cluster-card { margin-bottom: 16px; }
.cluster-header { display: flex; justify-content: space-between; align-items: center; }
.cluster-detail { display: grid; grid-template-columns: 1fr 1fr; gap: 4px 12px; font-size: 13px; }
.cluster-profile { margin-top: 12px; display: flex; flex-wrap: wrap; gap: 6px; }
.profile-tag { font-size: 12px; }
</style>
