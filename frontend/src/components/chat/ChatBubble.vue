<template>
  <div class="chat-bubble" :class="['chat-bubble--' + role]">
    <div v-if="role === 'ai'" class="chat-bubble__avatar">
      <img v-if="avatar" :src="avatar" class="chat-bubble__avatar-img" style="object-fit:cover;display:block;max-width:100%">
      <div v-else class="chat-bubble__avatar-placeholder">AI</div>
    </div>

    <div class="chat-bubble__content">
      <div v-if="role === 'ai' && name" class="chat-bubble__name">{{ name }}</div>
      <div class="chat-bubble__message" :class="{ 'chat-bubble__message--analyzing': isAnalyzing }">
        <div v-if="images?.length" class="chat-bubble__images">
          <img v-for="(image, index) in images" :key="index" :src="image" alt="已发送图片" />
        </div>
        <span class="chat-bubble__text">{{ content }}</span>
        <div v-if="isAnalyzing" class="chat-bubble__typing">
          <div class="chat-bubble__dot"></div>
          <div class="chat-bubble__dot"></div>
          <div class="chat-bubble__dot"></div>
        </div>
      </div>
      <div v-if="role === 'ai' && annotation" class="chat-bubble__annotation">
        <span class="chat-bubble__annotation-icon">💡</span>
        <span class="chat-bubble__annotation-text">{{ annotation }}</span>
      </div>
      <span class="chat-bubble__time">{{ time }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  role: 'ai' | 'user'
  content: string
  name?: string
  avatar?: string
  time?: string
  annotation?: string
  isAnalyzing?: boolean
  images?: string[]
}>(), {
  name: 'AI 助手',
  time: ''
})
</script>

<style scoped>
.chat-bubble {
  display: flex;
  margin-bottom: 32rpx;
  padding: 0 24rpx;
}
.chat-bubble--user {
  flex-direction: row-reverse;
}

/* Avatar */
.chat-bubble__avatar { width: 64rpx; height: 64rpx; flex-shrink: 0; margin-right: 20rpx; }
.chat-bubble--user .chat-bubble__avatar { margin-right: 0; margin-left: 20rpx; }
.chat-bubble__avatar-img { width: 64rpx; height: 64rpx; border-radius: 50%; }
.chat-bubble__avatar-placeholder {
  width: 64rpx; height: 64rpx; border-radius: 50%;
  background: linear-gradient(135deg, #8B1A1A, #5C0E0E);
  color: #FFFFFF; font-size: 22rpx; font-weight: 600;
  display: flex; align-items: center; justify-content: center;
}
.chat-bubble--user .chat-bubble__avatar-placeholder {
  background: linear-gradient(135deg, #6B5E5E, #4A3E3E);
}

/* Content */
.chat-bubble__content { max-width: 580rpx; }
.chat-bubble--user .chat-bubble__content { align-items: flex-end; }

.chat-bubble__name { font-size: 22rpx; color: var(--color-text-muted); margin-bottom: 8rpx; }
.chat-bubble--user .chat-bubble__name { text-align: right; }

.chat-bubble__message {
  padding: 24rpx 28rpx;
  border-radius: 4px;
  line-height: 1.6;
  position: relative;
}
.chat-bubble--ai .chat-bubble__message {
  background: #FFFFFF;
  box-shadow: 0 2rpx 8rpx rgba(0,0,0,0.06);
  transition: box-shadow 0.2s ease;
  border-top-left-radius: 4rpx;
}
.chat-bubble--user .chat-bubble__message {
  background: linear-gradient(135deg, #8B1A1A, #5C0E0E);
  color: #FFFFFF;
  border-top-right-radius: 4rpx;
}

.chat-bubble__text { font-size: 28rpx; word-break: break-word; white-space: pre-wrap; }
.chat-bubble--user .chat-bubble__text { color: #FFFFFF; }

/* Attached images sent with the user's message */
.chat-bubble__images { display: grid; gap: 8rpx; margin-bottom: 12rpx; }
.chat-bubble__images img { display: block; width: 100%; max-width: 320rpx; border-radius: 8rpx; object-fit: cover; }

/* Analysis state */
.chat-bubble__message--analyzing {
  background: rgba(139,26,26,0.06) !important;
  border: 1rpx solid #FFD7D0;
}

/* Typing animation */
.chat-bubble__typing { display: flex; align-items: center; gap: 8rpx; margin-top: 12rpx; }
.chat-bubble__dot {
  width: 12rpx; height: 12rpx; border-radius: 50%;
  background: #C41E1A; opacity: 0.5;
  animation: bounce 1.4s infinite ease-in-out;
}
.chat-bubble__dot:nth-child(1) { animation-delay: -0.32s; }
.chat-bubble__dot:nth-child(2) { animation-delay: -0.16s; }
.chat-bubble__dot:nth-child(3) { animation-delay: 0s; }
@keyframes bounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}

/* Annotation */
.chat-bubble__annotation {
  margin-top: 12rpx; padding: 16rpx 20rpx;
  background: var(--color-bg); border-radius: 4px;
  border-left: 4rpx solid #FFD700;
  display: flex; align-items: flex-start; gap: 8rpx;
}
.chat-bubble__annotation-icon { font-size: 24rpx; flex-shrink: 0; }
.chat-bubble__annotation-text { font-size: 24rpx; color: #8B6D00; line-height: 1.5; }

/* Time */
.chat-bubble__time { font-size: 20rpx; color: var(--color-text-muted); margin-top: 8rpx; display: block; }
.chat-bubble--user .chat-bubble__time { text-align: right; }
</style>
