<template>
  <div class="empty-state">
    <img v-if="image" :src="image" class="empty-state__image" style="object-fit:contain;display:block;max-width:100%">
    <div v-else class="empty-state__icon"><span>暂无</span></div>
    <span class="empty-state__title">{{ title }}</span>
    <span v-if="description" class="empty-state__desc">{{ description }}</span>
    <div v-if="actionText && actionText !== ''" class="empty-state__action" @click="handleAction">
      <span class="empty-state__action-text">{{ actionText }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
const emit = defineEmits<{ action: [] }>()
defineProps<{
  image?: string
  title?: string
  description?: string
  actionText?: string
}>()
function handleAction() { emit('action') }
</script>

<style scoped>
.empty-state { display:flex;flex-direction:column;align-items:center;justify-content:center;padding:100rpx 40rpx; }
.empty-state__icon {display:grid;place-items:center;width:112rpx;height:112rpx;margin-bottom:24rpx;border:1rpx solid #cdbda7;border-radius:50%;background:#f7f0e6;color:#9a8770;position:relative}.empty-state__icon:before,.empty-state__icon:after{content:'';position:absolute;background:#cdbda7}.empty-state__icon:before{width:140rpx;height:1rpx}.empty-state__icon:after{width:1rpx;height:140rpx}.empty-state__icon span{position:relative;z-index:1;padding:8rpx;background:#f7f0e6;font-family:var(--font-display);font-size:20rpx}
.empty-state__image { width: 240rpx; height: 240rpx; margin-bottom: 24rpx; }
.empty-state__title { font-family:var(--font-display);font-size:30rpx;font-weight:700;color:var(--color-text);margin-bottom:12rpx; }
.empty-state__desc { font-size:23rpx;color:var(--color-text-muted);text-align:center;line-height:1.7; }
.empty-state__action { margin-top:28rpx;padding:16rpx 34rpx;border:1rpx solid var(--color-primary);background:var(--color-primary);border-radius:999rpx; }
.empty-state__action-text { color:#fff;font-size:23rpx;font-weight:600; }
</style>
