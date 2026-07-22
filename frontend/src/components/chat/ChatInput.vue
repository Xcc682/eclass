<template>
  <div class="chat-input input-bar">
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

const emit = defineEmits<{ send: [text: string]; voice: [] }>()
const inputText = ref('')

function handleSend() {
  const text = inputText.value.trim()
  if (!text || props.disabled) return
  emit('send', text)
  inputText.value = ''
}
</script>

<style scoped>
.chat-input {
  padding-bottom: calc(16rpx + env(safe-area-inset-bottom, 0rpx));
}
.chat-input__field {
  height: 72rpx;
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
