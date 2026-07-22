<template>
  <svg :width="size" :height="size" viewBox="0 0 24 24" fill="none"
    :stroke="color" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"
    class="iconset" :class="'iconset--' + (animated ? 'animated' : 'static')">
    <!-- Navigation -->
    <template v-if="name === 'back'"><polyline points="15 18 9 12 15 6"/></template>
    <template v-else-if="name === 'arrow-right'"><polyline points="9 18 15 12 9 6"/></template>
    <template v-else-if="name === 'send'"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></template>
    <template v-else-if="name === 'voice'"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></template>
    <!-- TabBar -->
    <template v-else-if="name === 'home'"><path d="M3 12L12 3l9 9"/><path d="M5 10v10a1 1 0 001 1h3v-5h6v5h3a1 1 0 001-1V10"/></template>
    <template v-else-if="name === 'training'"><circle cx="12" cy="8" r="4"/><path d="M8 14v6l4-2 4 2v-6"/></template>
    <template v-else-if="name === 'community'"><circle cx="9" cy="7" r="3"/><path d="M3 20v-2a4 4 0 014-4h4a4 4 0 014 4v2"/><circle cx="17" cy="7" r="2"/><path d="M17 11a3 3 0 013 3v1h-3"/></template>
    <template v-else-if="name === 'knowledge'"><path d="M4 6h16M4 12h16M4 18h12"/><circle cx="8" cy="6" r="1" :fill="color" stroke="none"/><circle cx="8" cy="12" r="1" :fill="color" stroke="none"/><circle cx="8" cy="18" r="1" :fill="color" stroke="none"/></template>
    <template v-else-if="name === 'profile'"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/></template>
    <!-- Section Titles -->
    <template v-else-if="name === 'pin'"><line x1="12" y1="17" x2="12" y2="22"/><path d="M5 17h14v-2.3a1 1 0 0 0-.3-.7L16 11.3V4h3V2H5v2h3v7.3L5.3 14a1 1 0 0 0-.3.7V17z"/></template>
    <template v-else-if="name === 'chart'"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></template>
    <template v-else-if="name === 'target'"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></template>
    <template v-else-if="name === 'trophy'"><path d="M6 9H4.5a2.5 2.5 0 0 1 0-5C6 4 7 5 7 9"/><path d="M18 9h1.5a2.5 2.5 0 0 0 0-5C18 4 17 5 17 9"/><path d="M7 9h10v2a5 5 0 0 1-10 0V9z"/><path d="M12 16v5"/><path d="M8 21h8"/></template>
    <template v-else-if="name === 'calendar'"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></template>
    <template v-else-if="name === 'clipboard'"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/></template>
    <template v-else-if="name === 'bulb'"><path d="M9 18h6"/><path d="M10 22h4"/><path d="M15.09 14c.18-.98.65-1.74 1.41-2.5A4.65 4.65 0 0 0 18 8 6 6 0 0 0 6 8c0 1 .23 2.23 1.5 3.5A4.61 4.61 0 0 1 8.91 14"/></template>
    <template v-else-if="name === 'book'"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></template>
    <template v-else-if="name === 'key'"><path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/></template>
    <template v-else-if="name === 'chat'"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></template>
    <template v-else-if="name === 'fire'"><path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.07-2.14-.22-4.37 1-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 0 1-14 0c0-1.15.43-2.3 1-3.5"/></template>
    <template v-else-if="name === 'pen'"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></template>
    <!-- Status -->
    <template v-else-if="name === 'check'"><polyline points="20 6 9 17 4 12"/></template>
    <template v-else-if="name === 'warning'"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></template>
    <template v-else-if="name === 'info'"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></template>
    <template v-else-if="name === 'star'"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></template>
    <template v-else-if="name === 'empty'"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="M8 2v4M16 2v4M2 10h20"/></template>
    <!-- Quick Actions -->
    <template v-else-if="name === 'interview'"><circle cx="12" cy="10" r="3"/><path d="M12 2v4M12 14v4M7 4l4 4M17 4l-4 4M7 16l4-4M17 16l-4-4"/><circle cx="12" cy="20" r="2"/></template>
    <template v-else-if="name === 'history'"><path d="M3 3v5h5"/><path d="M3.05 13A9 9 0 1 0 6 6.3L3 8"/><path d="M12 7v5l4 2"/></template>
    <template v-else-if="name === 'tour'"><path d="M3 21h18"/><path d="M6 21v-7l-3-3 9-9 9 9-3 3v7"/><path d="M9 21v-5h6v5"/></template>
    <template v-else-if="name === 'debate'"><circle cx="12" cy="12" r="10"/><path d="M8 12h8M12 8v8"/></template>
    <template v-else-if="name === 'growth'"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></template>
    <template v-else-if="name === 'daily'"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/><polyline points="8 14 11 17 16 13"/></template>
    <template v-else-if="name === 'bell'"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></template>
    <template v-else-if="name === 'heart'"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></template>
    <template v-else-if="name === 'eye'"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></template>
    <template v-else-if="name === 'bolt'"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></template>
    <template v-else-if="name === 'sparkle'"><path d="M12 2l1.5 4.5L18 8l-4.5 1.5L12 14l-1.5-4.5L6 8l4.5-1.5z"/><path d="M2 20l.75 2.25L5 23l-2.25.75L2 26l-.75-2.25L-1 23l2.25-.75zM19 4l.5 1.5L21 6l-1.5.5L19 8l-.5-1.5L17 6l1.5-.5z"/></template>
    <!-- Logo -->
    <template v-else-if="name === 'logo'"><circle cx="12" cy="12" r="11"/><path d="M8 7h8v2l-3 3v5l-2-1v-4L8 9V7z"/></template>
  </svg>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  name: string
  size?: string
  color?: string
  animated?: boolean
}>(), {
  size: '24rpx',
  color: 'currentColor',
  animated: false
})
</script>

<style scoped>
.iconset { display: inline-block; vertical-align: middle; flex-shrink: 0; }
.iconset--animated { transition: transform 0.2s ease; }
</style>
