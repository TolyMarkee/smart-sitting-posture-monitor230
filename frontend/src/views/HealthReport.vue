<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../store/user'
import { usePostureStore } from '../store/posture'
import { mlApi } from '../api/ml'
import LineChart from '../components/LineChart.vue'

const userStore = useUserStore()
const postureStore = usePostureStore()
const loading = ref(false)
const healthScore = ref(null)
const forecast = ref(null)
const cluster = ref(null)

async function loadReport() {
  loading.value = true
  try {
    const uid = userStore.userInfo?.user_id || 1
    const { data } = await mlApi.getOverallReport(uid, 7)
    healthScore.value = data.health_score
    forecast.value = data.forecast
    cluster.value = data.cluster
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '加载失败，请确认已有足够的历史数据')
  } finally {
    loading.value = false
  }
}

const forecastX = computed(() =>
  forecast.value?.predictions?.map((_, i) => `+${i + 1}`) || []
)

const forecastHeadAngle = computed(() => [{
  name: '头部前倾预测',
  data: forecast.value?.predictions?.map((p) => p.head_angle) || [],
}])

const scoreColor = computed(() => {
  const s = healthScore.value?.score || 100
  if (s >= 90) return '#67c23a'
  if (s >= 75) return '#e6a23c'
  if (s >= 60) return '#f56c6c'
  return '#ff0000'
})

const nowStr = computed(() => {
  return new Date().toLocaleString('zh-CN')
})

function exportPDF() {
  ElMessage.success('正在生成PDF报告...')
  setTimeout(() => window.print(), 300)
}

onMounted(loadReport)
</script>

<template>
  <div class="report-page" id="report-content">
    <!-- 操作栏（打印时隐藏） -->
    <div class="page-header no-print">
      <h3>健康报告</h3>
      <div class="header-actions">
        <el-button :loading="loading" @click="loadReport">刷新数据</el-button>
        <el-button type="primary" @click="exportPDF" :disabled="!healthScore">
          导出 PDF 报告
        </el-button>
      </div>
    </div>

    <!-- 打印时显示的标题 -->
    <div class="print-only report-print-header">
      <h1>智能坐姿监测系统 — 健康报告</h1>
      <p>生成时间：{{ nowStr }}</p>
    </div>

    <div v-if="healthScore">
      <!-- 健康评分 -->
      <el-row :gutter="16">
        <el-col :span="8">
          <el-card :style="{ borderTop: `3px solid ${scoreColor}` }" class="score-section">
            <template #header>健康评分</template>
            <div class="score-big" :style="{ color: scoreColor }">
              {{ healthScore.score }}
              <span class="score-unit">分</span>
            </div>
            <div class="grade-text">{{ healthScore.grade }}</div>

            <div v-if="healthScore.deductions && Object.keys(healthScore.deductions).length > 0">
              <div class="deductions">
                <div v-for="(val, key) in healthScore.deductions" :key="key" class="deduction-item">
                  <span>{{ key }}</span>
                  <span class="deduction-val">-{{ val }}</span>
                </div>
                <div class="deduction-total">总扣分：-{{ healthScore.total_deduction }}</div>
              </div>
            </div>
            <div v-else class="no-deduction">各项指标正常</div>

            <!-- 说明 -->
            <div class="score-desc print-only">
              <p><strong>评分说明：</strong>满分 100 分，基于头部前倾、高低肩、驼背含胸、身体倾斜、圆肩五项指标综合评定。分数越高，坐姿越健康。</p>
            </div>
          </el-card>
        </el-col>

        <!-- 聚类 + 解读 -->
        <el-col :span="16">
          <el-card v-if="cluster && cluster.clusters">
            <template #header>坐姿模式分布</template>
            <el-row :gutter="12">
              <el-col
                :span="Math.min(12, 24 / cluster.clusters.length)"
                v-for="c in cluster.clusters"
                :key="c.cluster_id"
              >
                <div class="mode-card">
                  <div class="mode-label">{{ c.label }}</div>
                  <el-progress
                    :percentage="c.percentage"
                    :color="c.percentage > 50 ? '#f56c6c' : c.percentage > 25 ? '#e6a23c' : '#67c23a'"
                    :stroke-width="14"
                  />
                  <div class="mode-count">{{ c.count }} 条记录</div>
                </div>
              </el-col>
            </el-row>

            <!-- 各模式详情 -->
            <div class="cluster-detail-table print-only">
              <table>
                <thead>
                  <tr><th>模式</th><th>占比</th><th>头部前倾</th><th>高低肩</th><th>驼背</th><th>身体倾斜</th><th>圆肩</th></tr>
                </thead>
                <tbody>
                  <tr v-for="c in cluster.clusters" :key="c.cluster_id">
                    <td>{{ c.label }}</td>
                    <td>{{ c.percentage }}%</td>
                    <td>{{ c.center.head_angle }}°</td>
                    <td>{{ (c.center.shoulder_diff * 100).toFixed(1) }}%</td>
                    <td>{{ (c.center.hunchback_score * 100).toFixed(1) }}%</td>
                    <td>{{ c.center.body_tilt }}°</td>
                    <td>{{ (c.center.round_shoulder * 100).toFixed(1) }}%</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 趋势预测 -->
      <el-card v-if="forecast && forecast.predictions" style="margin-top: 16px">
        <template #header>未来趋势预测（LSTM 模型）</template>
        <div class="no-print">
          <LineChart
            title="头部前倾角度预测"
            :x-data="forecastX"
            :series="forecastHeadAngle"
            y-name="度"
            height="300px"
          />
        </div>
        <div class="print-only">
          <table>
            <thead><tr><th>预测步数</th><th>头部前倾</th><th>高低肩</th><th>驼背</th><th>倾斜</th><th>圆肩</th></tr></thead>
            <tbody>
              <tr v-for="p in forecast.predictions.slice(0, 12)" :key="p.step">
                <td>第 {{ p.step }} 步</td>
                <td>{{ p.head_angle }}°</td>
                <td>{{ (p.shoulder_diff * 100).toFixed(1) }}%</td>
                <td>{{ (p.hunchback_score * 100).toFixed(1) }}%</td>
                <td>{{ p.body_tilt }}°</td>
                <td>{{ (p.round_shoulder * 100).toFixed(1) }}%</td>
              </tr>
            </tbody>
          </table>
        </div>
      </el-card>

      <!-- 建议 -->
      <el-card style="margin-top: 16px" class="print-only">
        <template #header>改善建议</template>
        <ul class="advice-list">
          <li v-if="(healthScore?.deductions || {})['头部前倾']">头部前倾：收下巴、将显示器调高至视线水平、保持耳垂与肩峰在一条垂线上。</li>
          <li v-if="(healthScore?.deductions || {})['驼背含胸']">驼背含胸：挺胸收腹、椅子靠背调至100-110°、每隔30分钟做扩胸运动。</li>
          <li v-if="(healthScore?.deductions || {})['高低肩']">高低肩：注意左右均衡用力、避免单肩背包、可做耸肩放松训练。</li>
          <li v-if="(healthScore?.deductions || {})['身体倾斜']">身体倾斜：调整坐姿使重心居中、双脚平放地面、椅面保持水平。</li>
          <li v-if="(healthScore?.deductions || {})['圆肩']">圆肩：加强背阔肌和菱形肌训练、做YTWL肩部训练、避免长时间含胸。</li>
          <li v-if="!healthScore?.deductions || Object.keys(healthScore.deductions).length === 0">
            各项指标均在正常范围内，请继续保持良好坐姿习惯。
          </li>
        </ul>
      </el-card>

      <div class="print-only report-footer">
        <p>本报告由智能坐姿监测系统自动生成 | 仅供参考，不构成医学诊断</p>
      </div>
    </div>

    <el-empty v-if="!loading && !healthScore" description="暂无数据，请确保已有足够的历史记录" />
  </div>
</template>

<style scoped>
.report-page { padding: 20px; min-height: 100vh; background: #f0f2f5; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-header h3 { margin: 0; }
.header-actions { display: flex; gap: 8px; }

.score-big { font-size: 64px; font-weight: 700; text-align: center; }
.score-unit { font-size: 24px; font-weight: 400; }
.grade-text { text-align: center; font-size: 18px; color: #909399; margin: 8px 0 16px; }
.deductions { margin-top: 12px; font-size: 14px; }
.deduction-item { display: flex; justify-content: space-between; padding: 4px 0; border-bottom: 1px solid #f0f0f0; }
.deduction-val { color: #f56c6c; font-weight: 600; }
.deduction-total { margin-top: 8px; text-align: right; color: #f56c6c; font-weight: 700; }
.no-deduction { text-align: center; color: #67c23a; margin-top: 16px; }
.mode-card { padding: 4px 0; }
.mode-label { font-size: 13px; margin-bottom: 4px; }
.mode-count { font-size: 11px; color: #909399; text-align: center; margin-top: 2px; }
.score-desc { margin-top: 16px; font-size: 13px; color: #606266; line-height: 1.6; }

/* 表格 */
table { width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 8px; }
th, td { padding: 8px 10px; border: 1px solid #e4e7ed; text-align: center; }
th { background: #f5f7fa; font-weight: 600; }

.advice-list { padding-left: 20px; line-height: 2; font-size: 14px; color: #303133; }

/* 打印控制 */
.print-only { display: none; }
.report-print-header { text-align: center; margin-bottom: 24px; }
.report-print-header h1 { font-size: 22px; margin-bottom: 4px; }
.report-print-header p { font-size: 13px; color: #909399; }
.report-footer { text-align: center; margin-top: 24px; font-size: 12px; color: #c0c4cc; }

@media print {
  .no-print { display: none !important; }
  .print-only { display: block !important; }
  .report-page { background: #fff !important; padding: 20px !important; }
  .el-card { break-inside: avoid; box-shadow: none !important; border: 1px solid #e4e7ed !important; }
  .score-big { font-size: 48px !important; }
  body { background: #fff !important; }
}
</style>
