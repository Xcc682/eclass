<template>
  <!-- Home icon -->
  <svg v-if="name === 'home'" viewBox="0 0 24 24" fill="none" :stroke="stroke" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
    <path d="M3 12L12 3l9 9"/>
    <path d="M5 10v10a1 1 0 001 1h3v-5h6v5h3a1 1 0 001-1V10"/>
  </svg>
  <!-- Training icon -->
  <svg v-else-if="name === 'training'" viewBox="0 0 24 24" fill="none" :stroke="stroke" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="12" cy="8" r="4"/>
    <path d="M8 14v6l4-2 4 2v-6"/>
  </svg>
  <!-- Community icon -->
  <svg v-else-if="name === 'community'" viewBox="0 0 24 24" fill="none" :stroke="stroke" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="9" cy="7" r="3"/>
    <path d="M3 20v-2a4 4 0 014-4h4a4 4 0 014 4v2"/>
    <circle cx="17" cy="7" r="2"/>
    <path d="M17 11a3 3 0 013 3v1h-3"/>
  </svg>
  <!-- Knowledge icon -->
  <svg v-else-if="name === 'knowledge'" viewBox="0 0 24 24" fill="none" :stroke="stroke" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
    <path d="M4 6h16M4 12h16M4 18h12"/>
    <circle cx="8" cy="6" r="1" fill="currentColor" stroke="none"/>
    <circle cx="8" cy="12" r="1" fill="currentColor" stroke="none"/>
    <circle cx="8" cy="18" r="1" fill="currentColor" stroke="none"/>
  </svg>
  <!-- Profile icon -->
  <svg v-else viewBox="0 0 24 24" fill="none" :stroke="stroke" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="12" cy="8" r="4"/>
    <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/>
  </svg>
</template>

<script setup lang="ts">
defineProps<{ name: string; stroke?: string }>()
</script>
