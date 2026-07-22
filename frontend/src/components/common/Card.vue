<template>
  <div
    class="card"
    :style="[cardStyle]"
    :class="{ 'card--pressed': isPressed }"
    @click="handleTap"
    @touchstart="onTouchStart"
    @touchend="onTouchEnd"
  >
    <div v-if="title" class="card__header">
      <span class="card__title">{{ title }}</span>
      <div v-if="$slots.headerRight" class="card__header-right">
        <slot name="headerRight"></slot>
      </div>
    </div>
    <div class="card__body">
      <slot />
    </div>
    <div v-if="$slots.footer" class="card__footer">
      <slot name="footer" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

const props = withDefaults(defineProps<{
  title?: string
  padding?: string
  shadow?: 'sm' | 'md' | 'lg'
  radius?: string
  onClick?: () => void
}>(), {
  shadow: 'sm'
})

const emit = defineEmits<{ click: [] }>()
const isPressed = ref(false)

const cardStyle = computed(() => ({
  padding: props.padding || '32rpx',
  borderRadius: props.radius || '24rpx',
  boxShadow: props.shadow === 'sm' ? '0 2rpx 8rpx rgba(0,0,0,0.06)' :
             props.shadow === 'md' ? '0 4rpx 16rpx rgba(0,0,0,0.08)' :
             '0 8rpx 32rpx rgba(0,0,0,0.12)'
}))

function handleTap() {
  if (props.onClick) props.onClick()
  else emit('click')
}

function onTouchStart() { isPressed.value = true }
function onTouchEnd() { isPressed.value = false }
</script>

<style scoped>
.card {
  background: var(--color-paper);
  border: 1rpx solid var(--color-border);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-card);
  transition: transform 0.2s, box-shadow 0.2s;
  overflow: hidden;
}
.card--pressed {
  transform: scale(0.98);
  box-shadow: 0 1rpx 4rpx rgba(0,0,0,0.04);
  transition: box-shadow 0.2s ease;
}
.card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24rpx;
}
.card__title {
  font-family: var(--font-display);
  font-size: 30rpx;
  font-weight: 600;
  color: var(--color-text);
}
.card__header-right {
  flex-shrink: 0;
}
.card__footer {
  margin-top: 24rpx;
  padding-top: 24rpx;
  border-top: 1rpx solid var(--color-border);
}
</style>
