<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'

const senderId = ref('u1001')
const draftMessage = ref('')
const isSending = ref(false)
const errorMessage = ref('')
const messages = ref([])
const messagesContainer = ref(null)
const loadedHistoryCount = ref(0)
const currentPageDividerInserted = ref(false)

const orders = ref([])
const books = ref([])
const isLoadingSidebar = ref(false)
const sidebarError = ref('')
const activeTab = ref('orders')

// Copy state
const copyState = ref({})

// ── Canvas 粒子背景系统 ──────────────────────────────────────────────
const bgCanvas = ref(null)
let animFrameId = null
let bgParticles = []
const BG_PARTICLE_COUNT = 80
const BG_CONNECT_DIST = 150
const BG_MOUSE_RADIUS = 180
const bgMouse = { x: null, y: null }

function createBgParticles(w, h) {
  const palette = [
    [231, 176, 94], [201, 145, 60], [224, 138, 85],
    [243, 213, 163], [116, 211, 168], [230, 190, 120],
  ]
  bgParticles = Array.from({ length: BG_PARTICLE_COUNT }, () => {
    const color = palette[Math.floor(Math.random() * palette.length)]
    return {
      x: Math.random() * w, y: Math.random() * h,
      size: Math.random() * 2.5 + 1,
      vx: (Math.random() - 0.5) * 0.35,
      vy: (Math.random() - 0.5) * 0.35,
      color, opacity: Math.random() * 0.45 + 0.12,
      phase: Math.random() * Math.PI * 2,
      pulse: Math.random() * 0.015 + 0.005,
    }
  })
}

function animateBg(ctx, w, h, time) {
  ctx.clearRect(0, 0, w, h)

  for (const p of bgParticles) {
    p.x += p.vx + Math.sin(time * 0.001 + p.phase) * 0.25
    p.y += p.vy + Math.cos(time * 0.001 + p.phase + 1) * 0.25

    if (bgMouse.x !== null) {
      const dx = p.x - bgMouse.x, dy = p.y - bgMouse.y
      const dist = Math.hypot(dx, dy)
      if (dist < BG_MOUSE_RADIUS) {
        const force = (BG_MOUSE_RADIUS - dist) / BG_MOUSE_RADIUS
        p.x += (dx / dist) * force * 0.7
        p.y += (dy / dist) * force * 0.7
      }
    }

    if (p.x < -20) p.x = w + 20; if (p.x > w + 20) p.x = -20
    if (p.y < -20) p.y = h + 20; if (p.y > h + 20) p.y = -20
  }

  // 连线
  ctx.lineWidth = 0.5
  for (let i = 0; i < bgParticles.length; i++) {
    for (let j = i + 1; j < bgParticles.length; j++) {
      const dx = bgParticles[i].x - bgParticles[j].x
      const dy = bgParticles[i].y - bgParticles[j].y
      const dist = Math.hypot(dx, dy)
      if (dist < BG_CONNECT_DIST) {
        const alpha = (1 - dist / BG_CONNECT_DIST) * 0.1
        ctx.strokeStyle = `rgba(231,176,94,${alpha})`
        ctx.beginPath()
        ctx.moveTo(bgParticles[i].x, bgParticles[i].y)
        ctx.lineTo(bgParticles[j].x, bgParticles[j].y)
        ctx.stroke()
      }
    }
  }

  // 粒子光晕
  for (const p of bgParticles) {
    const pulse = 1 + Math.sin(time * p.pulse + p.phase) * 0.25
    const r = p.size * pulse
    const [cr, cg, cb] = p.color

    ctx.beginPath()
    ctx.arc(p.x, p.y, r * 2.5, 0, Math.PI * 2)
    ctx.fillStyle = `rgba(${cr},${cg},${cb},${p.opacity * 0.08})`
    ctx.fill()

    ctx.beginPath()
    ctx.arc(p.x, p.y, r, 0, Math.PI * 2)
    ctx.fillStyle = `rgba(${cr},${cg},${cb},${p.opacity * 0.7})`
    ctx.fill()
  }
}

function initBg() {
  const canvas = bgCanvas.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')

  const resize = () => {
    canvas.width = window.innerWidth
    canvas.height = window.innerHeight
    createBgParticles(canvas.width, canvas.height)
  }
  resize()
  window.addEventListener('resize', resize)

  const onMouseMove = (e) => { bgMouse.x = e.clientX; bgMouse.y = e.clientY }
  const onMouseLeave = () => { bgMouse.x = null; bgMouse.y = null }
  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseleave', onMouseLeave)

  const loop = (time) => {
    animateBg(ctx, canvas.width, canvas.height, time)
    animFrameId = requestAnimationFrame(loop)
  }
  animFrameId = requestAnimationFrame(loop)

  canvas._cleanup = () => {
    cancelAnimationFrame(animFrameId)
    window.removeEventListener('resize', resize)
    document.removeEventListener('mousemove', onMouseMove)
    document.removeEventListener('mouseleave', onMouseLeave)
  }
}
// ── 粒子背景系统结束 ──────────────────────────────────────────────────

// 客服配置
const customerService = {
  name: '小听',
  title: '听书顾问',
  avatar: '/avatar-xiaoting.png',
  fallbackAvatar: 'https://1234study.oss-cn-shenzhen.aliyuncs.com/%E5%AE%A2%E6%9C%8D.png',
  status: '在线'
}

// 用户配置
const userProfile = {
  name: '书友',
  avatar: '/avatar-reader.svg'
}

// 把网络层/解析层的原始报错换成可读提示，业务侧文案原样保留
function toFriendlyError(error, fallback) {
  const message = error instanceof Error ? error.message : ''
  if (!message) {
    return fallback
  }
  if (/Failed to (execute|fetch)|NetworkError|Load failed|Unexpected end of JSON|fetch failed/i.test(message)) {
    return '客服服务暂时没有响应，请确认后端服务已启动后重试。'
  }
  return message
}

// 欢迎语快捷入口
const welcomeChips = [
  '推荐一本适合睡前听的书',
  '查一下我的听书订单',
  '会员畅听权益怎么算',
  '我想申请退款',
]

// 本地头像资源缺失时回退到远端客服形象
function useFallbackAvatar(event) {
  const element = event?.target
  if (!element || element.dataset.fallbackApplied) {
    return
  }
  element.dataset.fallbackApplied = 'true'
  element.src = customerService.fallbackAvatar
}

// 将消息分组为 Turn 结构
const turns = computed(() => {
  const result = []
  let currentTurn = null
  let turnIndex = 0

  for (const message of messages.value) {
    if (message.type === 'divider') {
      if (currentTurn) {
        result.push(currentTurn)
        currentTurn = null
      }
      result.push({
        type: 'divider',
        text: message.text
      })
      continue
    }

    if (message.role === 'user') {
      // 如果有待处理的当前 turn，先保存
      if (currentTurn) {
        result.push(currentTurn)
      }
      // 创建新的 turn
      turnIndex++
      currentTurn = {
        type: 'turn',
        id: `turn-${turnIndex}`,
        index: turnIndex,
        userMessage: message,
        botMessages: []
      }
    } else if (message.role === 'bot') {
      if (!currentTurn) {
        // 如果没有当前 turn，创建一个（可能是因为历史消息）
        turnIndex++
        currentTurn = {
          type: 'turn',
          id: `turn-${turnIndex}`,
          index: turnIndex,
          userMessage: null,
          botMessages: []
        }
      }
      currentTurn.botMessages.push(message)
    }
  }

  if (currentTurn) {
    result.push(currentTurn)
  }

  return result
})

const chatEndpoint = computed(() => '/api/chat')
const chatHistoryEndpoint = computed(
  () => `/api/chat/history?sender_id=${encodeURIComponent(senderId.value.trim())}`
)
const commerceOrdersEndpoint = computed(
  () => `/commerce/users/${encodeURIComponent(senderId.value.trim())}/orders`
)
const commerceBooksEndpoint = computed(
  () => `/commerce/users/${encodeURIComponent(senderId.value.trim())}/books`
)

function createBaseMessage(role) {
  return {
    id: crypto.randomUUID(),
    role,
    buttons: [],
  }
}

function insertCurrentPageDividerIfNeeded() {
  if (currentPageDividerInserted.value || loadedHistoryCount.value === 0) {
    return
  }

  appendMessage('divider', { text: '以上为历史消息' })
  currentPageDividerInserted.value = true
}

function appendUserText(text) {
  insertCurrentPageDividerIfNeeded()
  messages.value.push({
    ...createBaseMessage('user'),
    type: 'text',
    text,
  })
}

function appendUserObject(objectType, payload) {
  insertCurrentPageDividerIfNeeded()
  messages.value.push({
    ...createBaseMessage('user'),
    type: 'object',
    objectType,
    payload,
  })
}

function appendBotMessages(botMessages) {
  for (const message of botMessages) {
    appendMessage('bot', message)
  }
}

function appendMessage(role, message) {
  if (role === 'divider') {
    messages.value.push({
      ...createBaseMessage('divider'),
      type: 'divider',
      text: message.text ?? '以上为历史消息',
    })
    return
  }

  if (message.object) {
    messages.value.push({
      ...createBaseMessage(role),
      type: 'object',
      objectType: message.object.type,
      payload: message.object,
    })
  } else {
    messages.value.push({
      ...createBaseMessage(role),
      type: 'text',
      text: message.text ?? '',
      suggestions: message.suggestions ?? null,
    })
  }
}

function setHistoryMessages(historyMessages) {
  messages.value = []
  currentPageDividerInserted.value = false
  for (const message of historyMessages) {
    if (message.role === 'divider') {
      continue
    }
    const role = ['user', 'bot'].includes(message.role) ? message.role : 'bot'
    appendMessage(role, message)
  }
  loadedHistoryCount.value = messages.value.length
}

async function scrollToBottom() {
  await nextTick()
  const container = messagesContainer.value
  if (!container) {
    return
  }
  container.scrollTop = container.scrollHeight
}

watch(
  () => messages.value.length,
  async () => {
    await scrollToBottom()
  }
)

function resetConversation() {
  messages.value = []
  loadedHistoryCount.value = 0
  currentPageDividerInserted.value = false
  errorMessage.value = ''
}

function formatAmount(amount) {
  const numericAmount = Number(amount)
  if (Number.isNaN(numericAmount)) {
    return '￥0.00'
  }
  return `￥${numericAmount.toFixed(2)}`
}

const ORDER_STATUS_CLASS = {
  '待支付': 'status-warning',
  '已完成': 'status-success',
  '已取消': 'status-muted',
  '退款中': 'status-danger',
  '已退款': 'status-muted',
}

function statusText(status) {
  if (!status) {
    return '状态未知'
  }
  return status
}

function getStatusClass(status) {
  return ORDER_STATUS_CLASS[status] || 'status-muted'
}

function getObjectTypeLabel(message) {
  return message?.objectType === 'order' ? '听书订单' : '有声书'
}

function formatBookSummary(book) {
  const parts = []
  if (book.author) {
    parts.push(`作者：${book.author}`)
  }
  if (book.narrator) {
    parts.push(`主播：${book.narrator}`)
  }
  if (book.category) {
    parts.push(`分类：${book.category}`)
  }
  if (parts.length > 0) {
    return parts.join(' · ')
  }
  if (book.price != null) {
    return `定价：${formatAmount(book.price)}`
  }
  return '有声书资料'
}

function getObjectTitle(message) {
  const payload = message.payload ?? {}
  if (payload.title) {
    return payload.title
  }
  return message.objectType === 'order' ? '听书订单' : '有声书'
}

function getObjectIdentifier(message) {
  const payload = message.payload ?? {}
  const id = payload.order_id ?? payload.book_id ?? payload.id
  const label = message.objectType === 'order' ? '订单编号' : '有声书编号'
  return id ? `${label}：${id}` : label
}

function getObjectSummary(message) {
  const payload = message.payload ?? {}
  if (message.objectType === 'order') {
    const status = payload.status ?? payload.attributes?.status
    return status ? `订单状态：${statusText(status)}` : '听书订单'
  }
  return formatBookSummary(payload)
}

function getObjectAmount(message) {
  const payload = message.payload ?? {}
  const amount = message.objectType === 'order'
    ? payload.amount ?? payload.attributes?.amount
    : payload.price ?? payload.attributes?.price
  return formatAmount(amount)
}

async function fetchSidebarData() {
  const currentSenderId = senderId.value.trim()
  orders.value = []
  books.value = []
  sidebarError.value = ''

  if (!currentSenderId) {
    return
  }

  isLoadingSidebar.value = true
  try {
    const [ordersResponse, booksResponse] = await Promise.all([
      fetch(commerceOrdersEndpoint.value),
      fetch(commerceBooksEndpoint.value),
    ])

    const [ordersPayload, booksPayload] = await Promise.all([
      ordersResponse.json(),
      booksResponse.json(),
    ])

    if (!ordersResponse.ok) {
      throw new Error(ordersPayload.detail || '加载听书订单失败。')
    }
    if (!booksResponse.ok) {
      throw new Error(booksPayload.detail || '加载有声书库失败。')
    }

    orders.value = Array.isArray(ordersPayload?.data?.orders) ? ordersPayload.data.orders : []
    books.value = Array.isArray(booksPayload?.data?.books) ? booksPayload.data.books : []
  } catch (error) {
    sidebarError.value = toFriendlyError(error, '加载听书业务台失败。')
  } finally {
    isLoadingSidebar.value = false
  }
}

async function fetchChatHistory() {
  const currentSenderId = senderId.value.trim()
  if (!currentSenderId) {
    messages.value = []
    return
  }

  try {
    const response = await fetch(chatHistoryEndpoint.value)
    const data = await response.json()
    if (!response.ok) {
      throw new Error(data.detail || '加载历史消息失败。')
    }
    if (currentSenderId === senderId.value.trim()) {
      setHistoryMessages(Array.isArray(data?.messages) ? data.messages : [])
    }
  } catch (error) {
    errorMessage.value = toFriendlyError(error, '加载历史对话失败。')
  }
}

async function sendPayload(payload) {
  if (isSending.value) {
    return
  }

  errorMessage.value = ''
  isSending.value = true

  try {
    await sendPayloadHttp(payload)
  } catch (error) {
    errorMessage.value = toFriendlyError(error, '消息没有送达，请稍后再试。')
  } finally {
    isSending.value = false
  }
}

async function sendPayloadHttp(payload) {
  const response = await fetch(chatEndpoint.value, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      sender_id: senderId.value.trim(),
      ...payload,
    }),
  })

  const data = await response.json()
  if (!response.ok) {
    throw new Error(data.detail || '请求失败。')
  }

  appendBotMessages(data.messages ?? [])
}

async function sendSuggestion(text) {
  appendUserText(text)
  await sendPayload({ text })
}

async function sendQuickText(text) {
  draftMessage.value = text
  await sendTextMessage()
}
async function sendTextMessage() {
  const text = draftMessage.value.trim()
  const currentSenderId = senderId.value.trim()

  if (!currentSenderId) {
    errorMessage.value = '请先填写书友账号。'
    return
  }
  if (!text) {
    return
  }

  draftMessage.value = ''
  appendUserText(text)
  await sendPayload({ text })
}

async function sendOrder(order) {
  const currentSenderId = senderId.value.trim()
  if (!currentSenderId) {
    errorMessage.value = '请先填写书友账号。'
    return
  }

  appendUserObject('order', { ...order })
  await sendPayload({
    object: {
      type: 'order',
      id: order.order_id,
      title: order.title,
      attributes: {
        status: order.status,
        amount: order.amount,
        created_at: order.created_at,
        cover_url: order.cover_url,
      },
    },
  })
}

async function sendBook(book) {
  const currentSenderId = senderId.value.trim()
  if (!currentSenderId) {
    errorMessage.value = '请先填写书友账号。'
    return
  }

  appendUserObject('book', { ...book })
  await sendPayload({
    object: {
      type: 'book',
      id: book.book_id,
      title: book.title,
      attributes: {
        author: book.author,
        narrator: book.narrator,
        category: book.category,
        price: book.price,
        cover_url: book.cover_url,
      },
    },
  })
}

watch(
  () => senderId.value.trim(),
  async (value, previousValue) => {
    if (value === previousValue) {
      return
    }

    // 切换 sender_id 时刷新会话历史与侧边栏
    resetConversation()
    if (!value) {
      orders.value = []
      books.value = []
      return
    }
    await Promise.all([fetchSidebarData(), fetchChatHistory()])
  }
)

onMounted(async () => {
  initBg()
  await Promise.all([fetchSidebarData(), fetchChatHistory()])
})

onUnmounted(() => {
  if (bgCanvas.value?._cleanup) bgCanvas.value._cleanup()
})

async function copyText(text, key) {
  if (!text || !key) return
  try {
    await navigator.clipboard.writeText(text)
    copyState.value[key] = true
    setTimeout(() => { copyState.value[key] = false }, 1800)
  } catch (error) {
    console.error('Copy failed:', error)
  }
}
</script>

<template>
  <div class="app-shell">
    <div class="bg-theme" aria-hidden="true"></div>
    <canvas ref="bgCanvas" class="bg-canvas"></canvas>
    <div class="workspace">
      <div class="chat-card">
        <header class="chat-header">
          <div class="header-content">
            <div class="brand">
              <div class="brand-mark">
                <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path d="M3.6 15.2v-2.4a8.4 8.4 0 0 1 16.8 0v2.4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
                  <rect x="1.8" y="13.6" width="4.4" height="7.6" rx="2.2" stroke="currentColor" stroke-width="1.6" />
                  <rect x="17.8" y="13.6" width="4.4" height="7.6" rx="2.2" stroke="currentColor" stroke-width="1.6" />
                </svg>
              </div>
              <div class="brand-text">
                <h1 class="brand-name">听书商城<span class="brand-divider">·</span><span class="brand-name-sub">智能客服</span></h1>
                <p class="brand-slogan">AUDIOBOOK STORE　用声音陪你读完每一页</p>
              </div>
              <div class="brand-wave" aria-hidden="true">
                <span v-for="n in 6" :key="n"></span>
              </div>
            </div>
            <div class="header-actions">
              <div class="service-info">
                <div class="service-avatar-wrapper">
                  <img :src="customerService.avatar" class="service-avatar" alt="小听" @error="useFallbackAvatar" />
                  <span class="status-indicator"></span>
                </div>
                <div class="service-details">
                  <span class="service-name">{{ customerService.name }}</span>
                  <span class="service-status">{{ customerService.status }} · {{ customerService.title }}</span>
                </div>
              </div>
              <button type="button" class="clear-button" title="清空对话" @click="resetConversation">
                <span class="clear-icon">✦</span>
                <span>新对话</span>
              </button>
            </div>
          </div>
        </header>

        <div class="chat-body">
          <main class="chat-main">
        <section ref="messagesContainer" class="messages">
          <div v-if="turns.length === 0" class="welcome">
            <div class="welcome-card">
              <div class="welcome-glow"></div>
              <div class="welcome-tag">听书商城 · 客服中心</div>
              <div class="welcome-avatar-wrapper">
                <img :src="customerService.avatar" class="welcome-avatar" alt="小听" @error="useFallbackAvatar" />
                <span class="welcome-status-pulse"></span>
              </div>
              <h2 class="welcome-greeting">夜色正好，想听点什么？</h2>
              <p class="welcome-subtitle">我是小听，你的专属听书顾问 —— 选书、找书、会员权益和售后，都可以交给我。</p>
              <div class="welcome-chips">
                <button
                  v-for="chip in welcomeChips"
                  :key="chip"
                  type="button"
                  class="welcome-chip"
                  :disabled="isSending"
                  @click="sendQuickText(chip)"
                >{{ chip }}</button>
              </div>
              <p class="welcome-features">
                <span>🎧 有声书推荐</span>
                <span>📚 专辑与主播</span>
                <span>🧾 订单与退款</span>
              </p>
            </div>
          </div>

          <!-- Turn 结构展示 -->
          <template v-for="(item, index) in turns" :key="item.id || index">
            <!-- 分隔线 -->
            <div v-if="item.type === 'divider'" class="history-divider">
              <span>{{ item.text }}</span>
            </div>

            <!-- Turn 卡片 -->
            <div v-else class="turn-card" :class="{ 'has-user-message': item.userMessage }">
              <!-- Turn 标识 -->
              <div class="turn-header">
                <span class="turn-badge">Turn {{ item.index }}</span>
                <span class="turn-label">本轮对话</span>
              </div>

              <!-- 用户消息区域 -->
              <div v-if="item.userMessage" class="turn-section user-section">
                <div class="section-header">
                  <div class="avatar-wrapper user-avatar">
                    <img :src="userProfile.avatar" class="avatar" />
                  </div>
                  <div class="agent-info">
                    <span class="agent-name">{{ userProfile.name }}</span>
                    <span class="agent-label">用户</span>
                  </div>
                </div>
                <div class="turn-bubble user-bubble">
                  <template v-if="item.userMessage.type === 'object'">
                    <div class="object-card" :class="`object-card-${item.userMessage.objectType}`">
                      <div class="object-card-badge">
                        {{ getObjectTypeLabel(item.userMessage) }}
                      </div>
                      <img
                        v-if="item.userMessage.type === 'object' && item.userMessage.payload.cover_url"
                        :src="item.userMessage.payload.cover_url"
                        :alt="getObjectTitle(item.userMessage)"
                        class="object-card-image"
                        @error="$event.target.style.display='none'"
                      />
                      <div class="object-card-title">{{ getObjectTitle(item.userMessage) }}</div>
                      <div class="object-card-meta">{{ getObjectIdentifier(item.userMessage) }}</div>
                      <div class="object-card-meta">
                        <span v-if="item.userMessage.objectType === 'order' && item.userMessage.payload.status" class="status-badge" :class="getStatusClass(item.userMessage.payload.status)">{{ statusText(item.userMessage.payload.status) }}</span>
                        <span v-else>{{ getObjectSummary(item.userMessage) }}</span>
                      </div>
                      <div class="object-card-price">{{ getObjectAmount(item.userMessage) }}</div>
                    </div>
                  </template>
                  <template v-else>
                    <div class="user-text-row">
                      <p>{{ item.userMessage.text }}</p>
                      <div class="user-actions">
                        <button type="button" class="copy-button copy-button-on-accent"
                          :class="{ 'copy-done': copyState[`${item.id}-user`] }"
                          :title="copyState[`${item.id}-user`] ? '已复制' : '复制文字'"
                          @click.stop="copyText(item.userMessage.text, `${item.id}-user`)">
                          <span v-if="copyState[`${item.id}-user`]">✓</span>
                          <span v-else>📋</span>
                        </button>
                      </div>
                    </div>
                  </template>
                </div>
              </div>

              <!-- 客服回复区域 -->
              <div v-if="item.botMessages.length > 0" class="turn-section bot-section">
                <div class="section-header">
                  <div class="avatar-wrapper service-avatar">
                    <img :src="customerService.avatar" class="avatar" />
                    <span class="status-dot"></span>
                  </div>
                  <div class="agent-info">
                    <span class="agent-name">{{ customerService.name }}</span>
                    <span class="agent-label">{{ customerService.title }}</span>
                  </div>
                </div>
                <div class="bot-messages">
                  <div
                    v-for="(botMsg, msgIndex) in item.botMessages"
                    :key="msgIndex"
                    class="turn-bubble bot-bubble"
                  >
                    <template v-if="botMsg.type === 'object'">
                      <div class="object-card" :class="`object-card-${botMsg.objectType}`">
                        <div class="object-card-badge">
                          {{ getObjectTypeLabel(botMsg) }}
                        </div>
                        <img
                          v-if="botMsg.type === 'object' && botMsg.payload.cover_url"
                          :src="botMsg.payload.cover_url"
                          :alt="getObjectTitle(botMsg)"
                          class="object-card-image"
                          @error="$event.target.style.display='none'"
                        />
                        <div class="object-card-title">{{ getObjectTitle(botMsg) }}</div>
                        <div class="object-card-meta">{{ getObjectIdentifier(botMsg) }}</div>
                        <div class="object-card-meta">
                          <span v-if="botMsg.objectType === 'order' && botMsg.payload.status" class="status-badge" :class="getStatusClass(botMsg.payload.status)">{{ statusText(botMsg.payload.status) }}</span>
                          <span v-else>{{ getObjectSummary(botMsg) }}</span>
                        </div>
                        <div class="object-card-price">{{ getObjectAmount(botMsg) }}</div>
                      </div>
                    </template>
                    <template v-else>
                      <div class="bot-text-row">
                        <p>{{ botMsg.text }}</p>
                      </div>
                    </template>
                    <div v-if="botMsg.suggestions && botMsg.suggestions.length > 0" class="suggestion-chips">
                      <button
                        v-for="sug in botMsg.suggestions"
                        :key="sug"
                        type="button"
                        class="suggestion-chip"
                        :disabled="isSending"
                        @click.stop="sendSuggestion(sug)"
                      >{{ sug }}</button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </template>
        </section>

        <div v-if="isSending" class="typing-indicator">
          <div class="typing-avatar">
            <img :src="customerService.avatar" class="avatar-small" alt="小听" @error="useFallbackAvatar" />
          </div>
          <div class="typing-bubble">
            <span class="typing-dots">
              <span></span><span></span><span></span>
            </span>
            <span class="typing-label">小听正在翻书，马上回答你…</span>
          </div>
        </div>

        <p v-if="errorMessage" class="error-message">
          {{ errorMessage }}
        </p>

        <form class="composer" @submit.prevent="sendTextMessage">
          <div class="composer-field">
            <span class="composer-hint" aria-hidden="true">🎧</span>
            <input
              v-model="draftMessage"
              type="text"
              placeholder="说说你想听哪本书，或直接发一本有声书给我…"
              :disabled="isSending"
            />
          </div>
          <button type="submit" :disabled="isSending || !draftMessage.trim()">
            {{ isSending ? '发送中…' : '发送' }}
          </button>
        </form>
          </main>
        </div>
      </div>

      <aside class="sidebar">
        <div class="sidebar-header">
          <div class="sidebar-heading">
            <h2>听书业务台</h2>
            <span class="sidebar-chip">BOOK DESK</span>
          </div>
          <p>把订单或有声书放进对话，小听接着为你服务。</p>
        </div>

        <div class="sidebar-user">
          <label class="sidebar-user-field">
            <span>账号</span>
            <input v-model="senderId" type="text" placeholder="u1001" />
          </label>
          <button
            type="button"
            class="secondary-button"
            title="刷新听书业务台"
            :disabled="isLoadingSidebar"
            @click="fetchSidebarData"
          >
            {{ isLoadingSidebar ? '加载中…' : '刷新' }}
          </button>
        </div>

        <div class="tabs">
          <button
            type="button"
            class="tab-button"
            :class="{ active: activeTab === 'orders' }"
            @click="activeTab = 'orders'"
          >
            听书订单
          </button>
          <button
            type="button"
            class="tab-button"
            :class="{ active: activeTab === 'books' }"
            @click="activeTab = 'books'"
          >
            有声书库
          </button>
        </div>

        <p v-if="sidebarError" class="sidebar-error">{{ sidebarError }}</p>

        <div v-if="activeTab === 'orders'" class="sidebar-list">
          <div v-if="!orders.length && !isLoadingSidebar" class="sidebar-empty">
            <span class="sidebar-empty-icon">🧾</span>
            <span>还没有听书订单，先去书城挑一本喜欢的书吧。</span>
          </div>

          <article v-for="order in orders" :key="order.order_id" class="sidebar-card">
            <div class="card-image-wrapper">
              <img
                v-if="order.cover_url"
                :src="order.cover_url"
                :alt="order.title"
                class="card-image"
                @error="$event.target.style.display='none'"
              />
              <div v-else class="card-image-placeholder">🎧</div>
              <span class="card-type-chip">听书订单</span>
            </div>
            <div class="card-top">
              <div class="card-title">{{ order.title }}</div>
              <div class="card-amount">{{ formatAmount(order.amount) }}</div>
            </div>
            <div class="card-meta">订单编号：{{ order.order_id }}</div>
            <div class="card-meta">
              <span class="status-badge" :class="getStatusClass(order.status)">{{ statusText(order.status) }}</span>
            </div>
            <button
              type="button"
              class="secondary-button full-width"
              :disabled="isSending"
              @click="sendOrder(order)"
            >
              发送此订单
            </button>
          </article>
        </div>

        <div v-else class="sidebar-list">
          <div v-if="!books.length && !isLoadingSidebar" class="sidebar-empty">
            <span class="sidebar-empty-icon">📚</span>
            <span>书架里还没有有声书，先去听一本试试。</span>
          </div>

          <article v-for="book in books" :key="book.book_id" class="sidebar-card">
            <div class="card-image-wrapper">
              <img
                v-if="book.cover_url"
                :src="book.cover_url"
                :alt="book.title"
                class="card-image"
                @error="$event.target.style.display='none'"
              />
              <div v-else class="card-image-placeholder">📚</div>
              <span class="card-type-chip">有声书</span>
            </div>
            <div class="card-top">
              <div class="card-title">{{ book.title }}</div>
              <div class="card-amount">{{ formatAmount(book.price) }}</div>
            </div>
            <div class="card-meta">有声书编号：{{ book.book_id }}</div>
            <div class="card-meta">作者：{{ book.author }} · 主播：{{ book.narrator }}</div>
            <div class="card-meta">分类：{{ book.category }}</div>
            <button
              type="button"
              class="secondary-button full-width"
              :disabled="isSending"
              @click="sendBook(book)"
            >
              发送这本书
            </button>
          </article>
        </div>
      </aside>
    </div>
  </div>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@500;600;700&family=Outfit:wght@300..700&display=swap');

:global(*) {
  box-sizing: border-box;
}

:global(:root) {
  /* ── 夜色书房底色 ── */
  --color-bg-deep: #0a0705;
  --color-bg-mid: #120d09;
  --color-bg-surface: #191108;

  /* 暖调玻璃面板 */
  --color-surface: rgba(24, 18, 13, 0.78);
  --color-surface-hover: rgba(33, 25, 18, 0.86);
  --color-surface-dim: rgba(16, 12, 8, 0.62);
  --color-surface-raised: rgba(32, 24, 17, 0.70);
  --color-surface-field: rgba(13, 10, 7, 0.62);

  /* 暖灯文字 */
  --color-text-primary: #f3eadb;
  --color-text-secondary: #b7a992;
  --color-text-muted: #8a7c68;
  --color-text-inverse: #1a130d;

  /* 主色：暖金（书灯） */
  --color-accent: #e7b05e;
  --color-accent-strong: #c98a3c;
  --color-accent-soft: rgba(231, 176, 94, 0.10);
  --color-accent-glow: rgba(231, 176, 94, 0.20);
  --color-accent-soft-bg: rgba(231, 176, 94, 0.06);
  --color-gold-line: rgba(231, 176, 94, 0.22);

  /* 辅助色：陶土橘 */
  --color-warm: #e08a55;
  --color-warm-strong: #c96f3d;
  --color-warm-soft: rgba(224, 138, 85, 0.10);
  --color-warm-glow: rgba(224, 138, 85, 0.18);
  --color-warm-soft-bg: rgba(224, 138, 85, 0.05);

  /* 语义色 */
  --color-success: #74d3a8;
  --color-success-soft: rgba(116, 211, 168, 0.12);
  --color-info: #7fbcd8;
  --color-info-soft: rgba(127, 188, 216, 0.10);
  --color-danger: #ef8080;
  --color-danger-soft: rgba(239, 128, 128, 0.10);

  /* 边框 */
  --color-border: rgba(243, 234, 219, 0.08);
  --color-border-light: rgba(243, 234, 219, 0.05);
  --color-border-strong: rgba(243, 234, 219, 0.14);

  /* ── 圆角 ── */
  --radius-sm: 10px;
  --radius-md: 16px;
  --radius-lg: 24px;
  --radius-xl: 28px;
  --radius-full: 9999px;

  /* ── 阴影 ── */
  --shadow-xs: 0 1px 3px rgba(0, 0, 0, 0.20);
  --shadow-sm: 0 4px 14px rgba(0, 0, 0, 0.24);
  --shadow-md: 0 8px 32px rgba(0, 0, 0, 0.30);
  --shadow-lg: 0 20px 56px rgba(0, 0, 0, 0.38);
  --shadow-glow-gold: 0 0 60px rgba(231, 176, 94, 0.10), 0 0 130px rgba(231, 176, 94, 0.04);
  --shadow-glow-copper: 0 0 50px rgba(201, 111, 61, 0.08), 0 0 100px rgba(201, 111, 61, 0.03);
  --shadow-inner-glow: inset 0 1px 0 rgba(255, 255, 255, 0.04);

  /* ── 动效 ── */
  --ease-out-expo: cubic-bezier(0.16, 1, 0.3, 1);
  --ease-out-back: cubic-bezier(0.34, 1.56, 0.64, 1);
  --ease-in-out: cubic-bezier(0.65, 0, 0.35, 1);
  --duration-fast: 150ms;
  --duration-base: 250ms;
  --duration-slow: 400ms;

  --font-serif: "Noto Serif SC", "Songti SC", "STSong", serif;
}

:global(body) {
  margin: 0;
  font-family: "Outfit", "PingFang SC", "Microsoft YaHei", sans-serif;
  background: var(--color-bg-deep);
  color: var(--color-text-primary);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

:global(button),
:global(input) {
  font: inherit;
}

:global(#app) {
  min-height: 100vh;
}

.app-shell {
  min-height: 100vh;
  padding: 24px;
  position: relative;
  overflow: hidden;
  background:
    radial-gradient(1200px 640px at 8% -8%, rgba(231, 176, 94, 0.12) 0%, transparent 62%),
    radial-gradient(900px 520px at 102% 108%, rgba(201, 111, 61, 0.10) 0%, transparent 64%),
    linear-gradient(162deg, #090604 0%, #130d08 26%, #0b0806 52%, #140e09 76%, #0a0705 100%);
  background-size: 100% 100%, 100% 100%, 300% 300%;
  animation: bgShift 28s ease-in-out infinite;
}

/* 细颗粒质感 */
.app-shell::before {
  content: "";
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  opacity: 0.03;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
}

.bg-theme {
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background-image: url('/bg-audiobook.svg');
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  opacity: 0.55;
}

.bg-canvas {
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
}

/* 暖灯大光斑 —— 左上 */
.app-shell::after {
  content: "";
  position: absolute;
  width: 820px;
  height: 820px;
  border-radius: 50%;
  pointer-events: none;
  z-index: 0;
  top: -340px;
  left: -300px;
  background: radial-gradient(circle, rgba(231, 176, 94, 0.16) 0%, rgba(201, 145, 60, 0.05) 38%, transparent 70%);
  animation: orb1 22s ease-in-out infinite;
}

/* 陶土色光斑 —— 右下 */
.workspace::before {
  content: "";
  position: fixed;
  border-radius: 50%;
  pointer-events: none;
  z-index: 0;
  width: 660px;
  height: 660px;
  bottom: -290px;
  right: -230px;
  background: radial-gradient(circle, rgba(201, 111, 61, 0.12) 0%, rgba(224, 138, 85, 0.04) 42%, transparent 70%);
  animation: orb2 26s ease-in-out infinite;
}

@keyframes bgShift {
  0%, 100% { background-position: 0% 0%, 0% 0%, 0% 0%; }
  50% { background-position: 0% 0%, 0% 0%, 100% 100%; }
}
@keyframes orb1 {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(130px, 80px) scale(1.18); }
  66% { transform: translate(-40px, 140px) scale(0.86); }
}
@keyframes orb2 {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(-100px, -60px) scale(1.14); }
  66% { transform: translate(60px, -120px) scale(0.9); }
}

.workspace {
  width: min(1760px, 100%);
  margin: 0 auto;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 370px;
  gap: 22px;
  position: relative;
  z-index: 1;
}

.chat-card,
.sidebar {
  min-height: calc(100vh - 48px);
  height: calc(100vh - 48px);
  background: var(--color-surface);
  backdrop-filter: blur(32px) saturate(1.15);
  -webkit-backdrop-filter: blur(32px) saturate(1.15);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  transition: border-color var(--duration-slow) var(--ease-in-out), box-shadow var(--duration-slow) var(--ease-in-out);
}
.chat-card {
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-glow-gold), var(--shadow-lg), var(--shadow-inner-glow);
}
.chat-card:hover {
  border-color: rgba(231, 176, 94, 0.18);
}

.chat-body {
  flex: 1;
  min-height: 0;
  display: flex;
  align-items: stretch;
}
.chat-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.sidebar {
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-glow-copper), var(--shadow-lg), var(--shadow-inner-glow);
}
.sidebar:hover {
  border-color: rgba(224, 138, 85, 0.18);
}

/* ── 顶部：品牌 + 客服 ───────────────────────────────────── */
.chat-header,
.sidebar-header {
  padding: 22px 26px 18px;
  border-bottom: 1px solid var(--color-border-light);
}

.chat-header {
  display: flex;
  align-items: center;
  gap: 20px;
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  width: 100%;
}

.brand {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
}

.brand-mark {
  flex-shrink: 0;
  width: 48px;
  height: 48px;
  display: grid;
  place-items: center;
  border-radius: 14px;
  color: var(--color-accent);
  background:
    radial-gradient(120% 120% at 30% 20%, rgba(231, 176, 94, 0.28) 0%, rgba(201, 145, 60, 0.10) 55%, rgba(18, 13, 9, 0.4) 100%);
  border: 1px solid var(--color-gold-line);
  box-shadow: 0 8px 24px rgba(231, 176, 94, 0.10), var(--shadow-inner-glow);
}
.brand-mark svg {
  width: 24px;
  height: 24px;
}

.brand-text {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.brand-name {
  margin: 0;
  display: flex;
  align-items: baseline;
  font-family: var(--font-serif);
  font-size: 25px;
  font-weight: 700;
  line-height: 1.15;
  letter-spacing: 0.01em;
  background: linear-gradient(105deg, #fbefd9 0%, #e7b05e 62%, #c98a3c 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  white-space: nowrap;
}
.brand-divider {
  margin: 0 6px;
  font-size: 18px;
  color: var(--color-text-muted);
  -webkit-text-fill-color: var(--color-text-muted);
}
.brand-name-sub {
  font-size: 16px;
  font-weight: 500;
  letter-spacing: 0.08em;
}

.brand-slogan {
  margin: 0;
  font-size: 11px;
  letter-spacing: 0.14em;
  color: var(--color-text-muted);
  text-transform: uppercase;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 声波装饰 */
.brand-wave {
  display: flex;
  align-items: center;
  gap: 3px;
  height: 22px;
  margin-left: 6px;
  opacity: 0.75;
}
.brand-wave span {
  width: 3px;
  height: 6px;
  border-radius: 2px;
  background: linear-gradient(180deg, rgba(231, 176, 94, 0.9), rgba(201, 111, 61, 0.45));
  animation: waveBar 1.6s ease-in-out infinite;
}
.brand-wave span:nth-child(1) { animation-delay: 0s; }
.brand-wave span:nth-child(2) { animation-delay: 0.12s; }
.brand-wave span:nth-child(3) { animation-delay: 0.24s; }
.brand-wave span:nth-child(4) { animation-delay: 0.36s; }
.brand-wave span:nth-child(5) { animation-delay: 0.48s; }
.brand-wave span:nth-child(6) { animation-delay: 0.60s; }
@keyframes waveBar {
  0%, 100% { height: 5px; opacity: 0.45; }
  50% { height: 18px; opacity: 1; }
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.service-info {
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 7px 16px 7px 8px;
  background: var(--color-surface-raised);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-inner-glow);
}

.service-avatar-wrapper {
  position: relative;
  flex-shrink: 0;
}

.service-avatar {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  object-fit: cover;
  padding: 3px;
  background: conic-gradient(var(--color-accent), var(--color-warm), var(--color-accent-strong), var(--color-accent));
  box-shadow: 0 0 18px var(--color-accent-glow), 0 4px 12px rgba(0, 0, 0, 0.35);
  animation: avatarSpin 6s linear infinite;
}
@keyframes avatarSpin {
  to { transform: rotate(360deg); }
}

.status-indicator {
  position: absolute;
  bottom: 2px;
  right: 2px;
  width: 13px;
  height: 13px;
  background: var(--color-success);
  border: 3px solid #1b140e;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

.service-details {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.service-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
  letter-spacing: 0.02em;
}

.service-status {
  font-size: 11.5px;
  color: var(--color-success);
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 5px;
  white-space: nowrap;
}
.service-status::before {
  content: '';
  width: 5px;
  height: 5px;
  background: var(--color-success);
  border-radius: 50%;
}

.clear-button {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface-raised);
  color: var(--color-text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--duration-base) var(--ease-out-expo);
  white-space: nowrap;
}
.clear-icon {
  color: var(--color-accent);
  font-size: 12px;
}
.clear-button:hover {
  background: var(--color-accent-soft);
  border-color: var(--color-gold-line);
  color: var(--color-accent);
  transform: translateY(-1px);
  box-shadow: 0 4px 18px rgba(231, 176, 94, 0.12);
}

/* ── 对话区 ─────────────────────────────────────────────── */
.messages {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  scrollbar-gutter: stable;
  padding: 22px 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.messages::-webkit-scrollbar,
.sidebar-list::-webkit-scrollbar {
  width: 8px;
}
.messages::-webkit-scrollbar-thumb,
.sidebar-list::-webkit-scrollbar-thumb {
  background: rgba(231, 176, 94, 0.22);
  border-radius: 999px;
}
.messages::-webkit-scrollbar-track,
.sidebar-list::-webkit-scrollbar-track {
  background: transparent;
}

/* Turn 卡片 */
.turn-card {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 20px 24px 22px;
  background: linear-gradient(160deg, rgba(33, 25, 18, 0.68) 0%, rgba(22, 16, 11, 0.58) 100%);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  transition: all var(--duration-base) var(--ease-out-expo);
  position: relative;
  overflow: hidden;
  animation: msgEnter 0.42s var(--ease-out-back) both;
}
@keyframes msgEnter {
  from { opacity: 0; transform: translateY(22px) scale(0.985); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}
.turn-card::before {
  content: "";
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(105deg, transparent 42%, rgba(231, 176, 94, 0.07) 50%, transparent 58%);
  transition: left 0.55s ease;
  pointer-events: none;
  z-index: 2;
}
.turn-card:hover::before {
  left: 100%;
}
.turn-card:hover {
  background: linear-gradient(160deg, rgba(38, 29, 21, 0.78) 0%, rgba(26, 19, 13, 0.66) 100%);
  border-color: var(--color-border-strong);
  box-shadow: var(--shadow-md), 0 0 42px rgba(231, 176, 94, 0.05);
  transform: translateY(-2px);
}

.turn-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-bottom: 12px;
  border-bottom: 1px dashed rgba(231, 176, 94, 0.16);
}

.turn-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 12px;
  background: linear-gradient(135deg, #f1c98d 0%, #c98a3c 100%);
  color: #231708;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.04em;
  border-radius: var(--radius-sm);
  box-shadow: 0 2px 12px rgba(231, 176, 94, 0.22);
}

.turn-label {
  font-size: 12px;
  color: var(--color-text-muted);
  font-weight: 500;
  letter-spacing: 0.04em;
}

.turn-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
  font-weight: 600;
}

.avatar-wrapper {
  position: relative;
  flex-shrink: 0;
}

.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  object-fit: cover;
  border: 2px solid rgba(243, 234, 219, 0.12);
  background: #1a130d;
  transition: all var(--duration-base) var(--ease-out-expo);
}

.user-avatar .avatar {
  border: 2px solid transparent;
  background: linear-gradient(#1a130d, #1a130d) padding-box,
              linear-gradient(135deg, var(--color-info), var(--color-accent)) border-box;
  box-shadow: 0 2px 14px var(--color-info-soft);
}

.service-avatar .avatar {
  border-color: var(--color-success);
  box-shadow: 0 2px 10px var(--color-success-soft);
}

.status-dot {
  position: absolute;
  bottom: 1px;
  right: 1px;
  width: 11px;
  height: 11px;
  background: var(--color-success);
  border: 2px solid #1b140e;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.65; transform: scale(1.12); }
}

.agent-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.agent-name {
  font-size: 14.5px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.agent-label {
  font-size: 11.5px;
  color: var(--color-text-muted);
  font-weight: 500;
  letter-spacing: 0.04em;
}

.user-section .agent-name {
  color: var(--color-info);
}

.bot-section .agent-name {
  color: var(--color-accent);
}

/* 用户侧（书友）头部镜像到右侧，与客服侧（小听）分开 */
.user-section .section-header {
  flex-direction: row-reverse;
}

.user-section .agent-info {
  align-items: flex-end;
  text-align: right;
}

/* 气泡 */
.turn-bubble {
  padding: 14px 18px;
  border-radius: var(--radius-md);
  max-width: 100%;
}

.user-bubble {
  background: linear-gradient(135deg, #f2cd96 0%, #dfa257 55%, #cf8a41 100%);
  border: 1px solid rgba(255, 236, 205, 0.35);
  color: #241708;
  box-shadow: 0 6px 22px rgba(231, 176, 94, 0.18);
  margin-left: auto;
  max-width: 85%;
}

.bot-bubble {
  background: linear-gradient(165deg, rgba(20, 15, 10, 0.72) 0%, rgba(15, 11, 8, 0.62) 100%);
  border: 1px solid var(--color-border);
  border-left: 2px solid rgba(231, 176, 94, 0.26);
  color: var(--color-text-primary);
  box-shadow: var(--shadow-xs);
}

.bot-messages {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.turn-bubble p {
  margin: 0;
  font-size: 15px;
  line-height: 1.72;
  white-space: pre-wrap;
  word-break: break-word;
}

.user-bubble p {
  color: #241708;
}

/* 历史分隔线 */
.history-divider {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 14px;
  color: var(--color-text-muted);
  font-size: 12.5px;
  padding: 6px 0;
}

.history-divider::before,
.history-divider::after {
  content: "";
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--color-border-strong), transparent);
}

.history-divider span {
  padding: 6px 14px;
  border-radius: var(--radius-full);
  background: var(--color-surface-raised);
  border: 1px solid var(--color-border);
  font-size: 12px;
  letter-spacing: 0.04em;
}

/* 欢迎页 */
.welcome {
  flex-shrink: 0;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}
.welcome-card {
  position: relative;
  max-width: 520px;
  width: 100%;
  padding: 42px 40px 38px;
  background:
    radial-gradient(120% 90% at 50% 0%, rgba(231, 176, 94, 0.10) 0%, transparent 62%),
    linear-gradient(170deg, rgba(33, 25, 18, 0.78) 0%, rgba(20, 15, 10, 0.62) 100%);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  text-align: center;
  box-shadow: var(--shadow-glow-gold), var(--shadow-lg);
  overflow: hidden;
  animation: welcomeFloat 0.62s var(--ease-out-back);
}
.welcome-card::before {
  content: "";
  position: absolute;
  inset: 0 0 auto 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(231, 176, 94, 0.45), transparent);
}
@keyframes welcomeFloat {
  from { opacity: 0; transform: translateY(34px) scale(0.95); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}
.welcome-glow {
  position: absolute;
  top: -110px;
  left: 50%;
  transform: translateX(-50%);
  width: 380px;
  height: 380px;
  background: radial-gradient(circle, rgba(231, 176, 94, 0.10) 0%, rgba(231, 176, 94, 0.03) 45%, transparent 70%);
  pointer-events: none;
}
.welcome-tag {
  position: relative;
  display: inline-block;
  margin-bottom: 22px;
  padding: 5px 14px;
  border: 1px solid var(--color-gold-line);
  border-radius: var(--radius-full);
  background: var(--color-accent-soft-bg);
  color: var(--color-accent);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.16em;
}

.welcome-avatar-wrapper {
  position: relative;
  display: inline-block;
  margin-bottom: 20px;
}
.welcome-avatar {
  width: 86px;
  height: 86px;
  border-radius: 50%;
  padding: 4px;
  object-fit: cover;
  background: conic-gradient(var(--color-accent), var(--color-warm), var(--color-accent-strong), var(--color-accent));
  animation: avatarSpin 7s linear infinite;
  box-shadow: 0 0 38px rgba(231, 176, 94, 0.22);
}
.welcome-status-pulse {
  position: absolute;
  bottom: 6px;
  right: 6px;
  width: 17px;
  height: 17px;
  background: var(--color-success);
  border: 3px solid #16100b;
  border-radius: 50%;
  animation: pulse 2s infinite;
  box-shadow: 0 0 16px rgba(116, 211, 168, 0.40);
}
.welcome-greeting {
  margin: 0 0 10px;
  font-family: var(--font-serif);
  font-size: 28px;
  font-weight: 600;
  letter-spacing: 0.02em;
  background: linear-gradient(110deg, #fbefd9 0%, #e7b05e 70%, #c98a3c 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.welcome-subtitle {
  margin: 0 auto 28px;
  max-width: 380px;
  color: var(--color-text-secondary);
  font-size: 14.5px;
  line-height: 1.8;
}
.welcome-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: center;
  margin-bottom: 26px;
}
.welcome-chip {
  padding: 9px 18px;
  border: 1px solid var(--color-gold-line);
  border-radius: var(--radius-full);
  background: var(--color-accent-soft-bg);
  color: var(--color-accent);
  font-size: 13.5px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--duration-base) var(--ease-out-expo);
}
.welcome-chip:hover:not(:disabled) {
  background: var(--color-accent-soft);
  border-color: var(--color-accent);
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(231, 176, 94, 0.16);
}
.welcome-chip:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.welcome-features {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  justify-content: center;
  margin: 0;
  padding-top: 20px;
  border-top: 1px solid var(--color-border-light);
  color: var(--color-text-muted);
  font-size: 12.5px;
  letter-spacing: 0.02em;
}

/* 输入中的提示 */
.typing-indicator {
  flex-shrink: 0;
  display: flex;
  align-items: flex-end;
  gap: 10px;
  padding: 0 22px;
  animation: msgEnter 0.3s var(--ease-out-expo);
}
.avatar-small {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  object-fit: cover;
  border: 2px solid var(--color-success);
  box-shadow: 0 0 12px rgba(116, 211, 168, 0.22);
}
.typing-bubble {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 11px 17px;
  background: var(--color-surface-raised);
  border: 1px solid var(--color-border);
  border-radius: 18px 18px 18px 6px;
  box-shadow: var(--shadow-sm);
}
.typing-dots {
  display: flex;
  gap: 4px;
  align-items: center;
}
.typing-dots span {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--color-accent);
  animation: dotBounce 1.2s ease-in-out infinite;
}
.typing-dots span:nth-child(1) { animation-delay: 0s; }
.typing-dots span:nth-child(2) { animation-delay: 0.2s; }
.typing-dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes dotBounce {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.3; }
  30% { transform: translateY(-8px); opacity: 1; }
}
.typing-label {
  font-size: 12.5px;
  color: var(--color-text-muted);
}

/* ── 对象卡片 ────────────────────────────────────────────── */
.object-card {
  display: flex;
  flex-direction: column;
  gap: 7px;
  min-width: 220px;
  padding: 14px;
  border-radius: 14px;
  background: linear-gradient(160deg, rgba(231, 176, 94, 0.10) 0%, rgba(18, 13, 9, 0.62) 100%);
  border: 1px solid var(--color-gold-line);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
}

.object-card-badge {
  align-self: flex-start;
  padding: 3px 11px;
  border-radius: var(--radius-full);
  background: rgba(231, 176, 94, 0.10);
  border: 1px solid var(--color-gold-line);
  color: var(--color-accent);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.10em;
}

.object-card-title {
  font-family: var(--font-serif);
  font-size: 16px;
  font-weight: 600;
  line-height: 1.5;
  color: var(--color-text-primary);
}

.object-card-meta {
  font-size: 12.5px;
  color: var(--color-text-secondary);
  line-height: 1.5;
}

.object-card-price {
  font-size: 16px;
  font-weight: 700;
  color: var(--color-accent);
  letter-spacing: 0.01em;
}

.object-card-image {
  width: 100%;
  height: 150px;
  object-fit: cover;
  border-radius: 10px;
  margin-bottom: 4px;
  border: 1px solid var(--color-border-light);
  background: var(--color-surface-field);
}

.turn-bubble .object-card {
  min-width: 200px;
}

/* 用户气泡里的对象卡片：在暖金色底上转为深色描边 */
.user-bubble .object-card {
  background: rgba(36, 22, 8, 0.14);
  border-color: rgba(36, 22, 8, 0.28);
  box-shadow: none;
}
.user-bubble .object-card-badge {
  background: rgba(36, 22, 8, 0.14);
  border-color: rgba(36, 22, 8, 0.30);
  color: #2a1a08;
}
.user-bubble .object-card-title,
.user-bubble .object-card-price {
  color: #241708;
}
.user-bubble .object-card-meta {
  color: rgba(36, 23, 8, 0.78);
}
.user-bubble .status-badge {
  background: rgba(36, 23, 8, 0.16);
  border-color: rgba(36, 23, 8, 0.34);
  color: #241708;
}

/* 状态徽章 */
.status-badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 11px;
  border-radius: var(--radius-full);
  font-size: 11.5px;
  font-weight: 600;
  letter-spacing: 0.02em;
}
.status-warning {
  background: var(--color-warm-soft);
  color: var(--color-warm);
  border: 1px solid rgba(224, 138, 85, 0.25);
}
.status-info {
  background: var(--color-info-soft);
  color: var(--color-info);
  border: 1px solid rgba(127, 188, 216, 0.25);
}
.status-success {
  background: var(--color-success-soft);
  color: var(--color-success);
  border: 1px solid rgba(116, 211, 168, 0.25);
}
.status-muted {
  background: rgba(138, 124, 104, 0.12);
  color: var(--color-text-muted);
  border: 1px solid rgba(138, 124, 104, 0.18);
}
.status-danger {
  background: var(--color-danger-soft);
  color: var(--color-danger);
  border: 1px solid rgba(239, 128, 128, 0.25);
}

/* 复制按钮 */
.bot-text-row { display: flex; align-items: flex-start; gap: 8px; }
.bot-text-row p { flex: 1; margin: 0; }
.user-text-row { display: flex; align-items: flex-start; gap: 8px; }
.user-text-row p { flex: 1; margin: 0; }
.user-actions {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
  align-items: center;
}
.copy-button {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  padding: 0;
  border: 1px solid var(--color-border-light);
  border-radius: 8px;
  background: var(--color-surface);
  cursor: pointer;
  font-size: 13px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: all var(--duration-base) var(--ease-out-expo);
  color: var(--color-text-muted);
}
.copy-button:hover:not(:disabled) {
  background: var(--color-accent-soft);
  border-color: var(--color-accent);
  color: var(--color-accent-strong);
  transform: scale(1.08);
}
.copy-button:disabled { cursor: not-allowed; opacity: 0.65; }
.copy-button.copy-done {
  background: var(--color-success-soft);
  border-color: var(--color-success);
  color: var(--color-success);
}
.copy-button.copy-button-on-accent {
  background: rgba(36, 23, 8, 0.16);
  border-color: rgba(36, 23, 8, 0.28);
  color: #241708;
  backdrop-filter: blur(2px);
}
.copy-button.copy-button-on-accent:hover:not(:disabled) {
  background: rgba(36, 23, 8, 0.28);
  border-color: rgba(36, 23, 8, 0.45);
  color: #1a1004;
}
.copy-button.copy-button-on-accent.copy-done {
  background: rgba(255, 250, 240, 0.92);
  border-color: #ffffff;
  color: var(--color-success);
}

/* 推荐追问 */
.suggestion-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--color-border-light);
}
.suggestion-chip {
  padding: 6px 14px;
  border: 1px solid var(--color-gold-line);
  border-radius: var(--radius-full);
  background: var(--color-accent-soft-bg);
  color: var(--color-accent);
  font-size: 12.5px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--duration-base) var(--ease-out-expo);
}
.suggestion-chip:hover:not(:disabled) {
  background: var(--color-accent-soft);
  border-color: var(--color-accent);
  transform: translateY(-1px);
}
.suggestion-chip:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* ── 底部输入区 ─────────────────────────────────────────── */
.composer {
  flex-shrink: 0;
  display: flex;
  align-items: stretch;
  gap: 12px;
  padding: 18px 24px 20px;
  border-top: 1px solid var(--color-border-light);
  background: linear-gradient(180deg, rgba(16, 12, 8, 0.42), rgba(12, 9, 6, 0.66));
}

.composer-field {
  position: relative;
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
}

.composer-hint {
  position: absolute;
  left: 14px;
  font-size: 15px;
  opacity: 0.6;
  pointer-events: none;
}

.composer input {
  width: 100%;
  min-width: 0;
  min-height: 48px;
  padding: 12px 14px 12px 40px;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-md);
  background: var(--color-surface-field);
  color: var(--color-text-primary);
  font-size: 15px;
  line-height: 1.4;
  transition: border-color var(--duration-fast) var(--ease-in-out), box-shadow var(--duration-fast) var(--ease-in-out);
}
.composer input::placeholder {
  color: var(--color-text-muted);
}
.composer input:focus {
  outline: none;
  border-color: var(--color-accent);
  box-shadow: 0 0 0 3px var(--color-accent-soft), inset 0 1px 0 rgba(255, 255, 255, 0.04);
}

.composer button,
.secondary-button,
.tab-button {
  min-height: 42px;
  padding: 9px 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  color: var(--color-text-primary);
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  line-height: 1.2;
  transition:
    transform var(--duration-fast) var(--ease-out-expo),
    box-shadow var(--duration-fast) var(--ease-out-expo),
    background var(--duration-fast) var(--ease-in-out),
    border-color var(--duration-fast) var(--ease-in-out);
}

.composer button:hover:not(:disabled),
.secondary-button:hover:not(:disabled),
.tab-button:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}

.composer button:active:not(:disabled),
.secondary-button:active:not(:disabled),
.tab-button:active:not(:disabled) {
  transform: translateY(0);
}

.composer button:disabled,
.secondary-button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.composer button {
  min-width: 96px;
  padding-inline: 22px;
  background: linear-gradient(135deg, #f2cd96 0%, #d9a05a 55%, #c08a42 100%);
  border-color: transparent;
  color: #231708;
  box-shadow: 0 14px 28px rgba(231, 176, 94, 0.18);
}
.composer button:hover:not(:disabled) {
  box-shadow: 0 18px 36px rgba(231, 176, 94, 0.24);
  transform: translateY(-2px);
}

.error-message,
.sidebar-error {
  margin: 0;
  padding: 0 24px 14px;
  color: var(--color-danger);
  font-size: 12.5px;
  font-weight: 500;
}

/* ── 右侧听书业务台 ─────────────────────────────────────── */
.sidebar-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.chat-header h1,
.sidebar-header h2 {
  margin: 0;
  line-height: 1.2;
  letter-spacing: -0.01em;
}

.sidebar-header h2 {
  font-family: var(--font-serif);
  font-size: 21px;
  font-weight: 700;
  background: linear-gradient(120deg, #fbefd9 0%, var(--color-warm) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.sidebar-chip {
  flex-shrink: 0;
  padding: 3px 9px;
  border: 1px solid var(--color-gold-line);
  border-radius: var(--radius-full);
  color: var(--color-accent);
  background: var(--color-accent-soft-bg);
  font-size: 9.5px;
  font-weight: 700;
  letter-spacing: 0.16em;
}

.chat-header p,
.sidebar-header p {
  margin: 9px 0 0;
  color: var(--color-text-secondary);
  font-size: 12.5px;
  line-height: 1.6;
  letter-spacing: 0.01em;
}

/* 账号切换 */
.sidebar-user {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 24px;
  border-bottom: 1px solid var(--color-border-light);
}
.sidebar-user-field {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}
.sidebar-user-field span {
  color: var(--color-text-secondary);
  font-size: 12.5px;
  font-weight: 500;
  white-space: nowrap;
}
.sidebar-user-field input {
  flex: 1;
  min-width: 0;
  min-height: 42px;
  padding: 9px 12px;
  border: 1px solid var(--color-border-strong);
  border-radius: var(--radius-md);
  background: var(--color-surface-field);
  color: var(--color-text-primary);
  font-size: 14px;
  line-height: 1.4;
  transition: border-color var(--duration-fast) var(--ease-in-out), box-shadow var(--duration-fast) var(--ease-in-out);
}
.sidebar-user-field input::placeholder {
  color: var(--color-text-muted);
}
.sidebar-user-field input:focus {
  outline: none;
  border-color: var(--color-accent);
  box-shadow: 0 0 0 3px var(--color-accent-soft);
}
.sidebar-user .secondary-button {
  flex-shrink: 0;
  white-space: nowrap;
}

.tabs {
  display: flex;
  gap: 8px;
  padding: 16px 24px 14px;
  border-bottom: 1px solid var(--color-border-light);
}

.tab-button {
  flex: 1;
  min-width: 80px;
  letter-spacing: 0.02em;
}

.tab-button.active {
  background: linear-gradient(135deg, #f0c887 0%, #c98a3c 100%);
  border-color: transparent;
  color: #231708;
  box-shadow: 0 4px 16px rgba(231, 176, 94, 0.22);
}

.sidebar-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 16px 24px 24px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.sidebar-empty {
  margin: auto;
  max-width: 260px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  color: var(--color-text-muted);
  text-align: center;
  line-height: 1.7;
  font-size: 13px;
}
.sidebar-empty-icon {
  font-size: 26px;
  opacity: 0.55;
}

.sidebar-card {
  padding: 14px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: linear-gradient(165deg, rgba(34, 26, 18, 0.72) 0%, rgba(22, 16, 11, 0.62) 100%);
  display: flex;
  flex-direction: column;
  gap: 11px;
  transition: all var(--duration-base) var(--ease-out-expo);
}
.sidebar-card:hover {
  background: linear-gradient(165deg, rgba(40, 31, 22, 0.82) 0%, rgba(26, 19, 13, 0.70) 100%);
  border-color: var(--color-gold-line);
  transform: translateY(-3px);
  box-shadow: var(--shadow-md), 0 0 30px rgba(231, 176, 94, 0.08);
}

.card-image-wrapper {
  position: relative;
  width: 100%;
  height: 144px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  background: var(--color-surface-field);
  border: 1px solid var(--color-border-light);
  display: flex;
  align-items: center;
  justify-content: center;
}
.card-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform var(--duration-base) var(--ease-out-expo);
}
.sidebar-card:hover .card-image {
  transform: scale(1.06);
}
.card-image-placeholder {
  font-size: 40px;
  opacity: 0.45;
}
.card-type-chip {
  position: absolute;
  top: 9px;
  left: 9px;
  padding: 3px 10px;
  border-radius: var(--radius-full);
  background: rgba(10, 7, 5, 0.72);
  border: 1px solid var(--color-gold-line);
  color: var(--color-accent);
  font-size: 10.5px;
  font-weight: 600;
  letter-spacing: 0.08em;
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
}

.card-top {
  display: flex;
  gap: 12px;
  justify-content: space-between;
  align-items: flex-start;
}

.card-title {
  font-family: var(--font-serif);
  font-size: 15px;
  line-height: 1.5;
  color: var(--color-text-primary);
  font-weight: 600;
}

.card-amount {
  flex-shrink: 0;
  color: var(--color-accent);
  font-weight: 700;
  font-size: 15px;
}

.card-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12.5px;
  color: var(--color-text-secondary);
  word-break: break-all;
}

.full-width {
  width: 100%;
}

.sidebar .secondary-button.full-width {
  min-height: 42px;
  border-color: var(--color-gold-line);
  background: var(--color-accent-soft-bg);
  color: var(--color-accent);
  font-weight: 600;
}
.sidebar .secondary-button.full-width:hover:not(:disabled) {
  background: var(--color-accent-soft);
  border-color: var(--color-accent);
  color: var(--color-accent);
  box-shadow: 0 6px 18px rgba(231, 176, 94, 0.14);
}

/* ── 响应式 ─────────────────────────────────────────────── */
@media (max-width: 1180px) {
  .workspace {
    grid-template-columns: 1fr;
  }

  .chat-header {
    flex-direction: column;
    align-items: stretch;
  }

  .header-content {
    flex-direction: column;
    align-items: stretch;
    gap: 14px;
  }

  .brand {
    width: 100%;
  }

  .header-actions {
    width: 100%;
    justify-content: space-between;
  }

  .sidebar {
    min-height: auto;
    height: auto;
  }
}

@media (max-width: 860px) {
  .brand-wave {
    display: none;
  }
}

@media (max-width: 720px) {
  .app-shell {
    padding: 0;
  }

  .workspace {
    gap: 0;
  }

  .chat-card,
  .sidebar {
    min-height: auto;
    height: auto;
    border-radius: 0;
    border-left: none;
    border-right: none;
  }

  .chat-card {
    min-height: 100vh;
  }

  .brand-slogan {
    white-space: normal;
  }

  .brand-name {
    font-size: 21px;
  }

  .brand-name-sub {
    font-size: 14px;
  }

  .composer {
    flex-direction: column;
    align-items: stretch;
  }

  .composer button {
    width: 100%;
  }
}
</style>