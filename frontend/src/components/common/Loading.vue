<template>
  <div class="loading" :class="['loading--' + type]">
    <div v-if="type === 'spinner'" class="loading__spinner"></div>
    <div v-else class="loading__skeleton">
      <div class="loading__skeleton-line" v-for="i in lines" :key="i"
        :style="{ width: (100 - (i * 5 - 5)) + '%', height: lineHeight + 'rpx' }"></div>
    </div>
    <span v-if="text" class="loading__text">{{ text }}</span>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  type?: 'spinner' | 'skeleton'
  text?: string
  lines?: number
  lineHeight?: number
}>(), {
  type: 'spinner',
  lines: 3,
  lineHeight: 28
})
</script>

<style scoped>
.loading { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 60rpx; }
.loading--skeleton { align-items: flex-start; padding: 32rpx; }

.loading__spinner {
  width: 64rpx; height: 64rpx;
  border: 6rpx solid #F0F0F0;
  border-top-color: var(--color-primary-light);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.loading__text { margin-top: 24rpx; font-size: 26rpx; color: var(--color-text-muted); }

.loading__skeleton { width: 100%; }
.loading__skeleton-line {
  background: linear-gradient(90deg, #F0F0F0 25%, #E8E8E8 50%, #F0F0F0 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: 8rpx;
  margin-bottom: 16rpx;
}
@keyframes shimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
</style>
