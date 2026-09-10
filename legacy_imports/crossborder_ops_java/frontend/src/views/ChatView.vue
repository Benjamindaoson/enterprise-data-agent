<template>
  <div class="chat-layout">
    <aside :class="['sidebar', { collapsed: sidebarCollapsed }]">
      <div class="sidebar-brand">
        <div class="brand-logo">
          <el-icon size="18"><TrendCharts /></el-icon>
        </div>
        <span v-if="!sidebarCollapsed" class="brand-text">Crossborder Ops</span>
        <button class="icon-btn" @click="sidebarCollapsed = !sidebarCollapsed">
          <el-icon size="14"><component :is="sidebarCollapsed ? Expand : Fold" /></el-icon>
        </button>
      </div>

      <div class="sidebar-new">
        <button class="new-chat-btn" @click="newChat" :title="sidebarCollapsed ? '新会话' : ''">
          <el-icon size="15"><Plus /></el-icon>
          <span v-if="!sidebarCollapsed">新会话</span>
        </button>
      </div>

      <div v-if="!sidebarCollapsed" class="session-list">
        <p class="list-label">历史对话</p>
        <div
          v-for="session in chat.sessions"
          :key="session.id"
          :class="['session-item', { active: session.id === chat.activeSessionId }]"
          @click="chat.switchSession(session.id)"
        >
          <el-icon size="13"><ChatLineRound /></el-icon>
          <span class="session-title">{{ session.title }}</span>
          <button class="del-btn" title="删除" @click.stop="confirmDelete(session.id)">
            <el-icon size="12"><Delete /></el-icon>
          </button>
        </div>
        <div v-if="chat.sessions.length === 0" class="empty-sessions">暂无对话记录</div>
      </div>

      <div v-if="!sidebarCollapsed" class="quick-section">
        <p class="list-label">快捷提问</p>
        <button v-for="q in quickQuestions" :key="q.text" class="quick-item" @click="sendQuick(q.text)">
          <el-icon size="14"><component :is="q.icon" /></el-icon>
          <span>{{ q.text }}</span>
        </button>
      </div>

      <div :class="['sidebar-user', { collapsed: sidebarCollapsed }]">
        <div class="user-avatar">{{ userInitial }}</div>
        <div v-if="!sidebarCollapsed" class="user-meta">
          <p class="user-name">{{ auth.userInfo?.username }}</p>
          <p class="user-role">{{ roleLabel }}</p>
        </div>
        <button v-if="!sidebarCollapsed" class="logout-btn" title="退出" @click="auth.logout()">
          <el-icon size="14"><SwitchButton /></el-icon>
        </button>
      </div>
    </aside>

    <main class="chat-main">
      <header class="chat-header">
        <div class="header-left">
          <div class="header-icon">
            <el-icon size="18"><Cpu /></el-icon>
          </div>
          <div>
            <h2>企业经营数据智能分析 Agent</h2>
            <p>订单利润、广告 ACOS、退款风险、评论洞察、Listing 优化</p>
          </div>
        </div>
        <div class="header-right">
          <el-tag v-if="chat.isStreaming" type="success" size="small">
            <el-icon class="spinning"><Loading /></el-icon>
            分析中
          </el-tag>
          <el-button v-if="chat.activeSession" size="small" plain :icon="Delete" @click="clearCurrentSession">
            清空记忆
          </el-button>
        </div>
      </header>

      <div ref="messagesEl" class="messages-container">
        <section v-if="!chat.activeSession || chat.activeSession.messages.length === 0" class="welcome">
          <div class="welcome-icon">
            <el-icon size="34"><TrendCharts /></el-icon>
          </div>
          <h3>你好，{{ auth.userInfo?.username }}</h3>
          <p>直接询问店铺经营情况，系统会调用后端工具读取演示数据，并在需要时生成 ECharts 图表。</p>
          <div class="welcome-grid">
            <button v-for="card in welcomeCards" :key="card.text" @click="sendQuick(card.text)">
              <el-icon size="20"><component :is="card.icon" /></el-icon>
              <span>{{ card.text }}</span>
            </button>
          </div>
        </section>

        <div v-else class="message-list">
          <MessageBubble v-for="msg in chat.activeSession.messages" :key="msg.id" :msg="msg" />
        </div>
      </div>

      <footer class="input-area">
        <div class="input-row">
          <el-input
            v-model="inputText"
            type="textarea"
            :autosize="{ minRows: 1, maxRows: 5 }"
            placeholder="例如：分析最近 30 天 Amazon US Store 的经营概览，并画出近 6 个月趋势图"
            resize="none"
            class="chat-input"
            :disabled="chat.isStreaming"
            @keydown.enter.exact.prevent="handleSend"
          />
          <el-button
            v-if="chat.isStreaming"
            type="danger"
            :icon="VideoPause"
            circle
            class="send-circle"
            @click="chat.stopStreaming()"
          />
          <el-button
            v-else
            type="primary"
            :icon="Promotion"
            circle
            class="send-circle"
            :disabled="!inputText.trim()"
            @click="handleSend"
          />
        </div>
        <p>演示数据用于教学，真实上线需接入订单、广告、评论和库存数据源。</p>
      </footer>
    </main>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import {
  TrendCharts, Plus, ChatLineRound, Delete, SwitchButton, Cpu, Promotion,
  VideoPause, Loading, Fold, Expand, DataLine, Warning, Tickets, EditPen,
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { useChatStore } from '@/stores/chat'
import { agentApi } from '@/api'
import MessageBubble from '@/components/MessageBubble.vue'

const auth = useAuthStore()
const chat = useChatStore()
const inputText = ref('')
const messagesEl = ref(null)
const sidebarCollapsed = ref(false)

const userInitial = computed(() => (auth.userInfo?.username || 'U').slice(0, 1))

const roleLabel = computed(() => {
  const map = {
    OPERATOR: '一线运营',
    STORE_MANAGER: '店长',
    OPERATIONS_DIRECTOR: '运营总监',
  }
  return map[auth.userInfo?.role] || auth.userInfo?.role || '运营账号'
})

const quickQuestions = [
  { icon: DataLine, text: '分析最近30天的经营概览' },
  { icon: TrendCharts, text: '画出近6个月净销售额和利润趋势图' },
  { icon: Warning, text: '找出ACOS偏高的广告活动' },
  { icon: Tickets, text: '哪些SKU退款风险最高？' },
  { icon: EditPen, text: '给 EB-US-1001 生成 Amazon US Listing 优化草案' },
]

const welcomeCards = [
  { icon: DataLine, text: '最近30天全公司经营概览' },
  { icon: TrendCharts, text: 'Amazon US Store 近6个月趋势图' },
  { icon: Warning, text: '广告ACOS异常活动排查' },
  { icon: Tickets, text: '近期低星评论主题分析' },
]

function scrollToBottom(smooth = true) {
  nextTick(() => {
    messagesEl.value?.scrollTo({
      top: messagesEl.value.scrollHeight,
      behavior: smooth ? 'smooth' : 'instant',
    })
  })
}

watch(() => chat.activeSession?.messages?.length, () => scrollToBottom())
watch(
  () => chat.activeSession?.messages?.at(-1)?.content || '',
  () => scrollToBottom(false),
)

async function handleSend() {
  const text = inputText.value.trim()
  if (!text || chat.isStreaming) return
  inputText.value = ''
  if (!chat.activeSession) chat.createSession()
  await chat.sendMessage(text)
}

function sendQuick(text) {
  if (chat.isStreaming) return
  if (!chat.activeSession) chat.createSession()
  chat.sendMessage(text)
}

function newChat() {
  chat.createSession()
}

function confirmDelete(sessionId) {
  ElMessageBox.confirm('确认删除这条对话记录？', '删除对话', {
    confirmButtonText: '删除',
    cancelButtonText: '取消',
    type: 'warning',
    confirmButtonClass: 'el-button--danger',
  }).then(() => chat.deleteSession(sessionId)).catch(() => {})
}

async function clearCurrentSession() {
  if (!chat.activeSession) return
  const confirmed = await ElMessageBox.confirm('清空后，AI 将忘记本次对话上下文。是否继续？', '清空记忆', {
    confirmButtonText: '清空',
    cancelButtonText: '取消',
    type: 'warning',
  }).then(() => true).catch(() => false)
  if (!confirmed) return

  try {
    await agentApi.clearSession(chat.activeSession.id)
    ElMessage.success('对话记忆已清空')
  } catch {
    ElMessage.error('清空失败')
  }
}
</script>

<style scoped>
.chat-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
  background: #f4f7fb;
}

.sidebar {
  width: 280px;
  min-width: 280px;
  background: #111827;
  color: #e5e7eb;
  display: flex;
  flex-direction: column;
  transition: width 0.2s ease, min-width 0.2s ease;
}

.sidebar.collapsed {
  width: 68px;
  min-width: 68px;
}

.sidebar-brand,
.sidebar-user {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px;
  border-bottom: 1px solid rgba(255,255,255,0.08);
}

.brand-logo,
.header-icon,
.welcome-icon {
  display: grid;
  place-items: center;
  color: #fff;
  background: #0f766e;
}

.brand-logo {
  width: 34px;
  height: 34px;
}

.brand-text {
  flex: 1;
  font-weight: 700;
}

.icon-btn,
.logout-btn,
.del-btn {
  border: 0;
  background: transparent;
  color: inherit;
  cursor: pointer;
}

.sidebar-new {
  padding: 12px;
}

.new-chat-btn,
.quick-item {
  width: 100%;
  border: 1px solid rgba(255,255,255,0.12);
  background: rgba(15, 118, 110, 0.18);
  color: #ccfbf1;
  padding: 9px 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  cursor: pointer;
}

.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 8px;
}

.quick-section {
  padding: 8px;
  border-top: 1px solid rgba(255,255,255,0.08);
}

.quick-item {
  justify-content: flex-start;
  margin-bottom: 6px;
  background: transparent;
  color: rgba(255,255,255,0.68);
}

.quick-item:hover,
.session-item:hover,
.session-item.active {
  background: rgba(255,255,255,0.08);
}

.list-label {
  padding: 10px 6px 6px;
  color: rgba(255,255,255,0.38);
  font-size: 12px;
}

.session-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 8px;
  cursor: pointer;
  color: rgba(255,255,255,0.72);
}

.session-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.empty-sessions {
  color: rgba(255,255,255,0.35);
  font-size: 12px;
  padding: 16px 8px;
}

.sidebar-user {
  border-top: 1px solid rgba(255,255,255,0.08);
  border-bottom: 0;
  margin-top: auto;
}

.sidebar-user.collapsed {
  justify-content: center;
}

.user-avatar {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  background: #0e7490;
  font-weight: 700;
}

.user-meta {
  flex: 1;
  min-width: 0;
}

.user-name,
.user-role {
  margin: 0;
}

.user-name {
  font-weight: 700;
  font-size: 13px;
}

.user-role {
  color: rgba(255,255,255,0.48);
  font-size: 12px;
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.chat-header {
  height: 72px;
  padding: 0 24px;
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-left,
.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-icon {
  width: 40px;
  height: 40px;
}

.chat-header h2,
.chat-header p {
  margin: 0;
}

.chat-header h2 {
  font-size: 16px;
}

.chat-header p {
  color: #64748b;
  font-size: 12px;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.message-list {
  max-width: 920px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.welcome {
  min-height: calc(100vh - 180px);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  text-align: center;
}

.welcome-icon {
  width: 72px;
  height: 72px;
  margin-bottom: 18px;
}

.welcome h3 {
  font-size: 24px;
  margin: 0 0 10px;
}

.welcome p {
  max-width: 560px;
  color: #64748b;
  line-height: 1.7;
  margin: 0 0 26px;
}

.welcome-grid {
  width: min(620px, 100%);
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.welcome-grid button {
  min-height: 64px;
  background: #fff;
  border: 1px solid #e5e7eb;
  color: #334155;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px;
  text-align: left;
  cursor: pointer;
}

.welcome-grid button:hover {
  border-color: #0f766e;
  color: #0f766e;
}

.input-area {
  padding: 16px 24px;
  background: #fff;
  border-top: 1px solid #e5e7eb;
}

.input-row {
  max-width: 920px;
  margin: 0 auto;
  display: flex;
  gap: 10px;
  align-items: flex-end;
}

.send-circle {
  width: 42px;
  height: 42px;
  flex: 0 0 auto;
}

.input-area p {
  max-width: 920px;
  margin: 8px auto 0;
  text-align: center;
  color: #94a3b8;
  font-size: 12px;
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@media (max-width: 760px) {
  .sidebar {
    display: none;
  }

  .chat-header {
    height: auto;
    min-height: 72px;
    padding: 12px 16px;
    align-items: flex-start;
  }

  .header-right {
    display: none;
  }

  .welcome-grid {
    grid-template-columns: 1fr;
  }
}
</style>
