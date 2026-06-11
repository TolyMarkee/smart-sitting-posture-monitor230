<script setup>
import { computed } from 'vue'

const props = defineProps({
  issues: { type: Array, default: () => [] },
  headAngle: { type: Number, default: 0 },
  shoulderDiff: { type: Number, default: 0 },
  hunchbackScore: { type: Number, default: 0 },
  bodyTilt: { type: Number, default: 0 },
  roundShoulder: { type: Number, default: 0 },
  confidence: { type: Number, default: 0 },
})

const severityColors = {
  normal: '#67c23a',
  mild: '#e6a23c',
  moderate: '#f56c6c',
  severe: '#ff0000',
}

const overallSeverity = computed(() => {
  if (!props.issues || props.issues.length === 0) return 'normal'
  const order = ['normal', 'mild', 'moderate', 'severe']
  let worst = 0
  props.issues.forEach((i) => {
    const idx = order.indexOf(i.severity)
    if (idx > worst) worst = idx
  })
  return order[worst]
})

const statusText = computed(() => {
  const map = { normal: '坐姿良好', mild: '轻微异常', moderate: '需要注意', severe: '严重警告' }
  return map[overallSeverity.value] || '未知'
})

const statusColor = computed(() => {
  return severityColors[overallSeverity.value] || '#909399'
})

function severityTag(severity) {
  const map = { normal: '正常', mild: '轻度', moderate: '中度', severe: '重度' }
  return map[severity] || '未知'
}

// 指标严重程度颜色（与K230 LCD一致）
function metricColor(val, thresholds) {
  if (val >= thresholds[2]) return '#ff0000'  // 重度
  if (val >= thresholds[1]) return '#f56c6c'  // 中度
  if (val >= thresholds[0]) return '#e6a23c'  // 轻度
  return '#67c23a'  // 正常
}

function issueIcon(type) {
  const map = {
    forward_head: '👤',
    high_low_shoulder: '↕',
    hunched_back: '🔻',
    body_tilt: '↗',
    round_shoulder: '🔘',
  }
  return map[type] || '⚠'
}
</script>

<template>
  <div class="indicator-container">
    <!-- 综合状态卡片 -->
    <el-card class="status-card" :style="{ borderColor: statusColor }">
      <div class="status-header">
        <span class="status-dot" :style="{ background: statusColor }"></span>
        <span class="status-label">当前状态</span>
      </div>
      <div class="status-main" :style="{ color: statusColor }">{{ statusText }}</div>
      <div class="status-sub" v-if="issues.length > 0">
        {{ issues.length }} 项体态问题
      </div>
      <div class="status-sub" v-else>未检测到异常</div>
    </el-card>

    <!-- 检测到的具体问题 -->
    <div class="issues-list" v-if="issues.length > 0">
      <div
        v-for="issue in issues"
        :key="issue.type"
        class="issue-item"
      >
        <span class="issue-icon">{{ issueIcon(issue.type) }}</span>
        <div class="issue-info">
          <span class="issue-name">{{ issue.name }}</span>
          <span class="issue-desc">{{ issue.description }}</span>
        </div>
        <el-tag
          :type="issue.severity === 'severe' ? 'danger' : issue.severity === 'moderate' ? 'warning' : 'info'"
          size="small"
        >
          {{ severityTag(issue.severity) }}
        </el-tag>
      </div>
    </div>

    <!-- 5项指标 -->
    <el-card class="metrics-card">
      <template #header>详细指标</template>
      <div class="metric-row">
        <span>头部前倾角度</span>
        <span :style="{ color: metricColor(headAngle, [40,50,60]), fontWeight: '700' }">{{ headAngle.toFixed(1) }}°</span>
      </div>
      <div class="metric-row">
        <span>高低肩比例</span>
        <span :style="{ color: metricColor(shoulderDiff*100, [5,8,12]), fontWeight: '700' }">{{ (shoulderDiff * 100).toFixed(1) }}%</span>
      </div>
      <div class="metric-row">
        <span>驼背前倾比例</span>
        <span :style="{ color: metricColor(hunchbackScore*100, [30,50,70]), fontWeight: '700' }">{{ (hunchbackScore * 100).toFixed(1) }}%</span>
      </div>
      <div class="metric-row">
        <span>身体倾斜角度</span>
        <span :style="{ color: metricColor(bodyTilt, [5,10,15]), fontWeight: '700' }">{{ bodyTilt.toFixed(1) }}°</span>
      </div>
      <div class="metric-row">
        <span>圆肩比例</span>
        <span :style="{ color: metricColor(roundShoulder*100, [20,30,50]), fontWeight: '700' }">{{ (roundShoulder * 100).toFixed(1) }}%</span>
      </div>
      <div class="metric-row">
        <span>检测置信度</span>
        <span>{{ (confidence * 100).toFixed(0) }}%</span>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.indicator-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.status-card {
  text-align: center;
  border-width: 2px;
}

.status-header {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin-bottom: 8px;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}

.status-label {
  font-size: 14px;
  color: #909399;
}

.status-main {
  font-size: 32px;
  font-weight: 700;
}

.status-sub {
  font-size: 13px;
  color: #909399;
  margin-top: 4px;
}

.issues-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.issue-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  background: #f5f7fa;
  border-radius: 8px;
}

.issue-icon {
  font-size: 20px;
}

.issue-info {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.issue-name {
  font-size: 14px;
  font-weight: 600;
}

.issue-desc {
  font-size: 12px;
  color: #909399;
}

.metrics-card {
  font-size: 14px;
}

.metric-row {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  border-bottom: 1px solid #f0f0f0;
}

.metric-row:last-child {
  border-bottom: none;
}
</style>
