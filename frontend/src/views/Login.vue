<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../store/user'

const router = useRouter()
const userStore = useUserStore()
const formRef = ref(null)

const form = ref({ username: '', password: '' })
const remember = ref(false)
const loading = ref(false)

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 2, message: '用户名至少2个字符', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少6位', trigger: 'blur' },
  ],
}

async function handleLogin() {
  if (!formRef.value) return
  try { await formRef.value.validate() } catch { return }

  loading.value = true
  try {
    await userStore.login(form.value.username, form.value.password)
    if (remember.value) {
      localStorage.setItem('saved_username', form.value.username)
    } else {
      localStorage.removeItem('saved_username')
    }
    ElMessage.success({ message: '登录成功，欢迎回来！', center: true })
    router.push('/dashboard')
  } catch (e) {
    ElMessage.error({ message: e?.response?.data?.detail || '用户名或密码错误', center: true })
  } finally {
    loading.value = false
  }
}

// 恢复记住的用户名
const savedUser = localStorage.getItem('saved_username')
if (savedUser) {
  form.value.username = savedUser
  remember.value = true
}
</script>

<template>
  <div class="login-page">
    <!-- 背景装饰 -->
    <div class="bg-shapes">
      <div class="shape shape-1"></div>
      <div class="shape shape-2"></div>
      <div class="shape shape-3"></div>
    </div>

    <div class="login-card">
      <!-- Logo 区 -->
      <div class="card-brand">
        <div class="brand-icon">
          <svg viewBox="0 0 24 24" width="36" height="36" fill="none" stroke="currentColor" stroke-width="1.5">
            <circle cx="12" cy="7" r="4"/>
            <path d="M5.5 21c0-4.4 3.1-8 6.5-8s6.5 3.6 6.5 8"/>
            <line x1="12" y1="11" x2="12" y2="17" stroke-width="2" stroke-linecap="round"/>
            <line x1="9" y1="14" x2="15" y2="14" stroke-width="2" stroke-linecap="round"/>
          </svg>
        </div>
        <h1>智能坐姿监测</h1>
        <p>Smart Sitting Posture Monitor</p>
      </div>

      <!-- 表单 -->
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        @submit.prevent="handleLogin"
        class="login-form"
      >
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            placeholder="用户名"
            size="large"
            clearable
          />
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码"
            size="large"
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>

        <div class="form-extra">
          <el-checkbox v-model="remember" size="small">记住用户名</el-checkbox>
        </div>

        <el-button
          type="primary"
          size="large"
          :loading="loading"
          class="login-btn"
          native-type="submit"
          round
        >
          {{ loading ? '登录中...' : '登 录' }}
        </el-button>
      </el-form>

      <div class="card-footer">
        还没有账号？<router-link to="/register">立即注册</router-link>
      </div>
    </div>

  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  position: relative;
  overflow: hidden;
}

/* 背景装饰 */
.bg-shapes { position: absolute; inset: 0; z-index: 0; }
.shape {
  position: absolute; border-radius: 50%;
  background: rgba(102, 126, 234, 0.08);
  animation: float 20s ease-in-out infinite;
}
.shape-1 { width: 500px; height: 500px; top: -200px; right: -100px; animation-delay: 0s; }
.shape-2 { width: 300px; height: 300px; bottom: -100px; left: -80px; animation-delay: -7s; }
.shape-3 { width: 200px; height: 200px; top: 40%; left: 60%; animation-delay: -14s; }

@keyframes float {
  0%, 100% { transform: translate(0, 0) rotate(0deg); }
  33% { transform: translate(30px, -30px) rotate(120deg); }
  66% { transform: translate(-20px, 20px) rotate(240deg); }
}

.login-card {
  position: relative; z-index: 1;
  width: 420px;
  padding: 44px 40px 32px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.25);
}

.card-brand { text-align: center; margin-bottom: 32px; }

.brand-icon {
  width: 64px; height: 64px;
  margin: 0 auto 16px;
  border-radius: 18px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: #fff;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 8px 24px rgba(102, 126, 234, 0.4);
}

.card-brand h1 { margin: 0 0 4px; font-size: 22px; color: #1a1a2e; font-weight: 700; }
.card-brand p { margin: 0; font-size: 12px; color: #909399; letter-spacing: 2px; text-transform: uppercase; }

.login-form { margin-bottom: 8px; }

.form-extra { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }

.login-btn { width: 100%; height: 44px; font-size: 16px; letter-spacing: 4px; }

.card-footer { text-align: center; font-size: 14px; color: #909399; padding-top: 16px; border-top: 1px solid #f0f0f0; }
.card-footer a { color: #667eea; text-decoration: none; font-weight: 600; margin-left: 4px; }
.card-footer a:hover { text-decoration: underline; }

.login-footer-text {
  position: relative; z-index: 1;
  margin-top: 24px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.35);
  letter-spacing: 1px;
}
</style>
