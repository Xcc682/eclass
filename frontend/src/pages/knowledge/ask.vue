<template>
  <div class="ask-page">
    <aside class="history-panel">
      <button class="new-chat" :disabled="sessionLoading" @click="newChat">＋ 新对话</button>
      <div class="history-panel__title">
        <h3>问答历史</h3>
        <button :disabled="sessionsLoading" @click="refreshSessions">刷新</button>
      </div>
      <div v-if="sessionsLoading" class="history-state">正在读取历史…</div>
      <div v-else-if="sessionsError" class="history-state history-state--error">
        <span>{{ sessionsError }}</span>
        <button @click="refreshSessions">重试</button>
      </div>
      <div v-else-if="!sessions.length" class="history-state">暂无历史对话</div>
      <template v-else>
        <div
          v-for="item in sessions"
          :key="item.id"
          class="session"
          :class="{ active: item.id === sessionId }"
          @click="openSession(item.id)"
        >
          <span>{{ item.title }}</span>
          <button
            class="session__delete"
            :disabled="sessionLoading || deletingSessionId === item.id"
            @click.stop="confirmDeleteSession(item)"
          >
            {{ deletingSessionId === item.id ? '…' : '删除' }}
          </button>
        </div>
      </template>
    </aside>

    <main>
      <div class="mobile-history">
        <button class="mobile-history__new" @click="newChat">＋ 新对话</button>
        <div class="mobile-history__sessions">
          <div v-for="item in sessions" :key="item.id" :class="{active:item.id===sessionId}" @click="openSession(item.id)"><span>{{ item.title }}</span><button @click.stop="confirmDeleteSession(item)">×</button></div>
        </div>
      </div>
      <header>
        <span>基于已审核资料回答</span>
        <strong>引用可追溯</strong>
      </header>

      <div class="messages">
        <div v-if="sessionLoading" class="page-state">正在打开历史对话…</div>
        <div v-else-if="sessionError" class="page-state page-state--error">
          {{ sessionError }}
          <button @click="sessionId && openSession(sessionId)">重新打开</button>
        </div>

        <div v-else-if="!messages.length" class="welcome">
          <b>可以这样问</b>
          <span @click="useSuggestion('红船精神的核心内涵是什么？')">红船精神的核心内涵是什么？</span>
          <span @click="useSuggestion('入党申请书应包含哪些内容？')">入党申请书应包含哪些内容？</span>
        </div>

        <section v-for="(message,index) in messages" :key="index" :class="['message', message.role]">
          <div class="bubble">{{ message.content }}</div>
          <div v-if="message.citations?.length" class="citations">
            <article v-for="citation in message.citations" :key="citation.chunk_id" @click="openCitation(citation)">
              <b>[{{ citation.index }}] {{ citation.document_title }}<span v-if="citation.relevance_score" class="rel-badge">{{ citation.relevance_score >= 8 ? '高度相关' : citation.relevance_score >= 5 ? '相关' : '低相关' }}</span></b>
              <p>{{ citation.excerpt }}</p>
              <small v-if="citation.relevance_reason">{{ citation.relevance_reason }}</small>
              <small>{{ citation.source }} · 第 {{ citation.chunk_index + 1 }} 段</small>
            </article>
          </div>
        </section>

        <div v-if="asking" class="thinking">正在查找依据并组织回答…</div>
      </div>

      <footer>
        <textarea
          v-model="question"
          maxlength="1000"
          placeholder="请输入问题；Enter 发送，Shift+Enter 换行"
          :disabled="sessionLoading"
          @keydown.enter.exact.prevent="send"
        />
        <button :disabled="asking || sessionLoading || !question.trim()" @click="send">
          {{ asking ? '等待中' : '发送' }}
        </button>
      </footer>
    </main>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { onHide, onUnload } from '@dcloudio/uni-app'
import { knowledgeApi, type Citation, type KnowledgeMessage, type KnowledgeSession } from '@/api/knowledge'

const sessions = ref<KnowledgeSession[]>([])
const messages = ref<Array<Pick<KnowledgeMessage, 'role'|'content'|'citations'>>>([])
const question = ref('')
const sessionId = ref<string>()
const asking = ref(false)
const sessionsLoading = ref(false)
const sessionsError = ref('')
const sessionLoading = ref(false)
const sessionError = ref('')
const deletingSessionId = ref('')

let alive = true
let requestToken = 0

function isCurrent(token: number) {
  return alive && token === requestToken
}

function cancelPendingRequest() {
  requestToken += 1
  asking.value = false
}

async function refreshSessions() {
  const token = requestToken
  sessionsLoading.value = true
  sessionsError.value = ''
  try {
    const data = await knowledgeApi.sessions()
    if (!alive || token !== requestToken) return
    sessions.value = data
  } catch (event: any) {
    if (!alive || token !== requestToken) return
    sessionsError.value = event.message || '问答历史暂时加载失败'
  } finally {
    if (alive && token === requestToken) sessionsLoading.value = false
  }
}

function newChat() {
  cancelPendingRequest()
  sessionId.value = undefined
  sessionError.value = ''
  messages.value = []
}

function showConfirm(title: string, content: string) {
  return new Promise<boolean>(resolve => {
    uni.showModal({
      title,
      content,
      confirmText: '删除',
      confirmColor: '#8d211b',
      cancelText: '取消',
      success: result => resolve(Boolean(result.confirm)),
      fail: () => resolve(false),
    })
  })
}

async function confirmDeleteSession(item: KnowledgeSession) {
  if (deletingSessionId.value || sessionLoading.value) return
  const confirmed = await showConfirm('删除会话', `确定删除“${item.title || '这条会话'}”吗？删除后不可恢复。`)
  if (!confirmed) return
  deletingSessionId.value = item.id
  try {
    await knowledgeApi.deleteSession(item.id)
    sessions.value = sessions.value.filter(session => session.id !== item.id)
    if (sessionId.value === item.id) {
      newChat()
    }
    uni.showToast({ title: '已删除会话', icon: 'success' })
  } catch (event: any) {
    uni.showToast({ title: event.message || '删除失败，请稍后重试', icon: 'none' })
  } finally {
    deletingSessionId.value = ''
  }
}

async function openSession(id: string) {
  cancelPendingRequest()
  const token = requestToken
  sessionLoading.value = true
  sessionError.value = ''
  try {
    const data = await knowledgeApi.session(id)
    if (!isCurrent(token)) return
    sessionId.value = id
    messages.value = data.messages || []
  } catch (event: any) {
    if (!isCurrent(token)) return
    sessionError.value = event.message || '历史对话暂时无法打开'
  } finally {
    if (isCurrent(token)) sessionLoading.value = false
  }
}

function useSuggestion(value: string) {
  if (asking.value || sessionLoading.value) return
  question.value = value
  send()
}

async function send() {
  const value = question.value.trim()
  if (!value || asking.value || sessionLoading.value) return
  const token = requestToken + 1
  requestToken = token
  messages.value.push({ role: 'user', content: value, citations: [] })
  question.value = ''
  sessionError.value = ''
  asking.value = true
  try {
    const result = await knowledgeApi.ask(value, sessionId.value)
    if (!isCurrent(token)) return
    sessionId.value = result.session_id
    messages.value.push({ role: 'assistant', content: result.answer, citations: result.citations })
    refreshSessions()
  } catch (event: any) {
    if (!isCurrent(token)) return
    messages.value.push({
      role: 'assistant',
      content: event.message || 'AI 服务暂不可用，请稍后重试。',
      citations: [],
    })
  } finally {
    if (isCurrent(token)) {
      asking.value = false
    }
  }
}

function openCitation(citation: Citation) {
  uni.navigateTo({ url: `/pages/knowledge/document?id=${citation.document_id}&chunk=${citation.chunk_index}` })
}

onMounted(refreshSessions)
onHide(cancelPendingRequest)
onUnload(() => { alive = false; cancelPendingRequest() })
onUnmounted(() => { alive = false; cancelPendingRequest() })
</script>

<style scoped>
.ask-page{height:calc(100vh - 100rpx);display:grid;grid-template-columns:260rpx 1fr;background:#f4efe6;color:#312b25}
.history-panel{padding:24rpx 16rpx;background:#332f2b;color:#eee4d5;overflow:auto}
.new-chat{width:100%;border:1rpx solid #a89985;background:transparent;color:#fff;border-radius:14rpx;padding:18rpx;font-weight:700}
.new-chat:disabled,.session__delete:disabled,.history-panel__title button:disabled{opacity:.45}
.history-panel__title{display:flex;align-items:center;justify-content:space-between;margin:30rpx 8rpx 14rpx}
.history-panel__title h3{font-size:20rpx;margin:0;color:#bfb3a3}
.history-panel__title button,.history-state button{border:0;background:transparent;color:#f1cf82;font-size:20rpx}
.history-state{display:grid;gap:12rpx;padding:18rpx 10rpx;color:#bfb3a3;font-size:21rpx;line-height:1.5}
.history-state--error{color:#f0b2a8}
.session{width:100%;display:flex;align-items:center;gap:8rpx;background:transparent;color:#e6dac9;text-align:left;padding:10rpx 8rpx;border-radius:12rpx}
.session span{flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;padding:6rpx 4rpx}
.session.active{background:rgba(255,255,255,.1);color:#fff}
.session__delete{flex:none;border:0;background:rgba(255,255,255,.08);color:#d8b7a9;border-radius:999rpx;padding:6rpx 12rpx;font-size:18rpx;line-height:1.4}
.session__delete:active{background:rgba(141,33,27,.35);color:#fff}
.ask-page main{min-width:0;display:flex;flex-direction:column}
.ask-page main>header{display:flex;justify-content:space-between;padding:20rpx 28rpx;background:#fffdf8;border-bottom:1rpx solid #e5dac9;font-size:21rpx}
.ask-page main>header strong{color:#8d211b}
.messages{flex:1;overflow:auto;padding:28rpx}
.welcome{max-width:680rpx;margin:50rpx auto;display:grid;gap:14rpx;text-align:center}
.welcome b{font-family:"STKaiti","KaiTi",serif;font-size:34rpx;color:#7f211b}
.welcome span{background:#fffdf8;border:1rpx solid #e4d8c6;border-radius:16rpx;padding:22rpx;box-shadow:0 14rpx 28rpx rgba(80,45,22,.06)}
.page-state{max-width:720rpx;margin:40rpx auto;padding:24rpx;background:#fffdf8;border:1rpx solid #eadfcd;border-radius:16rpx;color:#776b5e;text-align:center}
.page-state--error{color:#8d211b}
.page-state button{margin-left:16rpx;border:0;border-radius:999rpx;background:#8d211b;color:#fff;padding:8rpx 18rpx}
.message{max-width:760rpx;margin:0 auto 22rpx}
.message.user{text-align:right}
.bubble{display:inline-block;max-width:88%;white-space:pre-wrap;text-align:left;background:#fffdf8;border:1rpx solid #e5dac9;border-radius:18rpx;padding:22rpx 24rpx;font-size:25rpx;line-height:1.75;box-shadow:0 10rpx 24rpx rgba(74,45,23,.05)}
.user .bubble{background:#8d211b;color:#fff;border-color:#8d211b}
.citations{display:grid;grid-template-columns:repeat(2,1fr);gap:12rpx;margin-top:14rpx;text-align:left}
.citations article{background:#ede5d8;border-left:5rpx solid #ae8d50;border-radius:10rpx;padding:16rpx}
.citations b{font-size:21rpx;color:#6f201b}
.citations p{font-size:20rpx;line-height:1.5;color:#5e554c;margin:8rpx 0}
.citations small{color:#968878}
.thinking{max-width:760rpx;margin:auto;color:#8d7e70}
.ask-page main>footer{display:flex;gap:12rpx;padding:20rpx 28rpx;background:#fffdf8;border-top:1rpx solid #e5dac9}
.ask-page textarea{flex:1;min-height:72rpx;max-height:180rpx;background:#f5efe6;border-radius:14rpx;padding:16rpx;font-size:24rpx}
.ask-page main>footer button{border:0;border-radius:14rpx;background:#8d211b;color:#fff;padding:0 30rpx;font-weight:700}
.ask-page main>footer button:disabled{opacity:.4}
.mobile-history{display:none}
@media(max-width:600px){.ask-page{grid-template-columns:1fr;height:calc(100vh - 88rpx)}.history-panel{display:none}.mobile-history{display:flex;gap:10rpx;padding:12rpx 16rpx;background:#332f2b}.mobile-history__new{flex:none;margin:0;padding:10rpx 14rpx;border:1px solid rgba(241,207,130,.45);border-radius:2rpx;background:transparent;color:#f1cf82;font-size:16rpx;line-height:1.2}.mobile-history__sessions{display:flex;gap:8rpx;overflow-x:auto}.mobile-history__sessions>div{display:flex;align-items:center;flex:none;max-width:210rpx;padding:7rpx 8rpx 7rpx 12rpx;border:1px solid rgba(255,255,255,.1);color:#d9cdbd;font-size:16rpx}.mobile-history__sessions>div.active{border-color:#f1cf82;color:#fff}.mobile-history__sessions span{max-width:150rpx;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.mobile-history__sessions button{margin:0 0 0 6rpx;padding:0 4rpx;background:transparent;color:#c9a99d;font-size:20rpx;line-height:1}.citations{grid-template-columns:1fr}.ask-page main>header{padding:15rpx 20rpx}.messages{padding:20rpx 17rpx}.ask-page main>footer{padding:15rpx 17rpx}.bubble{font-size:22rpx;border-radius:3rpx}.welcome span{border-radius:3rpx}.ask-page textarea,.ask-page main>footer button{border-radius:2rpx}}
.rel-badge{display:inline-block;margin-left:8rpx;padding:2rpx 8rpx;border-radius:2rpx;font-size:15rpx;font-weight:400;vertical-align:middle;background:rgba(46,125,50,.12);color:#2e7d32}
</style>
