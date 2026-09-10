<template>
  <main class="login-page">
    <section class="login-shell">
      <div class="product-panel">
        <div class="brand-row">
          <div class="brand-mark">
            <el-icon size="26"><TrendCharts /></el-icon>
          </div>
          <div>
            <h1>Crossborder Ops Agent</h1>
            <p>跨境电商经营数据智能分析</p>
          </div>
        </div>

        <div class="metrics-strip">
          <div>
            <strong>订单</strong>
            <span>利润 / 趋势 / 店铺</span>
          </div>
          <div>
            <strong>广告</strong>
            <span>ACOS / ROAS</span>
          </div>
          <div>
            <strong>售后</strong>
            <span>退款 / 差评 / SKU</span>
          </div>
        </div>
      </div>

      <div class="login-card">
        <h2>运营账号登录</h2>
        <p class="card-desc">选择课堂演示账号，进入跨境经营分析工作台。</p>

        <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="handleLogin">
          <el-form-item label="运营账号 ID" prop="operatorId">
            <el-input
              v-model="form.operatorId"
              type="number"
              placeholder="例如 1、2、3"
              size="large"
              :prefix-icon="User"
              @keyup.enter="handleLogin"
            />
          </el-form-item>

          <el-button type="primary" size="large" :loading="loading" class="login-btn" @click="handleLogin">
            {{ loading ? '登录中...' : '进入工作台' }}
          </el-button>
        </el-form>

        <div class="demo-list">
          <span>演示账号</span>
          <button v-for="demo in demoAccounts" :key="demo.operatorId" @click="quickLogin(demo)">
            {{ demo.label }}
          </button>
        </div>
      </div>
    </section>

    <p class="footer-tip">Spring Boot · LangChain4j · Vue 3 · ECharts</p>
  </main>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { TrendCharts, User } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const formRef = ref(null)
const loading = ref(false)
const form = reactive({ operatorId: '' })

const rules = {
  operatorId: [{ required: true, message: '请输入运营账号 ID', trigger: 'blur' }],
}

const demoAccounts = [
  { label: 'Olivia 一线运营', operatorId: 1 },
  { label: 'Mia 店长', operatorId: 2 },
  { label: 'Alex 运营总监', operatorId: 3 },
]

function quickLogin(demo) {
  form.operatorId = demo.operatorId
  handleLogin()
}

async function handleLogin() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    await auth.login(Number(form.operatorId))
    ElMessage.success('登录成功')
    router.push('/')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #0f172a 0%, #172033 52%, #0b3b43 100%);
  color: #fff;
  padding: 24px;
}

.login-shell {
  width: min(920px, 100%);
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.06);
  box-shadow: 0 28px 80px rgba(0, 0, 0, 0.35);
}

.product-panel {
  padding: 44px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  min-height: 430px;
}

.brand-row {
  display: flex;
  gap: 16px;
  align-items: center;
}

.brand-mark {
  width: 56px;
  height: 56px;
  display: grid;
  place-items: center;
  background: #0891b2;
  color: #fff;
}

h1 {
  font-size: 28px;
  line-height: 1.2;
  margin: 0;
}

.brand-row p,
.card-desc,
.footer-tip {
  color: rgba(255, 255, 255, 0.68);
}

.metrics-strip {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.metrics-strip div {
  border-left: 3px solid #22d3ee;
  padding-left: 12px;
}

.metrics-strip strong,
.metrics-strip span {
  display: block;
}

.metrics-strip span {
  color: rgba(255, 255, 255, 0.64);
  font-size: 13px;
  margin-top: 4px;
}

.login-card {
  background: #f8fafc;
  color: #111827;
  padding: 44px 36px;
}

.login-card h2 {
  margin: 0 0 8px;
  font-size: 22px;
}

.card-desc {
  color: #64748b;
  margin-bottom: 28px;
}

.login-btn {
  width: 100%;
  height: 44px;
  background: #0f766e;
  border-color: #0f766e;
}

.demo-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 22px;
  padding-top: 20px;
  border-top: 1px solid #e2e8f0;
}

.demo-list span {
  width: 100%;
  color: #64748b;
  font-size: 12px;
}

.demo-list button {
  border: 1px solid #cbd5e1;
  background: #fff;
  color: #334155;
  padding: 7px 10px;
  cursor: pointer;
}

.demo-list button:hover {
  border-color: #0f766e;
  color: #0f766e;
}

.footer-tip {
  margin-top: 18px;
  font-size: 12px;
}

@media (max-width: 760px) {
  .login-shell {
    grid-template-columns: 1fr;
  }

  .product-panel {
    min-height: 260px;
    padding: 28px;
  }

  .metrics-strip {
    grid-template-columns: 1fr;
  }
}
</style>
