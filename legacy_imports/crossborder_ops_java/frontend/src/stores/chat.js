import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { agentApi } from '@/api'
import { ElMessage } from 'element-plus'
import { parseVisualPayload } from '@/utils/visualPayload.mjs'

const SESSION_KEY = 'crossborder-chat-sessions'

function loadSessions() {
  try {
    return JSON.parse(localStorage.getItem(SESSION_KEY) || '[]')
  } catch {
    return []
  }
}

function saveSessions(sessions) {
  try {
    const toSave = sessions.map(s => ({
      id: s.id,
      title: s.title,
      createdAt: s.createdAt,
      messages: s.messages.map(m => ({
        id: m.id,
        role: m.role,
        content: m.content,
        chartOption: m.chartOption || null,
        status: m.status === 'streaming' ? 'done' : m.status,
      })),
    }))
    localStorage.setItem(SESSION_KEY, JSON.stringify(toSave))
  } catch {
    // Ignore localStorage quota errors in demo mode.
  }
}

export const useChatStore = defineStore('chat', () => {
  const sessions = ref(loadSessions())
  const activeSessionId = ref(sessions.value[0]?.id || null)
  const isStreaming = ref(false)
  let abortController = null

  const activeSession = computed(() =>
    sessions.value.find(s => s.id === activeSessionId.value) || null
  )

  function createSession() {
    const id = `session-${Date.now()}`
    const session = {
      id,
      title: '新会话',
      createdAt: new Date().toISOString(),
      messages: [],
    }
    sessions.value.unshift(session)
    activeSessionId.value = id
    saveSessions(sessions.value)
    return session
  }

  function deleteSession(sessionId) {
    agentApi.clearSession(sessionId).catch(() => {})
    const idx = sessions.value.findIndex(s => s.id === sessionId)
    if (idx !== -1) sessions.value.splice(idx, 1)
    if (activeSessionId.value === sessionId) {
      activeSessionId.value = sessions.value[0]?.id || null
    }
    saveSessions(sessions.value)
  }

  function switchSession(sessionId) {
    activeSessionId.value = sessionId
  }

  function patchLastAssistant(sessionId, patch) {
    const session = sessions.value.find(s => s.id === sessionId)
    if (!session) return
    const msgs = session.messages
    for (let i = msgs.length - 1; i >= 0; i--) {
      if (msgs[i].role === 'assistant') {
        Object.assign(msgs[i], patch)
        break
      }
    }
  }

  async function sendMessage(text) {
    if (!text.trim() || isStreaming.value) return

    let session = activeSession.value
    if (!session) session = createSession()

    const sessionId = session.id
    const isFirstMsg = session.messages.length === 0

    session.messages.push({ id: Date.now(), role: 'user', content: text, status: 'done' })
    if (isFirstMsg) session.title = text.slice(0, 24)
    session.messages.push({
      id: Date.now() + 1,
      role: 'assistant',
      content: '',
      chartOption: null,
      status: 'streaming',
    })

    isStreaming.value = true
    abortController = new AbortController()

    let fullContent = ''
    let buffer = ''
    let visualResolved = false

    try {
      const response = await fetch('/agent/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'sa-token': localStorage.getItem('sa-token') || '',
        },
        body: JSON.stringify({ sessionId, message: text }),
        signal: abortController.signal,
      })

      if (response.status === 401) {
        const { useAuthStore } = await import('@/stores/auth')
        useAuthStore().clearAuth()
        const { default: router } = await import('@/router')
        router.push('/login')
        ElMessage.error('登录已过期，请重新登录')
        return
      }
      if (!response.ok) throw new Error(`HTTP ${response.status}`)

      const reader = response.body.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''

        for (const line of lines) {
          if (!line.startsWith('data:')) continue
          const token = line.slice(5)
          if (token.trimEnd() === '[DONE]') continue

          fullContent += token
          if (visualResolved) continue

          const payload = tryParseVisualPayload(fullContent)
          if (!payload) {
            patchLastAssistant(sessionId, { content: fullContent })
            continue
          }

          try {
            visualResolved = true
            patchLastAssistant(sessionId, { content: payload.text, chartOption: payload.chartOption })
          } catch {
            patchLastAssistant(sessionId, { content: '正在生成图表数据...' })
          }
        }
      }

      if (!visualResolved) {
        const payload = tryParseVisualPayload(fullContent)
        if (payload) {
          patchLastAssistant(sessionId, { content: payload.text, chartOption: payload.chartOption })
        }
      }

      patchLastAssistant(sessionId, { status: 'done' })
    } catch (err) {
      if (err.name === 'AbortError') {
        patchLastAssistant(sessionId, { status: 'done' })
      } else {
        ElMessage.error('请求失败，请检查后端服务是否正常运行')
        patchLastAssistant(sessionId, {
          content: '请求失败，请检查后端服务是否正常运行。',
          status: 'error',
        })
      }
    } finally {
      isStreaming.value = false
      abortController = null
      saveSessions(sessions.value)
    }
  }

  function stopStreaming() {
    abortController?.abort()
  }

  return {
    sessions,
    activeSessionId,
    activeSession,
    isStreaming,
    createSession,
    deleteSession,
    switchSession,
    sendMessage,
    stopStreaming,
  }
})

function tryParseVisualPayload(content) {
  try {
    return parseVisualPayload(content)
  } catch {
    return null
  }
}
