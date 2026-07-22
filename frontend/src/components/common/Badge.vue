<template>
  <div class="badge" :class="['badge--' + type, 'badge--' + size]">
    <span class="badge__text">{{ text }}</span>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  text: string
  type?: 'default' | 'primary' | 'success' | 'warning' | 'error'
  size?: 'sm' | 'md' | 'lg'
}>(), {
  type: 'default',
  size: 'sm'
})
</script>

<style scoped>
.badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border:1rpx solid transparent;
  border-radius: 999rpx;
  font-weight: 500;
}
.badge--sm { padding: 4rpx 14rpx; font-size: 20rpx; }
.badge--md { padding: 6rpx 18rpx; font-size: 22rpx; }
.badge--lg { padding: 8rpx 24rpx; font-size: 24rpx; }
.badge--default { border-color:#ddd2c3;background:#f7f2e9;color:var(--color-text-secondary); }
.badge--primary { border-color:#dfbcb8;background:#f8e9e6;color:var(--color-primary); }
.badge--success { border-color:#bed3c8;background:#eaf2ed;color:var(--color-green); }
.badge--warning { border-color:#e3cfac;background:#faf1df;color:#94601f; }
.badge--error { border-color:#dfbcb8;background:#f9e8e5;color:#96362f; }
</style>
