<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElNotification, ElMessageBox } from 'element-plus'
import { usePostureStore } from '../store/posture'
import { useUserStore } from '../store/user'
import request from '../api/request'
import RealTimeIndicator from '../components/RealTimeIndicator.vue'

const router = useRouter()
const route = useRoute()
const postureStore = usePostureStore()
const userStore = useUserStore()
const lastUpdate = ref('')
const refreshTime = ref('')
const currentPath = computed(() => route.path)
const pollCount = ref(0)

// ── 当前时间 ──
const nowStr = ref('')
const dateStr = ref('')
const weekdayStr = ref('')
const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 6) return '夜深了'
  if (h < 9) return '早上好'
  if (h < 12) return '上午好'
  if (h < 14) return '中午好'
  if (h < 18) return '下午好'
  return '晚上好'
})

function updateClock() {
  const d = new Date()
  nowStr.value = d.toLocaleTimeString('zh-CN', { hour12: false })
  dateStr.value = d.toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' })
  const wd = ['日', '一', '二', '三', '四', '五', '六']
  weekdayStr.value = '星期' + wd[d.getDay()]
}

// ── 打卡统计 ──
const dailyStats = ref([])
const streakDays = ref(0)

async function loadStats() {
  const uid = userStore.userInfo?.user_id
  if (!uid) return
  try {
    const end = new Date().toISOString().slice(0, 10)
    const start = new Date(Date.now() - 14 * 86400000).toISOString().slice(0, 10)
    const { data } = await postureStore.fetchDailySummary(uid, start, end)
    dailyStats.value = data.stats || []
    let streak = 0
    for (const s of [...dailyStats.value].reverse()) {
      if (s.bad_posture_ratio !== null && s.bad_posture_ratio < 0.3) streak++
      else break
    }
    streakDays.value = streak
  } catch { /* ignore */ }
}

function dayClass(day) {
  if (!day || day.bad_posture_ratio === null) return 'day-none'
  const r = day.bad_posture_ratio
  if (r < 0.15) return 'day-good'
  if (r < 0.30) return 'day-ok'
  if (r < 0.50) return 'day-bad'
  return 'day-warn'
}

// ── 日历点击详情 ──
const dayDetail = ref(null)
const dayDetailLoading = ref(false)
const showDayDetail = ref(false)
async function openDayDetail(day) {
  if (!day || !day.stat_date) return
  showDayDetail.value = true
  dayDetailLoading.value = true
  try {
    const uid = userStore.userInfo?.user_id
    const resp = await request.get('/api/v1/data/history', {
      params: {
        user_id: uid,
        start: `${day.stat_date}T00:00:00`,
        end: `${day.stat_date}T23:59:59`,
        limit: 500,
      },
    })
    const records = resp.data.records || []
    const badCount = records.filter(r => r.posture_label !== 'normal').length
    dayDetail.value = {
      date: day.stat_date,
      total: records.length,
      badCount,
      badRatio: records.length ? (badCount / records.length * 100).toFixed(1) : 0,
      avgHead: records.length ? (records.reduce((s, r) => s + (r.head_angle || 0), 0) / records.length).toFixed(1) : 0,
      records: records.slice(0, 20),
    }
  } catch { dayDetail.value = null } finally { dayDetailLoading.value = false }
}

// ── 不良坐姿检测 ──
const ALERT_THRESHOLD = 40
const badStreak = ref(0)
const showAlert = ref(false)
const notificationGranted = ref(false)

function formatTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return `${d.toLocaleDateString('zh-CN')} ${d.toLocaleTimeString('zh-CN', { hour12: false })}`
}

function isPostureBad() {
  const label = postureStore.latest?.posture_label || ''
  return label !== 'normal' && label !== ''
}

function sendBrowserNotification() {
  if (!notificationGranted.value) return
  try {
    new Notification('坐姿提醒', {
      body: '持续不良坐姿超过 2 分钟，请注意调整！',
      icon: '/favicon.svg', tag: 'posture-warning', requireInteraction: true,
    })
  } catch { /* ignore */ }
}

function showInAppWarning() {
  ElNotification({
    title: '坐姿警告', type: 'warning', duration: 0, position: 'top-right', showClose: true,
    message: '持续不良坐姿超过 2 分钟！\n建议：挺直腰背、收回下巴、双肩放松。',
  })
}

async function refresh() {
  const uid = userStore.userInfo?.user_id
  if (!uid) return
  refreshTime.value = new Date().toLocaleTimeString('zh-CN', { hour12: false })
  pollCount.value++
  try {
    const data = await postureStore.fetchLatest(uid)
    if (data.record) {
      lastUpdate.value = formatTime(data.record.created_at)
      if (isPostureBad()) {
        badStreak.value++
        if (badStreak.value === ALERT_THRESHOLD) {
          showAlert.value = true
          sendBrowserNotification()
          showInAppWarning()
        }
      } else {
        if (badStreak.value >= ALERT_THRESHOLD) showAlert.value = false
        badStreak.value = 0
      }
    }
  } catch { /* ignore */ }
}

function dismissAlert() { showAlert.value = false; badStreak.value = 0 }

async function requestNotification() {
  if (!('Notification' in window)) return
  if (Notification.permission === 'granted') notificationGranted.value = true
  else if (Notification.permission !== 'denied') {
    notificationGranted.value = (await Notification.requestPermission()) === 'granted'
  }
}

function handleLogout() { userStore.logout(); router.push('/login') }

// ── 生成模拟数据 ──
const genLoading = ref(false)
async function generateDemoData() {
  const uid = userStore.userInfo?.user_id
  if (!uid) return
  genLoading.value = true
  try {
    const resp = await request.post('/api/v1/data/generate-demo', null, { params: { user_id: uid, days: 3 } })
    ElNotification({ title: '数据已生成', message: `已生成 ${resp.data.created} 条模拟数据`, type: 'success' })
    refresh()
    loadStats()
  } catch {
    ElNotification({ title: '生成失败', message: '请确认后端已启动', type: 'error' })
  } finally { genLoading.value = false }
}

// ── 天气 ──
const weather = ref(null)
async function loadWeather() {
  try {
    const resp = await request.get('/api/v1/data/weather')
    weather.value = resp.data
  } catch { /* ignore */ }
}

let timer = null, clockTimer = null
onMounted(() => {
  updateClock()
  refresh()
  loadStats()
  loadWeather()
  requestNotification()
  timer = setInterval(refresh, 3000)
  clockTimer = setInterval(updateClock, 1000)
})
onUnmounted(() => {
  clearInterval(timer)
  clearInterval(clockTimer)
})
</script>

<template>
  <div class="dashboard">
    <!-- 顶部 -->
    <div class="dash-top">
      <div class="top-brand">
        <div class="brand-logo">
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.8">
            <circle cx="12" cy="7" r="4"/><path d="M5.5 21c0-4.4 3.1-8 6.5-8s6.5 3.6 6.5 8"/>
          </svg>
        </div>
        <span class="brand-name">智能坐姿监测</span>
      </div>
      <div class="top-nav">
        <router-link to="/dashboard" :class="{ active: currentPath === '/dashboard' }">实时看板</router-link>
        <router-link to="/history" :class="{ active: currentPath === '/history' }">历史趋势</router-link>
        <router-link to="/cluster" :class="{ active: currentPath === '/cluster' }">聚类分析</router-link>
        <router-link to="/health-report" :class="{ active: currentPath === '/health-report' }">健康报告</router-link>
        <router-link to="/assistant" :class="{ active: currentPath === '/assistant' }">智能客服</router-link>
        <router-link to="/activities" :class="{ active: currentPath === '/activities' }">活动</router-link>
      </div>
      <div class="top-right">
        <span class="top-time">{{ nowStr }}</span>
        <el-dropdown trigger="click">
          <span class="user-name">{{ userStore.userInfo?.username || '用户' }} ▾</span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="router.push('/profile')">个人中心</el-dropdown-item>
              <el-dropdown-item divided @click="handleLogout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>

    <!-- 警告横幅 -->
    <transition name="alert-slide">
      <div v-if="showAlert" class="alert-banner">
        <span class="alert-icon">⚠️</span>
        <span>持续不良坐姿 {{ Math.floor(badStreak * 3 / 60) }} 分钟，请调整坐姿！</span>
        <el-button size="small" type="warning" @click="dismissAlert">我知道了</el-button>
      </div>
    </transition>

    <!-- 主体 -->
    <div class="dash-body">
      <!-- 欢迎 + 状态栏 -->
      <div class="welcome-row">
        <div class="welcome-text">
          <h1>{{ greeting }}，{{ userStore.profile?.nickname || userStore.userInfo?.username || '用户' }}</h1>
          <p>{{ dateStr }} {{ weekdayStr }} · 刷新 {{ refreshTime }}</p>
        </div>
        <div class="quick-actions">
          <el-button size="small" :loading="genLoading" @click="generateDemoData" style="margin-right:12px">
            📊 生成模拟数据
          </el-button>
          <div class="stat-mini">
            <div class="stat-mini-val">{{ dailyStats.length }}</div>
            <div class="stat-mini-lbl">数据天数</div>
          </div>
          <div class="stat-mini">
            <div class="stat-mini-val" style="color:#67c23a">{{ streakDays }}</div>
            <div class="stat-mini-lbl">连续良好</div>
          </div>
          <div class="stat-mini">
            <div class="stat-mini-val">{{ (dailyStats[dailyStats.length - 1]?.record_count || 0).toLocaleString() }}</div>
            <div class="stat-mini-lbl">今日记录</div>
          </div>
          <div class="stat-mini">
            <div class="stat-mini-val" :style="{ color: (postureStore.latest?.posture_label||'') !== 'normal' ? '#f56c6c' : '#67c23a' }">
              {{ (postureStore.latest?.posture_label || '--') === 'normal' ? '良好' : (postureStore.latest?.posture_label || '--') }}
            </div>
            <div class="stat-mini-lbl">当前状态</div>
          </div>
        </div>
      </div>

      <!-- 内容区 -->
      <div class="content-grid">
        <!-- 左：实时指标 -->
        <div class="content-left">
          <RealTimeIndicator
            :issues="(postureStore.latest && postureStore.latest.issues) || []"
            :head-angle="postureStore.latest?.head_angle ?? 0"
            :shoulder-diff="postureStore.latest?.shoulder_diff ?? 0"
            :hunchback-score="postureStore.latest?.hunchback_score ?? 0"
            :body-tilt="postureStore.latest?.body_tilt ?? 0"
            :round-shoulder="postureStore.latest?.round_shoulder ?? 0"
            :confidence="postureStore.latest?.confidence ?? 0"
          />
        </div>

        <!-- 中：日历 -->
        <div class="content-center">
          <div class="panel-card">
            <div class="panel-title">近14天坐姿日历</div>
            <div class="calendar-grid" v-if="dailyStats.length > 0">
              <div v-for="(d, idx) in dailyStats" :key="idx"
                   :class="['day-cell', dayClass(d)]"
                   :title="`点击查看${d.stat_date}详情`"
                   @click="openDayDetail(d)" style="cursor:pointer">
                <span>{{ d.stat_date.slice(5) }}</span>
              </div>
            </div>
            <div v-else class="empty-hint">暂无统计数据</div>
            <div class="calendar-legend">
              <span><span class="ld day-good"></span>良好</span>
              <span><span class="ld day-ok"></span>一般</span>
              <span><span class="ld day-bad"></span>较差</span>
              <span><span class="ld day-warn"></span>需改善</span>
            </div>
          </div>
          <div class="panel-card streak-panel">
            <div class="panel-title">连续打卡</div>
            <div class="streak-big">{{ streakDays }}<span>天</span></div>
            <div class="streak-dots">
              <span v-for="i in 7" :key="i" :class="{ filled: i <= Math.min(streakDays, 7) }"></span>
            </div>
          </div>
        </div>

        <!-- 右：天气占位 + 快捷入口 -->
        <div class="content-right">
          <div class="panel-card weather-card">
            <div class="panel-title">环境信息</div>
            <div v-if="weather && weather.weather" class="weather-real">
              <div class="weather-icon">{{ weather.weather === '晴' ? '☀️' : weather.weather.includes('云') ? '⛅' : weather.weather.includes('雨') ? '🌧️' : '🌤️' }}</div>
              <div class="weather-temp">{{ weather.temperature }}°C</div>
              <div class="weather-detail">{{ weather.weather }} · 湿度{{ weather.humidity }}%</div>
              <div class="weather-detail">{{ weather.city }} · {{ weather.winddirection }}</div>
            </div>
            <div v-else class="weather-placeholder">
              <div class="weather-icon">🌤️</div>
              <p>等待数据...</p>
              <span class="weather-hint" style="cursor:pointer;color:#667eea" @click="router.push('/profile')">管理员配置API Key</span>
            </div>
          </div>
          <div class="panel-card quick-links">
            <div class="panel-title">快捷操作</div>
            <div class="link-grid">
              <div class="link-item" @click="router.push('/health-report')">
                <span class="link-icon">📋</span><span>健康报告</span>
              </div>
              <div class="link-item" @click="router.push('/cluster')">
                <span class="link-icon">📊</span><span>聚类分析</span>
              </div>
              <div class="link-item" @click="router.push('/assistant')">
                <span class="link-icon">🤖</span><span>智能客服</span>
              </div>
              <div class="link-item" @click="router.push('/history')">
                <span class="link-icon">📈</span><span>历史趋势</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  
    <!-- 日历日详情弹窗 -->
    <el-dialog v-model="showDayDetail" :title="dayDetail?.date ? dayDetail.date + ' 坐姿详情' : '加载中...'" width="600px">
      <div v-if="dayDetailLoading" style="text-align:center;padding:40px">加载中...</div>
      <div v-else-if="dayDetail">
        <el-row :gutter="12" style="margin-bottom:16px">
          <el-col :span="8"><div class="detail-stat"><b>{{ dayDetail.total }}</b><br/>总记录</div></el-col>
          <el-col :span="8"><div class="detail-stat" style="color:#f56c6c"><b>{{ dayDetail.badCount }}</b><br/>不良次数</div></el-col>
          <el-col :span="8"><div class="detail-stat" style="color:#e6a23c"><b>{{ dayDetail.avgHead }}°</b><br/>平均前倾</div></el-col>
        </el-row>
        <div v-if="dayDetail.records.length > 0" style="max-height:300px;overflow-y:auto">
          <div v-for="r in dayDetail.records" :key="r.id" style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #f5f5f5;font-size:13px">
            <span>{{ r.created_at?.slice(11,19) || '' }}</span>
            <span>前倾{{ r.head_angle?.toFixed(1) }}°</span>
            <span>驼背{{ ((r.hunchback_score||0)*100).toFixed(0) }}%</span>
            <el-tag size="small" :type="r.posture_label === 'normal' ? 'success' : 'warning'">{{ r.posture_label || '-' }}</el-tag>
          </div>
        </div>
        <div v-else style="text-align:center;color:#909399;padding:20px">该日无详细记录</div>
      </div>
    </el-dialog>

</div>
</template>

<style scoped>
.dashboard { min-height: 100vh; background: #f0f2f5; }

/* ── 顶部 ── */
.dash-top {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 24px; height: 52px;
  background: linear-gradient(135deg, #1a1a2e, #16213e);
  color: #fff;
}
.top-brand { display: flex; align-items: center; gap: 10px; }
.brand-logo { width: 34px; height: 34px; border-radius: 8px; background: rgba(255,255,255,0.15); display: flex; align-items: center; justify-content: center; }
.brand-name { font-size: 15px; font-weight: 600; letter-spacing: 1px; }
.top-nav { display: flex; gap: 4px; }
.top-nav a {
  color: rgba(255,255,255,0.65); text-decoration: none; padding: 6px 14px;
  border-radius: 6px; font-size: 13px; transition: all 0.2s;
}
.top-nav a:hover, .top-nav a.active { color: #fff; background: rgba(255,255,255,0.12); }
.top-right { display: flex; align-items: center; gap: 16px; }
.top-time { font-size: 14px; font-family: monospace; color: rgba(255,255,255,0.7); }
.user-name { color: rgba(255,255,255,0.85); cursor: pointer; font-size: 13px; }

/* ── 警告 ── */
.alert-banner {
  display: flex; align-items: center; justify-content: center; gap: 16px;
  padding: 10px; background: linear-gradient(90deg, #fef0f0, #fdf6ec);
  border-bottom: 2px solid #f56c6c; animation: shake 0.5s;
  font-size: 14px; color: #f56c6c;
}
.alert-icon { font-size: 22px; }
@keyframes shake {
  0%,100%{transform:translateX(0)} 20%{transform:translateX(-6px)}
  40%{transform:translateX(6px)} 60%{transform:translateX(-3px)} 80%{transform:translateX(3px)}
}
.alert-slide-enter-active { animation: slideDown 0.3s ease; }
.alert-slide-leave-active { animation: slideDown 0.3s ease reverse; }
@keyframes slideDown { from{opacity:0;transform:translateY(-20px)} to{opacity:1;transform:translateY(0)} }

/* ── 主体 ── */
.dash-body { padding: 20px 24px; }

/* 欢迎栏 */
.welcome-row {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 20px;
}
.welcome-text h1 { margin: 0; font-size: 22px; color: #1a1a2e; font-weight: 700; }
.welcome-text p { margin: 4px 0 0; font-size: 13px; color: #909399; }
.quick-actions { display: flex; gap: 20px; }
.stat-mini { text-align: center; min-width: 80px; }
.stat-mini-val { font-size: 26px; font-weight: 700; color: #303133; }
.stat-mini-lbl { font-size: 11px; color: #909399; margin-top: 2px; }

/* 三栏网格 */
.content-grid { display: grid; grid-template-columns: 340px 1fr 260px; gap: 16px; }

/* 卡片 */
.panel-card {
  background: #fff; border-radius: 12px; padding: 16px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.04); margin-bottom: 12px;
}
.panel-title { font-size: 14px; font-weight: 600; color: #303133; margin-bottom: 12px; }

/* 日历 */
.calendar-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 5px; }
.day-cell {
  aspect-ratio: 1; border-radius: 6px; display: flex; align-items: center;
  justify-content: center; font-size: 11px; font-weight: 600; cursor: default;
  transition: transform 0.15s;
}
.day-cell:hover { transform: scale(1.12); }
.day-none { background: #fafafa; color: #c0c4cc; }
.day-good { background: #e1f3d8; color: #529b2e; }
.day-ok { background: #faecd8; color: #b88230; }
.day-bad { background: #fde2e2; color: #c45656; }
.day-warn { background: #f89898; color: #fff; }
.calendar-legend { display: flex; gap: 12px; margin-top: 10px; font-size: 11px; color: #909399; }
.ld { display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 4px; vertical-align: middle; }
.ld.day-good { background: #e1f3d8; } .ld.day-ok { background: #faecd8; }
.ld.day-bad { background: #fde2e2; } .ld.day-warn { background: #f89898; }

/* 打卡 */
.streak-panel { text-align: center; }
.streak-big { font-size: 52px; font-weight: 800; color: #67c23a; }
.streak-big span { font-size: 20px; font-weight: 400; color: #909399; }
.streak-dots { display: flex; justify-content: center; gap: 8px; margin-top: 8px; }
.streak-dots span { width: 24px; height: 24px; border-radius: 50%; background: #ebeef5; transition: all 0.3s; }
.streak-dots span.filled { background: #67c23a; box-shadow: 0 2px 8px rgba(103,194,58,0.4); }

/* 天气 */
.weather-card { text-align: center; }
.weather-icon { font-size: 36px; }
.weather-placeholder p { color: #909399; font-size: 13px; margin: 8px 0 4px; }
.weather-hint { font-size: 11px; color: #c0c4cc; }

/* 快捷 */
.link-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.link-item { display: flex; align-items: center; gap: 6px; padding: 10px; border-radius: 8px;
  background: #f7f8fa; cursor: pointer; font-size: 13px; transition: all 0.15s; }
.link-item:hover { background: #e8eaed; transform: translateY(-1px); }
.link-icon { font-size: 18px; }

.empty-hint { text-align: center; color: #c0c4cc; font-size: 13px; padding: 20px; }

/* 响应式 */
@media (max-width: 1200px) {
  .content-grid { grid-template-columns: 1fr; }
  .top-nav { display: none; }
}
.detail-stat { text-align:center; padding:12px; background:#f7f8fa; border-radius:8px; font-size:13px; color:#606266; }
.detail-stat b { font-size:22px; display:block; margin-bottom:2px; }
</style>
