<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElNotification, ElMessageBox } from 'element-plus'
import { usePostureStore } from '../store/posture'
import { useUserStore } from '../store/user'
import request from '../api/request'
import RealTimeIndicator from '../components/RealTimeIndicator.vue'
import VideoStreamPanel from '../components/VideoStreamPanel.vue'
import SkeletonCanvas from '../components/SkeletonCanvas.vue'
// AiPet now in App.vue (global)
import PetHouse from '../components/PetHouse.vue'
import { useWebSocket } from '../composables/useWebSocket'
import { useVideoStream } from '../composables/useVideoStream'

const router = useRouter()
const route = useRoute()
const postureStore = usePostureStore()
const userStore = useUserStore()
const lastUpdate = ref('')
const refreshTime = ref('')
const currentPath = computed(() => route.path)
const pollCount = ref(0)

// WebSocket 实时连接（自动回退到轮询）
const { wsConnected, isFallbackPolling } = useWebSocket()

// 视频流状态（仅用快照模式）
const { snapshotUrl, startSnapshotPolling, stopSnapshotPolling } = useVideoStream()

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
const recentRecords = ref([])

async function loadStats() {
  const uid = userStore.userInfo?.user_id || userStore.profile?.id || 1
  // 加载每日聚合（日历数据）— 用 fetch 绕过 axios 拦截器问题
  try {
    const end = new Date().toISOString().slice(0, 10)
    const start = new Date(Date.now() - 14 * 86400000).toISOString().slice(0, 10)
    const url = new URL('/api/v1/data/daily-summary', window.location.origin)
    url.searchParams.set('user_id', uid)
    url.searchParams.set('start_date', start)
    url.searchParams.set('end_date', end)
    const resp = await fetch(url)
    const json = await resp.json()
    dailyStats.value = json.stats || []
  } catch (e) {
    console.error('[Dashboard] 日历加载失败:', e)
  }
  // 加载签到数据（打卡天数）
  try {
    const resp = await request.get('/api/v1/auth/checkin/status')
    streakDays.value = resp.data?.streak || 0
  } catch { /* ignore */ }
}

// 英文标签→中文
function postureToChinese(label) {
  if (!label || label === 'normal') return '良好'
  const sev = { normal:'正常', mild:'轻度', moderate:'中度', severe:'重度' }
  const name = { forward_head:'头部前倾', high_low_shoulder:'高低肩', hunched_back:'驼背含胸', body_tilt:'身体倾斜', round_shoulder:'圆肩' }
  return label.split(';').map(p => {
    const [t, s] = p.split(':')
    return (name[t]||t) + (sev[s]? '·'+sev[s] : '')
  }).join('，').slice(0, 30)
}

// 显示最大非零指标
function maxMetric(r) {
  const vals = [
    { k: 'head_angle', v: r.head_angle || 0, u: '°前倾' },
    { k: 'body_tilt', v: r.body_tilt || 0, u: '°倾斜' },
    { k: 'hunchback_score', v: (r.hunchback_score||0)*100, u: '%驼背' },
    { k: 'shoulder_diff', v: (r.shoulder_diff||0)*100, u: '%高低肩' },
  ]
  const best = vals.sort((a,b) => b.v - a.v)[0]
  return best.v > 0 ? best.v.toFixed(0) + best.u : '—'
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

// 解析 posture_label → issues 数组
const parsedIssues = computed(() => {
  const label = postureStore.latest?.posture_label || ''
  if (label === 'normal' || !label) return []
  return label.split(';').filter(Boolean).map(p => {
    const [type, sev] = p.split(':')
    const names = { forward_head:'头部前倾', high_low_shoulder:'高低肩', hunched_back:'驼背含胸', body_tilt:'身体倾斜', round_shoulder:'圆肩' }
    return { type, name: names[type] || type, severity: sev || 'mild' }
  })
})

// 中文状态标签
const chineseStatus = computed(() => {
  const label = postureStore.latest?.posture_label || ''
  if (label === 'normal' || !label) return '良好'
  const sevMap = { normal:'正常', mild:'轻度', moderate:'中度', severe:'重度' }
  const nameMap = { forward_head:'头部前倾', high_low_shoulder:'高低肩', hunched_back:'驼背含胸', body_tilt:'身体倾斜', round_shoulder:'圆肩' }
  return label.split(';').filter(Boolean).map(p => {
    const [type, sev] = p.split(':')
    return (nameMap[type] || type) + '：' + (sevMap[sev] || sev)
  }).join('，')
})

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
    // 同时拉最近5条记录
    try {
      const hResp = await request.get('/api/v1/data/history', { params: { user_id: uid, limit: 5 } })
      recentRecords.value = hResp.data.records || []
    } catch { /* ignore */ }
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
function openAssistant() { router.push('/assistant') }

// ── AI助手悬浮对话框 ──
const aiOpen = ref(false); const aiMinimized = ref(false)
const aiPos = ref({ x: Math.max(100, window.innerWidth - 400), y: Math.max(60, window.innerHeight - 540) })
const fabPos = ref({ x: window.innerWidth - 76, y: window.innerHeight - 76 })
let aiDragging = false, aiDragStart = { x:0, y:0 }
let fabDragging = false, fabDragStart = { x:0, y:0 }, fabClickMoved = false

// 对话框拖动
function aiStartDrag(e) {
  if (e.target.closest('.ai-dialog-actions') || e.target.closest('button') || e.target.closest('a')) return
  aiDragging = true; aiDragStart = { x: e.clientX - aiPos.value.x, y: e.clientY - aiPos.value.y }
  document.addEventListener('mousemove', aiOnDrag); document.addEventListener('mouseup', aiStopDrag)
}
function aiOnDrag(e) {
  if (!aiDragging) return
  aiPos.value = { x: e.clientX - aiDragStart.x, y: e.clientY - aiDragStart.y }
}
function aiStopDrag() { aiDragging = false; document.removeEventListener('mousemove', aiOnDrag); document.removeEventListener('mouseup', aiStopDrag) }

// FAB拖动 + 空闲边缘吸附
let fabSnapTimer = null
const fabEl = () => document.querySelector('.ai-fab')
function fabStartDrag(e) {
  e.preventDefault()
  clearTimeout(fabSnapTimer); clearTimeout(fabHoldTimer)
  // 拖动时去掉transition，跟手
  const el = fabEl(); if (el) el.style.transition = 'none'
  fabDragging = true; fabClickMoved = false
  fabDragStart = { x: e.clientX - fabPos.value.x, y: e.clientY - fabPos.value.y }
  document.addEventListener('mousemove', fabOnDrag); document.addEventListener('mouseup', fabStopDrag)
  // 按住600ms不动→显示剩余次数
  fabHoldTimer = setTimeout(() => { if (!fabClickMoved) checkQuota() }, 600)
}
function fabOnDrag(e) {
  if (!fabDragging) return
  if (Math.abs(e.clientX - fabDragStart.x - fabPos.value.x) > 1 || Math.abs(e.clientY - fabDragStart.y - fabPos.value.y) > 1) {
    fabClickMoved = true; clearTimeout(fabHoldTimer)
  }
  fabPos.value = { x: e.clientX - fabDragStart.x, y: e.clientY - fabDragStart.y }
}
function snapToEdge() {
  const ww = window.innerWidth, wh = window.innerHeight
  const x = fabPos.value.x, y = fabPos.value.y
  // 确定最近边
  const distLeft = x + 26, distRight = ww - (x + 26), distBottom = wh - (y + 26)
  if (distLeft < distRight && distLeft < distBottom && distLeft < 150) {
    fabPos.value.x = -32
  } else if (distRight < distLeft && distRight < distBottom && distRight < 150) {
    fabPos.value.x = ww - 20
  } else if (distBottom < 200) {
    fabPos.value.y = wh - 20
  }
}
function fabStopDrag() {
  fabDragging = false; clearTimeout(fabHoldTimer)
  document.removeEventListener('mousemove', fabOnDrag); document.removeEventListener('mouseup', fabStopDrag)
  // 恢复transition用于吸附动画
  const el = fabEl(); if (el) el.style.transition = ''
  if (fabClickMoved) fabSnapTimer = setTimeout(snapToEdge, 3000)
}
// 宠物皮肤
const PETS = { cat:'🐱', dog:'🐶', hamster:'🐹', fox:'🦊', neko:'🎀' }
const currentPet = ref(localStorage.getItem('ai_pet') || 'cat')
const petEmoji = computed(() => PETS[currentPet.value] || '🐱')

// 右键迷你窗 · 长按显示剩余次数
const miniChatOpen = ref(false)
const miniChatInput = ref('')
const miniChatMessages = ref([])
const miniChatLoading = ref(false)
const fabQuotaLeft = ref(30)
let fabLongPressTimer = null

// 长按查剩余次数
let fabHoldTimer = null
const fabQuotaHint = ref('')

function fabClick() {
  if (!fabClickMoved) aiOpen = true
}
function fabRightClick(e) {
  e.preventDefault()
  miniChatOpen.value = !miniChatOpen.value
  aiOpen.value = false
  if (miniChatOpen.value) checkQuota()
}
async function checkQuota() {
  try {
    const { useUserStore } = await import('../store/user')
    const uid = useUserStore().userInfo?.user_id || 191
    const { data } = await (await import('../api/request')).default.get('/api/v1/chat/quota', { params: { user_id: uid } })
    fabQuotaLeft.value = Math.max(0, 30 - (data?.used || 0))
    fabQuotaHint.value = '💬 还可以问 ' + fabQuotaLeft.value + ' 次'
    setTimeout(() => { fabQuotaHint.value = '' }, 2500)
  } catch { fabQuotaLeft.value = 30 }
}

async function miniChatSend(q) {
  const msg = (q || miniChatInput.value).trim()
  if (!msg || miniChatLoading.value) return
  miniChatMessages.value.push({ role: 'user', content: msg })
  miniChatInput.value = ''
  miniChatLoading.value = true
  try {
    const uid = userStore.userInfo?.user_id || 1
    const { data } = await import('../api/chat').then(m => m.chatApi.sendMessage(msg, [], uid))
    miniChatMessages.value.push({ role: 'assistant', content: data.reply })
  } catch {
    miniChatMessages.value.push({ role: 'assistant', content: 'AI服务暂不可用', error: true })
  }
  miniChatLoading.value = false
}
function fabHover() {
  clearTimeout(fabSnapTimer)
  if (fabPos.value.x < -10) fabPos.value.x = 12
  else if (fabPos.value.x > window.innerWidth - 42) fabPos.value.x = window.innerWidth - 64
  if (fabPos.value.y > window.innerHeight - 42) fabPos.value.y = window.innerHeight - 64
}
function fabLeave() { fabSnapTimer = setTimeout(snapToEdge, 3000) }
function fabResize() { fabPos.value.x = Math.min(fabPos.value.x, window.innerWidth - 20); fabPos.value.y = Math.min(fabPos.value.y, window.innerHeight - 20) }

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

// ── 天气 + 城市选择 ──
const weather = ref(null)
const showCityPicker = ref(false)
const cityName = ref(localStorage.getItem('weather_city') || '')
const cityCode = ref(localStorage.getItem('weather_city_code') || '')
const citySuggestions = ref([])  // 联想搜索结果
let citySearchTimer = null

// 输入城市名时触发联想搜索（300ms 防抖）
function onCityInput() {
  clearTimeout(citySearchTimer)
  const q = cityName.value.trim()
  if (!q || q.length < 1) {
    citySuggestions.value = []
    return
  }
  citySearchTimer = setTimeout(async () => {
    try {
      const url = new URL('/api/v1/data/city-lookup', window.location.origin)
      url.searchParams.set('name', q)
      const resp = await fetch(url)
      const data = await resp.json()
      citySuggestions.value = data.cities || []
    } catch { citySuggestions.value = [] }
  }, 300)
}

// 点击联想条目直接选择城市
function selectCity(city) {
  cityCode.value = city.adcode
  cityName.value = city.name
  localStorage.setItem('weather_city', city.name)
  localStorage.setItem('weather_city_code', city.adcode)
  citySuggestions.value = []
  showCityPicker.value = false
  loadWeather()
}

async function loadWeather() {
  try {
    const url = new URL('/api/v1/data/weather', window.location.origin)
    if (cityCode.value) url.searchParams.set('city', cityCode.value)
    const resp = await fetch(url)
    const data = await resp.json()
    if (data && data.weather) {
      weather.value = data
    }
  } catch (e) {
    console.error('[Weather] 加载失败:', e)
  }
}
async function switchCity() {
  const name = cityName.value.trim()
  if (!name) return
  try {
    // 通过后端代理查询城市编码（无需前端持有API Key）
    const url = new URL('/api/v1/data/city-lookup', window.location.origin)
    url.searchParams.set('name', name)
    const resp = await fetch(url)
    const data = await resp.json()
    if (data.status === 'success' && data.adcode) {
      cityCode.value = data.adcode
      cityName.value = data.name
      localStorage.setItem('weather_city', data.name)
      localStorage.setItem('weather_city_code', data.adcode)
      showCityPicker.value = false
      await loadWeather()
      return
    }
    ElNotification({ title: '城市切换失败', message: data.message || '未找到该城市', type: 'warning' })
  } catch {
    ElNotification({ title: '切换失败', message: '网络异常，请稍后重试', type: 'error' })
  }
}

let timer = null, clockTimer = null
onMounted(() => {
  updateClock()
  refresh()
  loadStats()
  loadWeather()
  requestNotification()
  startSnapshotPolling() // K230截图轮询
  timer = setInterval(refresh, 3000)
  clockTimer = setInterval(updateClock, 1000)
  window.addEventListener('resize', fabResize)
})
onUnmounted(() => {
  clearInterval(timer)
  clearInterval(clockTimer)
  stopSnapshotPolling()
  window.removeEventListener('resize', fabResize)
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
        <router-link to="/shop" :class="{ active: currentPath === '/shop' }">商城</router-link>
        <router-link to="/settings" :class="{ active: currentPath === '/settings' }">⚙</router-link>
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
          <p>
            {{ dateStr }} {{ weekdayStr }} · 刷新 {{ refreshTime }}
            <span v-if="wsConnected" style="color:#67c23a;margin-left:8px">⚡实时</span>
            <span v-else style="color:#e6a23c;margin-left:8px">📡轮询</span>
          </p>
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
        </div>
      </div>

      <!-- 内容区 -->
      <div class="content-grid">
        <!-- 左：实时指标 -->
        <div class="content-left">
          <!-- 视频面板：PC摄像头 + K230骨架叠加 -->
          <VideoStreamPanel
            :snapshot-url="snapshotUrl"
            :keypoints-json="postureStore.latest?.keypoints || '[]'"
            :posture-label="postureStore.latest?.posture_label || 'normal'"
          />
          <SkeletonCanvas
            :keypoints-json="postureStore.latest?.keypoints || '[]'"
            :posture-label="postureStore.latest?.posture_label || 'normal'"
          />
        </div>

        <!-- 中：天气+日历 -->
        <div class="content-center">
          <!-- 天气横条 -->
          <div v-if="weather" class="weather-bar">
            <span class="weather-bar-icon">{{ weather.weather === '晴' ? '☀️' : weather.weather.includes('云') ? '⛅' : weather.weather.includes('雨') ? '🌧️' : '🌤️' }}</span>
            <span class="weather-bar-city">{{ weather.city || '福州' }}</span>
            <span class="weather-bar-temp">{{ weather.temperature }}°</span>
            <span class="weather-bar-desc">{{ weather.weather }}</span>
            <span class="weather-bar-extra">💧{{ weather.humidity || '--' }}% 💨{{ weather.winddirection || '--' }}</span>
            <span class="weather-bar-change" @click="showCityPicker = !showCityPicker">切换 ▾</span>
          </div>
          <div v-else class="weather-bar weather-bar-placeholder">
            <span>🌤️</span>
            <span>{{ cityName || '选择城市' }}</span>
            <span @click="showCityPicker = !showCityPicker" style="cursor:pointer;color:#409EFF">切换 ▾</span>
            <span @click="loadWeather()" style="cursor:pointer;margin-left:8px">刷新</span>
          </div>
          <!-- 城市选择 -->
          <div v-if="showCityPicker" class="city-picker-inline">
            <el-input v-model="cityName" size="small" placeholder="搜索城市..." @input="onCityInput" @keyup.enter="switchCity" style="flex:1" />
            <el-button size="small" type="primary" @click="switchCity">切换</el-button>
            <div v-if="citySuggestions.length > 0" class="city-dropdown-inline">
              <div v-for="c in citySuggestions" :key="c.adcode" class="city-dropdown-item" @click="selectCity(c)">{{ c.name }}</div>
            </div>
          </div>
          <!-- 日历 -->
          <div class="panel-card">
            <div class="panel-title">近14天坐姿日历 <span class="detail-btn" @click.stop="router.push('/posture-calendar')" title="查看详情">📅 ›</span></div>
            <div v-if="dailyStats.length === 0" class="empty-hint">
              暂无数据，请先<el-button type="primary" size="small" text :loading="genLoading" @click="generateDemoData">生成模拟数据</el-button>
            </div>
            <div class="calendar-grid" v-else>
              <div v-for="(d, idx) in dailyStats" :key="idx"
                   :class="['day-cell', dayClass(d)]"
                   :title="`点击查看${d.stat_date}详情`"
                   @click="openDayDetail(d)" style="cursor:pointer">
                <span>{{ d.stat_date.slice(5) }}</span>
              </div>
            </div>
            <div class="calendar-legend">
              <span><span class="ld day-good"></span>良好</span>
              <span><span class="ld day-ok"></span>一般</span>
              <span><span class="ld day-bad"></span>较差</span>
              <span><span class="ld day-warn"></span>需改善</span>
            </div>
          </div>
          <div class="panel-card streak-panel">
            <div class="panel-title">连续打卡 <span class="detail-btn" @click.stop="router.push('/calendar')" title="打卡详情">📋 ›</span></div>
            <div class="streak-big">{{ streakDays }}<span>天</span></div>
            <div class="streak-dots">
              <span v-for="i in 7" :key="i" :class="{ filled: i <= Math.min(streakDays, 7) }"></span>
            </div>
          </div>
          <!-- 最近记录 -->
          <div class="panel-card recent-panel">
            <div class="panel-title" style="cursor:pointer" @click="router.push('/history')">最近坐姿记录 <span style="font-size:11px;color:#909399">历史 ›</span></div>
            <div v-if="recentRecords.length === 0" class="empty-hint">暂无数据</div>
            <div v-else class="recent-list">
              <div v-for="r in recentRecords" :key="r.id" class="recent-row">
                <span class="recent-time">{{ (r.created_at || '').slice(11, 19) }}</span>
                <span class="recent-status" :style="{ color: r.posture_label === 'normal' ? '#67c23a' : '#f56c6c' }">
                  {{ postureToChinese(r.posture_label) }}
                </span>
                <span class="recent-val">{{ maxMetric(r) }}</span>
              </div>
            </div>
            <!-- 当前坐姿状态条（嵌入最近记录下方） -->
            <div v-if="chineseStatus !== '良好'" class="posture-status-inline">
              <span class="status-inline-icon">{{ parsedIssues.length >= 3 ? '🛑' : parsedIssues.length >= 2 ? '⚠️' : '🔔' }}</span>
              <span class="status-inline-text">{{ chineseStatus }}</span>
            </div>
          </div>
        </div>

        <!-- 右：实时指标 + 天气 + 快捷入口 -->
        <div class="content-right">
          <!-- 实时指标卡片 -->
          <RealTimeIndicator
            :issues="parsedIssues"
            :head-angle="postureStore.latest?.head_angle ?? 0"
            :shoulder-diff="postureStore.latest?.shoulder_diff ?? 0"
            :hunchback-score="postureStore.latest?.hunchback_score ?? 0"
            :body-tilt="postureStore.latest?.body_tilt ?? 0"
            :round-shoulder="postureStore.latest?.round_shoulder ?? 0"
            :confidence="postureStore.latest?.confidence ?? 0"
          />

          <div class="panel-card quick-links">
            <div class="panel-title">快捷操作</div>
            <div class="link-grid">
              <div class="link-item" @click="router.push('/health-report')"><span class="link-icon">📋</span><span>健康报告</span></div>
              <div class="link-item" @click="router.push('/cluster')"><span class="link-icon">📊</span><span>聚类分析</span></div>
              <div class="link-item" @click="router.push('/assistant')"><span class="link-icon">🤖</span><span>智能客服</span></div>
              <div class="link-item" @click="router.push('/history')"><span class="link-icon">📈</span><span>历史趋势</span></div>
            </div>
          </div>
          <!-- 助手之家 -->
          <PetHouse />
        </div>
      </div>
    </div>
  
    <!-- 日历日详情弹窗 -->
    <el-dialog  append-to-body v-model="showDayDetail" :title="dayDetail?.date ? dayDetail.date + ' 坐姿详情' : '加载中...'" width="600px">
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

    <!-- AI宠物（左键拖动 · 右键迷你窗 · 3D待机动画） -->
    <AiPet v-if="!aiOpen && !miniChatOpen"
      :pet-type="currentPet" :quota-left="fabQuotaLeft" :quota-hint="fabQuotaHint"
      @rightClick="fabRightClick" @click="fabClick" @longPress="checkQuota"
    />
    <!-- 悬浮聊天框（右键宠物打开 · 可拖动） -->
    <transition name="ai-slide">
      <div v-if="miniChatOpen" class="float-chat" :style="{ left: Math.max(4, fabPos.x - 340) + 'px', top: Math.max(40, fabPos.y - 400) + 'px' }" @mousedown="aiStartDrag">
        <div class="float-chat-header">
          <span>{{ petEmoji }} 智能问答</span>
          <span class="mini-quota">剩 {{ fabQuotaLeft }} 次</span>
          <span @click.stop="router.push('/assistant'); miniChatOpen=false" class="float-chat-btn" title="全屏">⛶</span>
          <span @click.stop="miniChatOpen=false" class="float-chat-btn float-chat-close" title="关闭">✕</span>
        </div>
        <div class="float-chat-body">
          <div v-if="miniChatMessages.length===0" class="float-chat-empty">
            <span style="font-size:32px">{{ petEmoji }}</span>
            <p>有什么可以帮你的？</p>
            <div class="float-quick-asks">
              <span @click="miniChatSend">我的坐姿怎么样</span>
              <span @click="miniChatSend">怎么改善驼背</span>
            </div>
          </div>
          <div v-for="(m,i) in miniChatMessages" :key="i">
            <div v-if="m.role==='user'" class="float-msg float-msg-user">{{ m.content }}</div>
            <div v-else class="float-msg float-msg-ai">{{ m.content }}</div>
          </div>
          <div v-if="miniChatLoading" class="float-msg float-msg-ai" style="opacity:0.6">思考中...</div>
        </div>
        <div class="float-chat-input">
          <input v-model="miniChatInput" @keyup.enter="miniChatSend" placeholder="输入问题..." :disabled="miniChatLoading" />
          <button @click="miniChatSend" :disabled="miniChatLoading || !miniChatInput.trim()">▶</button>
        </div>
      </div>
    </transition>
    <!-- AI对话框（全区域可拖动） -->
    <transition name="ai-slide">
      <div v-if="aiOpen" class="ai-dialog" :class="{ minimized: aiMinimized }"
           :style="{ left: aiPos.x + 'px', top: aiPos.y + 'px' }" @mousedown="aiStartDrag">
        <div class="ai-dialog-header">
          <span>🤖 AI坐姿助手</span>
          <div class="ai-dialog-actions">
            <span @click.stop="aiMinimized = !aiMinimized" :title="aiMinimized ? '展开' : '收起'">
              {{ aiMinimized ? '□' : '─' }}
            </span>
            <span @click.stop="aiPos = { x: Math.max(100, window.innerWidth - 400), y: Math.max(60, window.innerHeight - 540) }" title="复位">↺</span>
            <span @click.stop="aiOpen = false" title="关闭">✕</span>
          </div>
        </div>
        <div v-show="!aiMinimized" class="ai-dialog-body">
          <div style="display:flex;flex-direction:column;align-items:center;gap:12px;padding:10px 0">
            <el-button type="primary" @click.stop="openAssistant" style="width:100%">
              💬 打开完整对话
            </el-button>
            <el-button @click.stop="router.push('/assistant');aiOpen=false" style="width:100%">
              📋 查看对话记录
            </el-button>
            <span style="font-size:11px;color:#909399">
              拖动对话框任意位置可移动 · 点击 ─ 收起
            </span>
          </div>
        </div>
      </div>
    </transition>

</div>
</template>

<style scoped>
.dashboard { min-height: 100vh; width: 100%; background: #f0f2f5; }

/* ── 顶部 ── */
.dash-top {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 24px; height: 52px;
  background: linear-gradient(135deg, #1a1a2e, #16213e);
  color: #fff; width: 100%;
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

/* 三栏网格 — 自适应缩放 */
.content-grid { display: grid; grid-template-columns: minmax(300px, 380px) 1fr minmax(260px, 380px); gap: 1rem; }

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

/* 天气横条（中栏顶部） */
.weather-bar {
  background: linear-gradient(135deg, #3b82f6, #60a5fa);
  border-radius: 10px; padding: 10px 16px; margin-bottom: 12px;
  display: flex; align-items: center; gap: 12px;
  color: #fff; font-size: 14px; position: relative; overflow: hidden;
}
.weather-bar::after { content:''; position:absolute; top:-20px; right:-20px; width:80px; height:80px; border-radius:50%; background:rgba(255,255,255,0.1); }
.weather-bar-icon { font-size: 24px; position: relative; z-index: 1; }
.weather-bar-city { font-weight: 600; position: relative; z-index: 1; }
.weather-bar-temp { font-size: 22px; font-weight: 300; position: relative; z-index: 1; }
.weather-bar-desc { opacity: 0.85; position: relative; z-index: 1; }
.weather-bar-extra { font-size: 12px; opacity: 0.7; margin-left: auto; position: relative; z-index: 1; }
.weather-bar-change { font-size: 11px; opacity: 0.7; cursor: pointer; position: relative; z-index: 1; }
.weather-bar-change:hover { opacity: 1; }
.weather-bar-placeholder { background: linear-gradient(135deg, #94a3b8, #cbd5e1); }
.city-picker-inline { display: flex; gap: 8px; margin-bottom: 12px; padding: 8px; background: #fff; border-radius: 8px; position: relative; }
.city-dropdown-inline { position: absolute; top: 100%; left: 0; right: 0; background: #fff; border-radius: 6px; box-shadow: 0 4px 16px rgba(0,0,0,0.15); max-height: 160px; overflow-y: auto; z-index: 100; }
.city-dropdown-item { padding: 8px 12px; cursor: pointer; font-size: 13px; color: #303133; }
.city-dropdown-item:hover { background: #f0f2f5; }

/* 天气大卡片 */
.weather-big-card {
  background: linear-gradient(135deg, #3b82f6 0%, #60a5fa 40%, #93c5fd 100%);
  border-radius: 14px; padding: 18px; color: #fff; margin-bottom: 12px;
  box-shadow: 0 4px 16px rgba(59,130,246,0.3);
  position: relative; overflow: hidden;
}
.weather-big-card::after {
  content: ''; position: absolute; top: -30px; right: -30px;
  width: 120px; height: 120px; border-radius: 50%;
  background: rgba(255,255,255,0.1);
}
.weather-main { display: flex; justify-content: space-between; align-items: center; position: relative; z-index: 1; }
.weather-left { display: flex; align-items: center; gap: 12px; }
.weather-icon-big { font-size: 42px; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.2)); animation: weatherFloat 3s ease-in-out infinite; }
@keyframes weatherFloat { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-4px)} }
.weather-city { font-size: 15px; font-weight: 600; }
.weather-change { font-size: 11px; opacity: 0.7; cursor: pointer; margin-left: 4px; }
.weather-change:hover { opacity: 1; }
.weather-time { font-size: 12px; opacity: 0.75; margin-top: 2px; }
.weather-right { text-align: right; position: relative; z-index: 1; }
.weather-temp-big { font-size: 48px; font-weight: 300; line-height: 1; }
.weather-temp-big span { font-size: 22px; }
.weather-desc { font-size: 14px; opacity: 0.85; margin-top: 2px; }
.weather-extra { display: flex; gap: 16px; margin-top: 12px; font-size: 12px; opacity: 0.8; position: relative; z-index: 1; }
.city-picker-row { display: flex; gap: 6px; margin-top: 10px; position: relative; z-index: 1; }
.city-input { flex: 1; }
.city-dropdown { position: absolute; top: 100%; left: 0; right: 0; background: #fff; border-radius: 6px; box-shadow: 0 4px 16px rgba(0,0,0,0.15); max-height: 180px; overflow-y: auto; z-index: 100; }
.city-dropdown-item { padding: 8px 12px; cursor: pointer; font-size: 13px; color: #303133; transition: background 0.1s; }
.city-dropdown-item:hover { background: #f0f2f5; }
.weather-placeholder-card { background: linear-gradient(135deg, #94a3b8, #cbd5e1) !important; box-shadow: 0 4px 16px rgba(148,163,184,0.2) !important; }

/* 天气占位 */
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
@media (max-width: 1000px) {
  .content-grid { grid-template-columns: 1fr; }
  .top-nav { display: none; }
}
@media (max-width: 600px) {
  .top-right { gap: 8px; }
  .quick-actions { flex-wrap: wrap; gap: 8px; }
  .calendar-grid { gap: 3px; }
}
.detail-stat { text-align:center; padding:12px; background:#f7f8fa; border-radius:8px; font-size:13px; color:#606266; }
.detail-stat b { font-size:22px; display:block; margin-bottom:2px; }
/* 视频面板样式已迁移至 VideoStreamPanel.vue */
.video-placeholder span { font-size: 11px; color: #c0c4cc; }
.video-status.offline { color: #f56c6c; font-size: 11px; }

/* 悬浮AI入口按钮 */
.ai-fab { position:fixed; width:56px; height:56px; border-radius:50%;
  background:linear-gradient(135deg,#ffe0e8,#ffd4e0); display:flex; align-items:center; justify-content:center;
  font-size:28px; cursor:grab; z-index:999; box-shadow:0 4px 16px rgba(255,150,180,0.4);
  transition:transform 0.15s, box-shadow 0.15s;
  user-select:none; }
.fab-pet { animation:petIdle 2.5s ease-in-out infinite; }
@keyframes petIdle { 0%,100%{transform:translateY(0) rotate(0deg)} 15%{transform:translateY(-3px) rotate(-3deg)} 30%{transform:translateY(0) rotate(0deg)} 45%{transform:translateY(-2px) rotate(3deg)} 60%{transform:translateY(0) rotate(0deg)} 75%{transform:scale(1.08)} 85%{transform:scale(1)} }
.ai-fab::before { content:''; position:absolute; inset:-6px; border-radius:50%; background:transparent;
  transition:all 0.3s; z-index:-1; }
.ai-fab.dragging::before { background:rgba(102,126,234,0.12); animation:trailPulse 0.5s ease-out infinite; }
.ai-fab.dragging { box-shadow: 0 0 0 8px rgba(102,126,234,0.15), 0 0 0 20px rgba(102,126,234,0.06) !important; }
@keyframes trailPulse { 0%{inset:-8px;opacity:0.8} 50%{inset:-18px;opacity:0.3} 100%{inset:-8px;opacity:0.8} }
.ai-fab:active { cursor:grabbing; transform:scale(1.05); box-shadow:0 8px 28px rgba(102,126,234,0.55); }
.ai-fab:hover { transform:scale(1.08); box-shadow:0 6px 22px rgba(102,126,234,0.5); }
.fab-badge { position:absolute; top:-4px; right:-4px; width:20px; height:20px; border-radius:50%;
  background:#f56c6c; color:#fff; font-size:10px; font-weight:700; display:flex; align-items:center; justify-content:center;
  animation:badgePulse 1.5s ease-in-out infinite; z-index:2; }
@keyframes badgePulse { 0%,100%{transform:scale(1)} 50%{transform:scale(1.15)} }
/* 云朵气泡 */
.fab-cloud { position:absolute; top:-52px; left:50%; transform:translateX(-50%);
  background:#fff; border-radius:16px; padding:6px 14px;
  box-shadow:0 3px 12px rgba(102,126,234,0.2);
  animation:cloudFloat 2s ease-in-out infinite; z-index:3; white-space:nowrap; }
.fab-cloud::after { content:''; position:absolute; bottom:-6px; left:50%; transform:translateX(-50%);
  width:0; height:0; border-left:7px solid transparent; border-right:7px solid transparent;
  border-top:8px solid #fff; }
.fab-cloud-text { font-size:12px; font-weight:700; color:#667eea; }
@keyframes cloudFloat { 0%,100%{transform:translateX(-50%) translateY(0)} 50%{transform:translateX(-50%) translateY(-4px)} }
/* AI对话框 */
.ai-dialog { position:fixed; z-index:1000; width:clamp(300px, 360px, 90vw); background:#fff; border-radius:14px;
  box-shadow:0 8px 40px rgba(0,0,0,0.2); overflow:hidden; cursor:move; user-select:none; }
.ai-dialog.minimized { height:auto; }
.ai-dialog-header { display:flex; justify-content:space-between; align-items:center;
  padding:12px 16px; background:linear-gradient(135deg,#667eea,#764ba2); color:#fff;
  font-weight:600; }
.ai-dialog-header span { cursor:default; }
.ai-dialog-actions span { margin-left:12px; cursor:pointer; opacity:0.8; font-size:16px; }
.ai-dialog-actions span:hover { opacity:1; }
.ai-dialog-body { padding:16px; max-height:420px; overflow-y:auto; }
.ai-slide-enter-active { animation: aiIn 0.3s ease; }
.ai-slide-leave-active { animation: aiIn 0.2s ease reverse; }
@keyframes aiIn { from{opacity:0;transform:scale(0.9)} to{opacity:1;transform:scale(1)} }
/* 悬浮聊天框 */
.float-chat { position:fixed; z-index:1001; width:360px; height:440px; background:#fff; border-radius:16px;
  box-shadow:0 12px 48px rgba(0,0,0,0.2); display:flex; flex-direction:column; overflow:hidden; }
.float-chat-header { display:flex; align-items:center; gap:8px;
  padding:10px 14px; background:linear-gradient(135deg,#667eea,#764ba2); color:#fff; font-weight:600; font-size:13px; cursor:move; }
.float-chat-header span:first-child { flex:0; }
.float-chat-btn { cursor:pointer; opacity:0.8; font-size:14px; padding:2px 4px; }
.float-chat-btn:hover { opacity:1; }
.float-chat-close:hover { color:#ff6b6b; }
.float-chat-body { flex:1; overflow-y:auto; padding:12px; display:flex; flex-direction:column; gap:8px; }
.float-chat-empty { text-align:center; padding:20px; color:#909399; }
.float-chat-empty p { margin:8px 0 14px; }
.float-quick-asks { display:flex; flex-wrap:wrap; gap:6px; justify-content:center; }
.float-quick-asks span { background:#f0f2f5; padding:6px 12px; border-radius:14px; font-size:11px; cursor:pointer; color:#606266; transition:all 0.15s; }
.float-quick-asks span:hover { background:#e0e4e8; color:#303133; }
.float-msg { max-width:85%; padding:8px 12px; border-radius:14px; font-size:13px; line-height:1.5; word-break:break-word; animation:msgIn 0.2s ease; }
.float-msg-user { background:linear-gradient(135deg,#667eea,#764ba2); color:#fff; align-self:flex-end; border-bottom-right-radius:4px; }
.float-msg-ai { background:#f0f2f5; color:#303133; align-self:flex-start; border-bottom-left-radius:4px; }
@keyframes msgIn { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:translateY(0)} }
.float-chat-input { display:flex; padding:10px 12px; gap:8px; border-top:1px solid #eee; }
.float-chat-input input { flex:1; border:1px solid #e0e0e0; border-radius:20px; padding:8px 14px; font-size:13px; outline:none; transition:border 0.2s; }
.float-chat-input input:focus { border-color:#667eea; }
.float-chat-input button { width:32px; height:32px; border-radius:50%; border:none; background:linear-gradient(135deg,#667eea,#764ba2); color:#fff; font-size:12px; cursor:pointer; transition:transform 0.15s; flex-shrink:0; }
.float-chat-input button:hover { transform:scale(1.1); }
.float-chat-input button:disabled { opacity:0.5; transform:none; }
.mini-quota { font-size:10px; opacity:0.85; background:rgba(255,255,255,0.2); padding:2px 8px; border-radius:10px; flex:1; text-align:center; }
/* 详情按钮（防误触整卡跳转） */
.detail-btn { font-size:12px; color:#409EFF; cursor:pointer; padding:2px 8px; border-radius:12px; background:rgba(64,158,255,0.08); transition:all 0.15s; }
.detail-btn:hover { background:rgba(64,158,255,0.2); color:#337ecc; }
/* 最近记录内嵌当前坐姿状态条 */
.posture-status-inline {
  margin-top: 10px; padding: 10px 14px;
  background: linear-gradient(135deg, rgba(245,108,108,0.1), rgba(245,108,108,0.05));
  border: 1px solid rgba(245,108,108,0.3);
  border-radius: 10px;
  display: flex; align-items: center; gap: 10px;
  font-size: 14px; font-weight: 600; color: #f56c6c;
  animation: statusPulse 2s ease-in-out infinite;
}
.status-inline-icon { font-size: 22px; }
.status-inline-text { line-height: 1.5; }
@keyframes statusPulse {
  0%, 100% { border-color: rgba(245,108,108,0.2); }
  50% { border-color: rgba(245,108,108,0.6); }
}
/* 最近记录 */
.recent-list { max-height: 220px; overflow-y: auto; }
.recent-row { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid #f5f5f5; font-size: 13px; }
.recent-row:last-child { border-bottom: none; }
.recent-time { color: #909399; font-family: monospace; min-width: 60px; }
.recent-status { font-weight: 600; flex: 1; margin: 0 8px; }
.recent-val { color: #303133; font-weight: 700; }

</style>
