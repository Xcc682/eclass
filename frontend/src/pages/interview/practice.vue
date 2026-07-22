<template>
  <div class="practice">
    <!-- 情景头部 -->
    <div class="practice__header">
      <div class="practice__header-left">
        <div class="practice__header-avatar">谈</div>
        <div class="practice__header-info">
          <span class="practice__header-name">{{ roleName }}</span>
          <span class="practice__header-title">{{ roleTitle }}</span>
        </div>
      </div>
      <div class="practice__header-right">
        <span class="practice__header-hint" @click="showHint">回答提示</span>
        <span class="practice__round">ROUND {{ String(currentRound).padStart(2, '0') }}</span>
      </div>
    </div>

    <!-- 对话区域 -->
    <div class="practice__messages" style="overflow-y:auto;overflow-x:hidden;height:100%;-webkit-overflow-scrolling:touch">
      <div class="practice__messages-inner">
        <ChatBubble
          v-for="msg in messages" :key="msg.id"
          :id="'msg-' + msg.id"
          :role="msg.role"
          :content="msg.content"
          :name="msg.role === 'ai' ? roleName : '我'"
          :annotation="msg.ai_analysis ? getAnalysisHint(msg.ai_analysis) : ''"
        />
        <!-- AI 思考动画 -->
        <div v-if="isThinking" class="practice__thinking">
          <ChatBubble role="ai" content="" name="AI" :is-analyzing="true" />
        </div>
        <div id="msg-bottom"></div>
      </div>
    </div>

    <!-- 底部操作栏 -->
    <div class="practice__phase" v-if="currentPhase">
      <div class="practice__phase-bar"><div class="practice__phase-fill" :style="{width:phaseProgress+'%'}"></div></div>
      <span class="practice__phase-label">{{ currentPhase }} · {{ currentRound }}/6 轮</span>
    </div>
    <ChatInput
      :disabled="isThinking"
      placeholder="输入你的回答..."
      @send="handleSend"
    />

    <!-- 结束按钮 -->
    <div class="practice__end-btn" :class="{ 'practice__end-btn--disabled': !canEnd }" @click="endPractice">
      <span v-if="canEnd">结束并生成报告</span>
      <span v-else>请至少回答 2 个问题（已答 {{ userAnswerCount }}）</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import ChatBubble from '@/components/chat/ChatBubble.vue'
import ChatInput from '@/components/chat/ChatInput.vue'
import { interviewApi } from '@/api/interview'

const scenarioId = ref('')
const roleName = ref('AI 考官')
const roleTitle = ref('')
const currentRound = ref(1)
const isThinking = ref(false)
const currentPhase = ref('开场寒暄')
const phaseProgress = computed(() => {
  const phases = ['开场寒暄','自我认知','入党动机','理论考察','情景假设']
  const idx = phases.indexOf(currentPhase.value)
  return Math.min(100, Math.max(10, (idx + 1) * 20))
})
const messages = ref<Array<{ id: string; role: 'ai' | 'user'; content: string; ai_analysis?: any }>>([])
const practiceId = ref('')

function scrollToBottom() {
  nextTick(() => {
    const el = document.querySelector('.practice__messages')
    if (el) el.scrollTop = el.scrollHeight
  })
}

onLoad(async (query: any) => {
  scenarioId.value = query.scenarioId || '1'
  roleName.value = query.roleName ? decodeURIComponent(query.roleName) : '张老师'
  roleTitle.value = query.roleTitle ? decodeURIComponent(query.roleTitle) : '院党委组织委员'

  // Start practice via backend AI
  isThinking.value = true
  try {
    const data = await interviewApi.startPractice(scenarioId.value)
    practiceId.value = data.id
    const firstQ = data.first_question
    messages.value.push({ id: 'init', role: 'ai', content: firstQ })
  } catch(error: any) {
    messages.value.push({ id: 'init', role: 'ai', content: error.message || 'AI 服务暂不可用，请稍后重试。' })
  }
  isThinking.value = false
})

async function handleSend(text: string) {
  if (isThinking.value || !text.trim() || !practiceId.value) return

  messages.value.push({ id: Date.now().toString(), role: 'user', content: text })
  isThinking.value = true
  currentRound.value++

  try {
    const aiData = await interviewApi.submitResponse(practiceId.value, text)
    const userAnswers = messages.value.filter(m => m.role === 'user').length
    // End at 6+ user answers OR if backend signals completion
    if (aiData?.is_completed || userAnswers >= 6) {
      messages.value.push({
        id: 'done', role: 'ai',
        content: '谈话已结束，点击下方按钮查看AI评估报告。'
      })
    } else {
      messages.value.push({
        id: (Date.now() + 1).toString(), role: 'ai',
        content: aiData?.question || '请继续。',
        ai_analysis: aiData?.analysis,
      })
    }
  } catch(error: any) {
    messages.value.push({
      id: (Date.now() + 1).toString(),
      role: 'ai',
      content: error.message || '网络异常，请重试。'
    })
  }
  isThinking.value = false
}

function getAnalysisHint(analysis: any): string { return analysis?.comment || '' }

async function showHint() {
  if (!practiceId.value) return
  uni.showLoading({ title: '生成提示...' })
  try {
    const data = await interviewApi.getHint(practiceId.value)
    uni.hideLoading()
    if (data?.hint) {
      uni.showModal({ title: '回答提示', content: data.hint, showCancel: false })
    }
  } catch {
    uni.hideLoading()
    uni.showModal({ title: '回答提示', content: '可以从个人经历、理论学习、思想认识等方面来回答。尝试结合具体事例。', showCancel: false })
  }
}

const userAnswerCount = computed(() => messages.value.filter(m => m.role === 'user').length)
const canEnd = computed(() => userAnswerCount.value >= 2)

async function endPractice() {
  if (!practiceId.value) return
  if (userAnswerCount.value < 2) {
    uni.showModal({
      title: '回答太少',
      content: `你只回答了 ${userAnswerCount.value} 个问题，AI 无法进行有效评估。建议至少回答 2-3 个问题后再生成报告。`,
      confirmText: '继续回答',
      showCancel: false
    })
    return
  }
  uni.showLoading({ title: 'AI正在生成报告...' })
  try {
    await interviewApi.endPractice(practiceId.value)
    uni.hideLoading()
    uni.showToast({ title: '报告已生成', icon: 'success' })
    uni.redirectTo({ url: `/pages/interview/report?practiceId=${practiceId.value}` })
  } catch(error: any) {
    uni.hideLoading()
    uni.showToast({ title: error.message || '生成失败，请重试', icon: 'error' })
  }
}
</script>

<style scoped>
.practice {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 88rpx);
  background: var(--color-bg);
}

/* Header */
.practice__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20rpx 32rpx;
  background: #3f1917;
  border-bottom: 1rpx solid rgba(231,201,129,.22);
}
.practice__header-left { display: flex; align-items: center; gap: 16rpx; }
.practice__header-avatar { width: 64rpx; height: 64rpx; border: 3rpx double #e7c981; border-radius: 50%; display: flex; align-items: center; justify-content: center; color:#e7c981; font:700 25rpx var(--font-display); }
.practice__header-name { font:700 27rpx var(--font-display); color: #fff8e9; }
.practice__header-title { font-size: 18rpx; color: rgba(255,248,233,.52); }
.practice__header-right { display: flex; align-items: center; gap: 20rpx; }
.practice__header-hint { font-size: 18rpx; color: #e7c981; padding: 8rpx 13rpx; border:1px solid rgba(231,201,129,.3); }
.practice__round { font-size: 15rpx; letter-spacing:1rpx; color: rgba(255,248,233,.45); }

/* Messages */
.practice__messages {
  flex: 1;
  overflow-y: auto;
  padding: 24rpx 0;
}
.practice__messages-inner { min-height: 100%; }
.practice__thinking { opacity: 0.7; }

/* End Button */
.practice__end-btn {
  margin: 16rpx 32rpx;
  padding: 24rpx;
  background: var(--color-primary);
  border: 1px solid var(--color-primary);
  border-radius: 2rpx;
  text-align: center;
  font-size: 26rpx;
  color: white;
  font-weight: 500;
}
.practice__end-btn--disabled { background: #E8E0D5 !important; color: #9B8E8E !important; border-color: #E8E0D5 !important; cursor: not-allowed; }

/* Phase bar */
.practice__phase { display: flex; align-items: center; gap: 12rpx; padding: 0 32rpx; margin-bottom: 8rpx; }
.practice__phase-bar { flex: 1; height: 6rpx; background: var(--color-border); border-radius: 3rpx; overflow: hidden; }
.practice__phase-fill { height: 100%; background: linear-gradient(90deg, #8B1A1A, #C41E1A); border-radius: 3rpx; transition: width 0.5s ease; }
.practice__phase-label { font-size: 20rpx; color: var(--color-text-muted); white-space: nowrap; }
</style>
