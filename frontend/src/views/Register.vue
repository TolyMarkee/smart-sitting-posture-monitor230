<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../store/user'

const router = useRouter()
const userStore = useUserStore()
const formRef = ref(null)

const form = ref({ username: '', email: '', password: '', password2: '' })
const loading = ref(false)

function validatePass(rule, value, callback) {
  if (value !== form.value.password) {
    callback(new Error('两次密码输入不一致'))
  } else {
    callback()
  }
}

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 2, message: '用户名至少2个字符', trigger: 'blur' },
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' },
  ],
  password2: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: validatePass, trigger: 'blur' },
  ],
}

async function handleRegister() {
  if (!formRef.value) return
  try { await formRef.value.validate() } catch { return }

  loading.value = true
  try {
    await userStore.register(form.value.username, form.value.email, form.value.password)
    ElMessage.success({ message: '注册成功，请登录', center: true })
    router.push('/login')
  } catch (e) {
    ElMessage.error({ message: e?.response?.data?.detail || '注册失败，请稍后重试', center: true })
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="bg-shapes">
      <div class="shape shape-1"></div>
      <div class="shape shape-2"></div>
      <div class="shape shape-3"></div>
    </div>

    <div class="login-card">
      <div class="card-brand">
        <div class="brand-icon">
          <svg viewBox="0 0 24 24" width="36" height="36" fill="none" stroke="currentColor" stroke-width="1.5">
            <circle cx="12" cy="7" r="4"/>
            <path d="M5.5 21c0-4.4 3.1-8 6.5-8s6.5 3.6 6.5 8"/>
            <line x1="12" y1="11" x2="12" y2="17" stroke-width="2" stroke-linecap="round"/>
          </svg>
        </div>
        <h1>创建账号</h1>
        <p>加入智能坐姿监测系统</p>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        @submit.prevent="handleRegister"
        class="login-form"
      >
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="用户名" size="large" clearable />
        </el-form-item>

        <el-form-item prop="email">
          <el-input v-model="form.email" placeholder="邮箱地址" size="large" clearable />
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码（至少6位）"
            size="large"
            show-password
          />
        </el-form-item>

        <el-form-item prop="password2">
          <el-input
            v-model="form.password2"
            type="password"
            placeholder="确认密码"
            size="large"
            show-password
            @keyup.enter="handleRegister"
          />
        </el-form-item>

        <el-button
          type="primary"
          size="large"
          :loading="loading"
          class="login-btn"
          native-type="submit"
          round
        >
          {{ loading ? '注册中...' : '注 册' }}
        </el-button>
      </el-form>

      <div class="card-footer">
        已有账号？<router-link to="/login">返回登录</router-link>
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
  padding: 36px 40px 28px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  border-radius: 20px;
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.25);
}

.card-brand { text-align: center; margin-bottom: 24px; }

.brand-icon {
  width: 56px; height: 56px;
  margin: 0 auto 12px;
  border-radius: 16px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: #fff;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 8px 24px rgba(102, 126, 234, 0.4);
}

.card-brand h1 { margin: 0 0 4px; font-size: 20px; color: #1a1a2e; font-weight: 700; }
.card-brand p { margin: 0; font-size: 12px; color: #909399; letter-spacing: 2px; text-transform: uppercase; }

.login-form :deep(.el-form-item) { margin-bottom: 16px; }
.login-form :deep(.el-form-item__label) { font-size: 13px; padding-bottom: 2px; }

.login-btn { width: 100%; height: 44px; font-size: 16px; letter-spacing: 4px; margin-top: 4px; }

.card-footer { text-align: center; font-size: 14px; color: #909399; padding-top: 14px; border-top: 1px solid #f0f0f0; margin-top: 4px; }
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
