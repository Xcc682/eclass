<template>
  <div class="avatar" :style="{ width: size + 'rpx', height: size + 'rpx', borderRadius: round ? '50%' : radius + 'rpx' }">
    <img v-if="src" :src="src" class="avatar__img"
      :style="{ width: size + 'rpx', height: size + 'rpx', borderRadius: round ? '50%' : radius + 'rpx' }" />
    <div v-else class="avatar__placeholder" :style="{ fontSize: (size * 0.4) + 'rpx', borderRadius: round ? '50%' : radius + 'rpx' }">
      {{ name?.[0] || '?' }}
    </div>
    <div v-if="online" class="avatar__dot"></div>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  src?: string
  name?: string
  size?: number
  round?: boolean
  radius?: number
  online?: boolean
}>(), {
  size: 80,
  round: true,
  radius: 16
})
</script>

<style scoped>
.avatar {
  position: relative;
  flex-shrink: 0;
  overflow: hidden;
}
.avatar__img {
  width: 100%;
  height: 100%;
}
.avatar__placeholder {
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, #8B1A1A, #5C0E0E);
  color: #FFFFFF;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
}
.avatar__dot {
  position: absolute;
  bottom: 0;
  right: 0;
  width: 16rpx;
  height: 16rpx;
  background: var(--color-primary-light);
  border-radius: 50%;
  border: 2rpx solid #FFFFFF;
}
</style>
