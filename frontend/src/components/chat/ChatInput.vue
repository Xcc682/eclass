<template>
  <div class="chat-input input-bar">
    <button
      class="chat-input__attach"
      type="button"
      title="附上一张图片"
      :disabled="disabled || images.length >= 2"
      @click="pickImage"
    >
      ＋图
    </button>
    <div v-if="images.length" class="chat-input__chips">
      <figure v-for="(image, index) in images" :key="index" class="chat-input__chip">
        <img :src="image" alt="待发送图片" />
        <button type="button" title="移除图片" @click="images.splice(index, 1)">×</button>
      </figure>
    </div>
    <input
      class="chat-input__field"
      v-model="inputText"
      :placeholder="placeholder"
      :disabled="disabled"
      @keydown.enter.exact.prevent="handleSend"
    />
    <button
      class="chat-input__send"
      :class="{ 'chat-input__send--active': inputText.trim() }"
      :disabled="disabled || !inputText.trim()"
      @click="handleSend"
    >
      <IconSet name="send" size="28rpx" color="#FFFFFF" />
    </button>
    <input ref="fileEl" type="file" accept="image/png,image/jpeg,image/webp" hidden @change="onPickImages" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import IconSet from '@/components/common/IconSet.vue'

const props = withDefaults(defineProps<{
  placeholder?: string
  disabled?: boolean
  showVoice?: boolean
}>(), {
  placeholder: '输入你的回答...',
  showVoice: true
})

const emit = defineEmits<{ send: [text: string, images?: string[]]; voice: [] }>()
const inputText = ref('')
const images = ref<string[]>([])
const fileEl = ref<HTMLInputElement | null>(null)
const IMAGE_MAX_BYTES = 4 * 1024 * 1024

function pickImage() {
  fileEl.value?.click()
}

function onPickImages(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file || images.value.length >= 2) return
  if (!/^image\/(png|jpeg|webp)$/.test(file.type)) {
    uni.showToast({ title: '仅支持 PNG/JPEG/WebP 图片', icon: 'none' })
    return
  }
  if (file.size > IMAGE_MAX_BYTES) {
    uni.showToast({ title: '图片不得超过 4MB', icon: 'none' })
    return
  }
  const reader = new FileReader()
  reader.onload = () => {
    if (typeof reader.result === 'string') images.value.push(reader.result)
  }
  reader.readAsDataURL(file)
}

function handleSend() {
  const text = inputText.value.trim()
  if (!text || props.disabled) return
  emit('send', text, images.value.length ? images.value.slice() : undefined)
  inputText.value = ''
  images.value = []
}
</script>

<style scoped>
.chat-input {
  padding-bottom: calc(16rpx + env(safe-area-inset-bottom, 0rpx));
  flex-wrap: wrap;
}
.chat-input__field {
  height: 72rpx;
}
.chat-input__attach {
  flex: none;
  width: auto;
  min-width: 0;
  padding: 0 16rpx;
  height: 52rpx;
  line-height: 52rpx;
  font-size: 22rpx;
  color: #7d2924;
  background: #faf5ec;
  border: 1rpx solid #d6c9b7;
  border-radius: 8rpx;
}
.chat-input__attach:disabled {
  opacity: 0.4;
}
.chat-input__chips {
  flex: none;
  width: 100%;
  display: flex;
  gap: 12rpx;
  padding-bottom: 8rpx;
}
.chat-input__chip {
  position: relative;
  width: 96rpx;
  height: 96rpx;
  margin: 0;
  padding: 0;
  border: 1rpx solid #d8cbb8;
  background: #fff;
}
.chat-input__chip img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.chat-input__chip button {
  position: absolute;
  top: -10rpx;
  right: -10rpx;
  width: 32rpx;
  height: 32rpx;
  line-height: 30rpx;
  padding: 0;
  border-radius: 50%;
  background: #7d2924;
  color: #fff;
  font-size: 20rpx;
}
.chat-input__send {
  width: auto;
  min-width: 64rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6rpx;
}
.chat-input__send:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
</style>
