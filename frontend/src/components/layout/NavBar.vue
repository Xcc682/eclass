<template>
  <div class="navbar" :class="{'navbar--root':root}" :style="{ paddingTop: statusBarHeight + 'px' }">
    <div class="navbar__inner">
      <div class="navbar__left" @click="goBack" v-if="showBack">
        <IconSet name="back" size="44rpx" color="#FFFFFF" />
      </div>
      <div class="navbar__left" v-else></div>
      <div class="navbar__brand"><span class="navbar__mark"></span><span class="navbar__title">{{ title }}</span></div>
      <div class="navbar__right"></div>
    </div>
  </div>
  <!-- 占位 -->
  <div class="navbar-placeholder"></div>
</template>

<script setup lang="ts">
import IconSet from '@/components/common/IconSet.vue'

withDefaults(defineProps<{
  title?: string
  showBack?: boolean
  statusBarHeight?: number
  root?: boolean
}>(), {
  title: '思政情景工坊',
  showBack: false,
  statusBarHeight: 0,
  root: false
})

function goBack() {
  uni.navigateBack()
}
</script>

<style scoped>
.navbar {
  position: fixed;
  top: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 100%;
  max-width: 480px;
  z-index: 1000;
  background: rgba(70, 22, 19, .97);
  box-shadow: 0 8rpx 28rpx rgba(55, 20, 16, .16);
  border-bottom: 1px solid rgba(181,138,63,.42);
  backdrop-filter: blur(16px);
}
.navbar__inner {
  width: 100%;
  max-width: var(--desktop-dashboard, 1180px);
  margin: 0 auto;
  box-sizing: border-box;
  height: 92rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 24rpx;
  position: relative;
}
.navbar__left {
  position: absolute;
  left: 16rpx;
  width: 60rpx;
  height: 60rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 1;
}
.navbar__back-icon {
  font-size: 44rpx;
  color: #FFFFFF;
  line-height: 1;
  font-weight: 300;
}
.navbar__title {
  font-family: var(--font-display);
  font-size: 29rpx;
  font-weight: 700;
  letter-spacing: 3rpx;
  color: #fff9ed;
}
.navbar__brand{display:flex;align-items:center;gap:13rpx}.navbar__mark{width:8rpx;height:8rpx;border:1rpx solid #d8b96f;transform:rotate(45deg);background:#a82d27}
.navbar__right {
  position: absolute;
  right: 16rpx;
  width: 60rpx;
  height: 60rpx;
}

.navbar-placeholder {
  height: 92rpx;
}
</style>
