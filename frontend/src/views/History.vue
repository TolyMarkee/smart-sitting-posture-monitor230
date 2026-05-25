<script setup>
import { ref, onMounted, watch, computed } from 'vue'
import { usePostureStore } from '../store/posture'
import { useUserStore } from '../store/user'
import LineChart from '../components/LineChart.vue'

const postureStore = usePostureStore()
const userStore = useUserStore()
const range = ref('7d')
const loading = ref(false)

const ranges = {
  '1d': 1,
  '7d': 7,
  '30d': 30,
}

// 从记录中提取时间轴和各项指标
const xData = computed(() =>
  postureStore.history.map((r) => {
    const d = new Date(r.created_at)
    return d.toLocaleString('zh-CN', {
      month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit',
    })
  })
)

const headAngleSeries = computed(() => [{
  name: '头部前倾角度',
  data: postureStore.history.map((r) => r.head_angle),
}])

const shoulderDiffSeries = computed(() => [{
  name: '高低肩比例',
  data: postureStore.history.map((r) => +(r.shoulder_diff * 100).toFixed(1)),
}])

const hunchbackSeries = computed(() => [{
  name: '驼背前倾比例',
  data: postureStore.history.map((r) => +(r.hunchback_score * 100).toFixed(1)),
}])

const bodyTiltSeries = computed(() => [{
  name: '身体倾斜',
  data: postureStore.history.map((r) => r.body_tilt),
}])

const roundShoulderSeries = computed(() => [{
  name: '圆肩比例',
  data: postureStore.history.map((r) => +(r.round_shoulder * 100).toFixed(1)),
}])

async function loadHistory() {
  loading.value = true
  const days = ranges[range.value] || 7
  const uid = userStore.userInfo?.user_id
  if (!uid) return
  const end = new Date().toISOString()
  const start = new Date(Date.now() - days * 86400000).toISOString()
  await postureStore.fetchHistory(uid, start, end)
  loading.value = false
}

watch(range, loadHistory)
onMounted(loadHistory)
</script>

<template>
  <div class="history-page">
    <div class="page-header">
      <h3>历史趋势</h3>
      <div class="header-right">
        <span v-if="loading">加载中...</span>
        <span v-else-if="postureStore.history.length > 0" class="record-hint">
          共 {{ postureStore.history.length }} 条记录
        </span>
        <el-radio-group v-model="range" size="small">
          <el-radio-button value="1d">近1天</el-radio-button>
          <el-radio-button value="7d">近7天</el-radio-button>
          <el-radio-button value="30d">近30天</el-radio-button>
        </el-radio-group>
      </div>
    </div>

    <!-- 无数据提示 -->
    <el-empty v-if="!loading && postureStore.history.length === 0" description="暂无数据，请先上传坐姿记录">
      <el-button type="primary" @click="loadHistory">刷新</el-button>
    </el-empty>

    <!-- 图表网格 -->
    <div v-else class="charts-grid">
      <el-card>
        <LineChart
          title="头部前倾角度 (°)"
          :x-data="xData"
          :series="headAngleSeries"
          y-name="度"
        />
      </el-card>
      <el-card>
        <LineChart
          title="高低肩比例 (%)"
          :x-data="xData"
          :series="shoulderDiffSeries"
          y-name="%"
        />
      </el-card>
      <el-card>
        <LineChart
          title="驼背前倾比例 (%)"
          :x-data="xData"
          :series="hunchbackSeries"
          y-name="%"
        />
      </el-card>
      <el-card>
        <LineChart
          title="身体倾斜角度 (°)"
          :x-data="xData"
          :series="bodyTiltSeries"
          y-name="度"
        />
      </el-card>
      <el-card>
        <LineChart
          title="圆肩比例 (%)"
          :x-data="xData"
          :series="roundShoulderSeries"
          y-name="%"
        />
      </el-card>
    </div>

    <!-- 返回顶部 -->
    <el-backtop target=".history-page" />
  </div>
</template>

<style scoped>
.history-page {
  padding: 20px;
  min-height: 100vh;
  background: #f0f2f5;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h3 {
  margin: 0;
  font-size: 18px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.record-hint {
  font-size: 13px;
  color: #909399;
}

.charts-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

@media (max-width: 1200px) {
  .charts-grid {
    grid-template-columns: 1fr;
  }
}
</style>
