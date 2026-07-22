<template>
  <div class="tabbar">
    <div v-for="tab in tabs" :key="tab.path" class="tabbar__item" @click="switchTab(tab)">
      <div class="tabbar__icon-wrap" :class="{ 'tabbar__icon-wrap--active': tab.active }">
        <IconSet :name="tab.icon" size="44rpx" :color="tab.active ? 'var(--color-primary-light)' : 'var(--color-text-muted)'" />
      </div>
      <span class="tabbar__label" :class="{ 'tabbar__label--active': tab.active }">{{ tab.label }}</span>
    </div>
  </div>
  <div class="tabbar-placeholder"></div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import IconSet from '@/components/common/IconSet.vue'

const router = useRouter()
const route = useRoute()

const tabs = computed(() => {
  const current = route.path
  return [
    { path: '/pages/index/index', label: '首页', icon: 'home', active: current === '/pages/index/index' },
    { path: '/pages/interview/interview', label: '情景实训', icon: 'training', active: current.startsWith('/pages/interview') },
    { path: '/pages/community/community', label: '成长社区', icon: 'community', active: current === '/pages/community/community' },
    { path: '/pages/knowledge/knowledge', label: '知识库', icon: 'knowledge', active: current.startsWith('/pages/knowledge') },
    { path: '/pages/community/profile', label: '我的', icon: 'profile', active: current === '/pages/community/profile' },
  ]
})

function switchTab(tab: any) { router.replace(tab.path) }
</script>

<style scoped>
.tabbar {
  display: flex;
  position: fixed;
  bottom: 12rpx;
  left: 50%;
  transform: translateX(-50%);
  width: calc(100% - 24rpx);
  max-width: 456px;
  z-index: 1000;
  overflow:hidden;
  border: 1rpx solid rgba(109,85,60,.16);
  border-radius: 22rpx;
  background: rgba(255,253,247,.96);
  backdrop-filter: blur(18px);
  box-shadow: 0 14rpx 40rpx rgba(54,38,24,.14);
  padding: 5rpx 7rpx calc(5rpx + env(safe-area-inset-bottom, 0px));
}
.tabbar__item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-width:0;
  padding: 7rpx 0 5rpx;
  border-radius:16rpx;
  cursor: pointer;
  transition: transform 0.15s ease;
}
.tabbar__item:active { transform: scale(0.96); background:#f3ece1; }
.tabbar__icon-wrap {
  width: 48rpx;
  height: 48rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 1rpx;
  transition: transform 0.2s ease;
}
.tabbar__icon-wrap--active { transform: translateY(-1rpx); }
.tabbar__icon-wrap svg { width: 44rpx; height: 44rpx; }
.tabbar__label { max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size: 18rpx; color: #92877b; font-weight: 500; transition: color 0.2s ease; }
.tabbar__label--active { color: var(--color-primary); font-weight: 700; }

.tabbar-placeholder {
  height: var(--tabbar-space);
  padding-bottom: env(safe-area-inset-bottom, 0px);
}
</style>
