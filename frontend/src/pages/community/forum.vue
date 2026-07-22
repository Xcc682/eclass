<template>
  <div class="forum">
    <span>正在进入学习圈...</span>
  </div>
</template>

<script setup lang="ts">
import { onLoad } from '@dcloudio/uni-app'

onLoad(() => uni.switchTab({ url: '/pages/community/community' }))
</script>

<style scoped>
.forum { min-height:100vh; display:flex; align-items:center; justify-content:center; color:var(--color-text-muted); }
</style>
