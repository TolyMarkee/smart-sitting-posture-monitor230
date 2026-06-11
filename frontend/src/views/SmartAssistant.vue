<script setup>
import PageTitle from "../components/PageTitle.vue"
import { ref, nextTick, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { chatApi } from '../api/chat'
import { useUserStore } from '../store/user'
import { useAiPet } from '../composables/useAiPet'

const userStore = useUserStore()
const { currentPet, switchPet: globalSwitch } = useAiPet()
const petAvatar = computed(() => '/pets/' + currentPet.value + '.png')

const allPetDefs = [
  { id: 'cat', name: '小猫', img: '/pets/cat.png' },
  { id: 'dog', name: '小狗', img: '/pets/dog.png' },
  { id: 'fox', name: '狐狸', img: '/pets/fox.png' },
  { id: 'hamster', name: '仓鼠', img: '/pets/hamster.png' },
  { id: 'neko', name: '猫娘', img: '/pets/neko.png' },
]
const ownedPets = computed(() => JSON.parse(localStorage.getItem('owned_pets') || '["cat"]'))
const ownedPetList = computed(() => allPetDefs.filter(p => ownedPets.value.includes(p.id)))
function switchPet(id) { globalSwitch(id); ElMessage.success('已切换伙伴') }

const DEFAULT_WELCOME = {
  role: 'assistant',
  content: '你好！我是你的坐姿健康助手 AI。我可以帮你：\n\n\u2022 解读你的坐姿监测数据\n\u2022 分析头部前倾、驼背、高低肩等问题\n\u2022 提供科学的坐姿矫正建议\n\u2022 推荐适合的锻炼方式\n\n请问有什么可以帮你的？',
  time: new Date().toLocaleTimeString('zh-CN', { hour12: false }),
}

const messages = ref([{ ...DEFAULT_WELCOME }])
const input = ref('')
const loading = ref(false)
const chatBox = ref(null)
const copyIdx = ref(-1)

// 次数和积分
const quotaLeft = ref(30)
const userPoints = ref(0)
const DAILY_LIMIT = 30

async function loadQuota() {
  const uid = userStore.userInfo?.user_id
  if (!uid) return
  try {
    // 获取积分
    const { data: profileData } = await import('../api/request').then(m => m.default.get('/api/v1/auth/profile'))
    userPoints.value = profileData?.points || 0
  } catch {}
  try {
    // 获取今日已用次数
    const { data: quotaData } = await import('../api/request').then(m => m.default.get('/api/v1/chat/quota', { params: { user_id: uid } }))
    quotaLeft.value = Math.max(0, DAILY_LIMIT - (quotaData?.used || 0))
  } catch { quotaLeft.value = DAILY_LIMIT }
}

// 加载历史聊天记录（从数据库恢复）
async function loadHistory() {
  const uid = userStore.userInfo?.user_id
  if (!uid) return
  try {
    const { data } = await chatApi.getHistory(uid, 200)
    if (data.messages && data.messages.length > 0) {
      messages.value = data.messages
    }
  } catch { /* 忽略，使用默认欢迎语 */ }
}

onMounted(() => { loadHistory(); loadQuota() })

function scrollBottom() {
  nextTick(() => {
    if (chatBox.value) {
      chatBox.value.scrollTop = chatBox.value.scrollHeight
    }
  })
}

async function send(text) {
  const msg = (text || input.value).trim()
  if (!msg || loading.value) return

  const now = new Date().toLocaleTimeString('zh-CN', { hour12: false })
  messages.value.push({ role: 'user', content: msg, time: now })
  input.value = ''
  loading.value = true
  scrollBottom()

  const history = messages.value
    .filter((m) => m.role !== 'assistant' || m.content.length > 0)
    .slice(-20)
    .map((m) => ({ role: m.role, content: m.content }))

  const uid = userStore.userInfo?.user_id || 1
  try {
    const { data } = await chatApi.sendMessage(msg, history.slice(0, -1), uid)
    const reply = data.reply
    const ctx = data.posture_context
    // 如果有数据上下文，在回复前显示
    const fullReply = ctx
      ? `📊 *已读取你的最新坐姿数据*\\n\\n${reply}`
      : reply
    messages.value.push({
      role: 'assistant',
      content: fullReply,
      time: new Date().toLocaleTimeString('zh-CN', { hour12: false }),
    })
  } catch {
    messages.value.push({
      role: 'assistant',
      content: '抱歉，AI 服务暂不可用。\n\n请检查：\n1. 是否已配置 LLM_API_KEY\n2. API 地址是否正确\n3. 网络是否可达',
      time: new Date().toLocaleTimeString('zh-CN', { hour12: false }),
      error: true,
    })
  } finally {
    loading.value = false
    scrollBottom()
  }
}

function quickAsk(q) {
  send(q)
}

function copyMessage(idx) {
  const text = messages.value[idx]?.content || ''
  navigator.clipboard.writeText(text).then(() => {
    copyIdx.value = idx
    ElMessage.success('已复制')
    setTimeout(() => (copyIdx.value = -1), 2000)
  }).catch(() => {
    ElMessage.error('复制失败')
  })
}

function clearChat() {
  messages.value = [messages.value[0]]
  ElMessage.success('对话已清空')
}
</script>

<template>
  <div class="chat-page">
    <div class="chat-topbar">
      <div class="chat-topbar-left">
        <PageTitle>坐姿健康助手</PageTitle>
        <router-link to="/shop" class="chat-shop-link">🛒 积分商城</router-link>
      </div>
      <div class="chat-quota">
        今日剩余 <b>{{ quotaLeft }}</b> 次 · 积分 <b>{{ userPoints }}</b>
      </div>
    </div>
    <div class="chat-container">
      <!-- 头部 -->
      <div class="chat-header">
        <div class="header-main">
          <div class="ai-avatar-lg">
            <img :src="petAvatar" class="avatar-pet-img" alt="AI宠物" />
          </div>
          <div class="header-text">
            <h3 class="chat-title">坐姿健康助手</h3>
            <div class="header-status">
              <span class="status-dot"></span>
              AI 在线 · {{ messages.length }} 条消息
            </div>
          </div>
        </div>
        <el-button text circle @click="clearChat" title="清空对话">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3,6 5,6 21,6"/><path d="M19,6v14a2,2,0,0,1-2,2H7a2,2,0,0,1-2-2V6M8,6V4a2,2,0,0,1,2-2h4a2,2,0,0,1,2,2V6"/>
          </svg>
        </el-button>
      </div>

      <!-- 消息区 -->
      <div class="chat-messages" ref="chatBox">
        <div
          v-for="(msg, idx) in messages"
          :key="idx"
          :class="['msg-wrapper', msg.role === 'user' ? 'msg-right' : 'msg-left']"
        >
          <!-- 助手头像 -->
          <div v-if="msg.role === 'assistant'" class="avatar avatar-ai">
            <img :src="petAvatar" class="avatar-pet-img" alt="AI" />
          </div>

          <div class="msg-content">
            <div
              :class="['msg-bubble', {
                'bubble-user': msg.role === 'user',
                'bubble-ai': msg.role === 'assistant',
                'bubble-error': msg.error,
              }]"
            >
              <div class="msg-text" v-text="msg.content"></div>
              <div class="msg-meta">
                <span class="msg-time">{{ msg.time }}</span>
                <button
                  v-if="msg.role === 'assistant'"
                  class="btn-copy"
                  @click="copyMessage(idx)"
                  :title="copyIdx === idx ? '已复制' : '复制'"
                >
                  <svg v-if="copyIdx !== idx" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5,15H4a2,2,0,0,1-2-2V4A2,2,0,0,1,4,2h9a2,2,0,0,1,2,2V5"/>
                  </svg>
                  <svg v-else viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="#67c23a" stroke-width="2.5">
                    <polyline points="20,6 9,17 4,12"/>
                  </svg>
                </button>
              </div>
            </div>
          </div>

          <!-- 用户头像 -->
          <div v-if="msg.role === 'user'" class="avatar avatar-user">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5">
              <circle cx="12" cy="8" r="4"/><path d="M4,20c0-4.4,3.6-8,8-8s8,3.6,8,8"/>
            </svg>
          </div>
        </div>

        <!-- 加载动画 -->
        <div v-if="loading" class="msg-wrapper msg-left">
          <div class="avatar avatar-ai">
            <img :src="petAvatar" class="avatar-pet-img" alt="AI" />
          </div>
          <div class="msg-content">
            <div class="msg-bubble bubble-ai">
              <div class="typing-dots">
                <span></span><span></span><span></span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 快捷提问 -->
      <div class="quick-bar">
        <span class="quick-label">快捷提问：</span>
        <el-tag
          v-for="q in ['我现在坐姿怎么样？', '帮我分析一下坐姿数据', '头部前倾怎么改善？', '驼背含胸如何矫正？']"
          :key="q"
          class="quick-tag"
          @click="quickAsk(q)"
          effect="plain"
        >
          {{ q }}
        </el-tag>
      </div>

      <!-- 输入区 -->
      <div class="input-bar">
        <el-input
          v-model="input"
          placeholder="输入你的健康问题，按 Enter 发送..."
          size="large"
          @keyup.enter="send()"
          :disabled="loading"
          class="input-field"
          maxlength="500"
          show-word-limit
        />
        <el-button
          type="primary"
          size="large"
          :loading="loading"
          :disabled="!input.trim()"
          @click="send()"
          class="btn-send"
        >
          <template v-if="!loading">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22,2 15,22 11,13 2,9"/>
            </svg>
          </template>
        </el-button>
      </div>

      <!-- 伙伴切换 -->
      <div class="pet-switch-row">
        <img v-for="p in ownedPetList" :key="p.id" :src="p.img"
          :class="{ active: currentPet.value === p.id }"
          @click="switchPet(p.id)" :title="p.name" class="pet-switch-img" />
      </div>
      <div class="disclaimer">
        内容由 AI 生成，仅供参考，不能替代专业医疗诊断
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-page {
  padding: 20px 24px; width: 100%; min-height: 100vh;
  display: flex; flex-direction: column;
  background: #f0f2f5;
}
/* 顶部导航条 */
.chat-topbar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; gap: 16px; }
.chat-topbar-left { display: flex; align-items: center; gap: 12px; }
.chat-shop-link { font-size: 13px; color: #409EFF; text-decoration: none; padding: 4px 12px; border-radius: 6px; background: rgba(64,158,255,0.06); transition: all 0.15s; }
.chat-shop-link:hover { background: rgba(64,158,255,0.15); }
.chat-quota { font-size: 12px; color: #909399; }
.chat-quota b { color: #409EFF; }

.chat-title { font-size: 18px; font-weight: 800; margin: 0; letter-spacing: 0.5px; color: #3a4452;
  text-shadow: 0 1px 1px rgba(255,255,255,0.95), 0 -0.5px 0 rgba(0,0,0,0.06), 0 2px 3px rgba(0,0,0,0.04); }
.chat-container {
  width: 100%; margin: 0; flex: 1; display: flex; flex-direction: column;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06);
}

/* header */
.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid #f0f0f0;
  background: #fafbfc;
}

.header-main {
  display: flex;
  align-items: center;
  gap: 12px;
}

.ai-avatar-lg {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
}

.header-text h3 {
  margin: 0;
  font-size: 17px;
  font-weight: 600;
}

.header-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #67c23a;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

/* messages */
.chat-messages {
  flex: 1;
  padding: clamp(14px, 2.5vw, 28px);
  overflow-y: auto;
  max-height: 52vh;
  min-height: 320px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  background: #fff;
}

.msg-wrapper {
  display: flex;
  gap: 10px;
  max-width: 88%;
  animation: fadeIn 0.25s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}

.msg-left { align-self: flex-start; }
.msg-right { align-self: flex-end; flex-direction: row-reverse; }

.avatar {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.avatar-ai {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: #fff;
}

.avatar-user {
  background: #e8eaed;
  color: #5f6368;
}

.msg-content { min-width: 0; }

.msg-bubble {
  padding: 10px 14px;
  border-radius: 14px;
  font-size: 14px;
  line-height: 1.65;
  white-space: pre-wrap;
  word-break: break-word;
}

.bubble-user {
  background: #667eea;
  color: #fff;
  border-bottom-right-radius: 4px;
}

.bubble-ai {
  background: #f4f5f7;
  color: #303133;
  border-bottom-left-radius: 4px;
}

.bubble-error {
  background: #fef0f0;
  border: 1px solid #fde2e2;
}

.msg-text { margin-bottom: 6px; }

.msg-meta {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
}

.msg-time {
  font-size: 11px;
  opacity: 0.5;
}

.btn-copy {
  background: none;
  border: none;
  cursor: pointer;
  padding: 2px;
  opacity: 0;
  transition: opacity 0.15s;
  color: inherit;
}

.msg-bubble:hover .btn-copy { opacity: 0.7; }
.btn-copy:hover { opacity: 1 !important; }

/* typing */
.typing-dots {
  display: flex;
  gap: 4px;
  padding: 4px 0;
}

.typing-dots span {
  width: 7px;
  height: 7px;
  background: #c0c4cc;
  border-radius: 50%;
  animation: bounce 1.2s ease-in-out infinite;
}

.typing-dots span:nth-child(2) { animation-delay: 0.2s; }
.typing-dots span:nth-child(3) { animation-delay: 0.4s; }

@keyframes bounce {
  0%, 60%, 100% { transform: translateY(0); }
  30% { transform: translateY(-6px); }
}

/* quick bar */
.quick-bar {
  padding: 10px 20px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  border-top: 1px solid #f5f5f5;
}

.quick-label {
  font-size: 12px;
  color: #909399;
  white-space: nowrap;
}

.quick-tag {
  cursor: pointer;
  transition: all 0.15s;
}

.quick-tag:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

/* input bar */
.input-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 20px;
  border-top: 1px solid #f0f0f0;
}

.input-field { flex: 1; }

.btn-send {
  width: 44px;
  height: 44px;
  padding: 0;
  border-radius: 12px;
}

/* disclaimer */
.disclaimer {
  text-align: center;
  padding: 10px;
  font-size: 11px;
  color: #c0c4cc;
  background: #fafbfc;
  border-top: 1px solid #f5f5f5;
}
.avatar-pet-img { width: 100%; height: 100%; object-fit: contain; image-rendering: pixelated; }
.pet-switch-row { display: flex; gap: 8px; padding: 10px 0; justify-content: center; }
.pet-switch-img { width: 36px; height: auto; image-rendering: pixelated; border-radius: 8px; cursor: pointer; padding: 2px; border: 2px solid transparent; transition: all 0.15s; }
.pet-switch-img:hover { transform: scale(1.15); }
.pet-switch-img.active { border-color: #667eea; background: rgba(102,126,234,0.1); }
</style>
