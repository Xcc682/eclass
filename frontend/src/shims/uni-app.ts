// @dcloudio/uni-app shim for H5 mode
// Provides lifecycle hooks compatible with Vue Router

import { onBeforeUnmount, onMounted, onUnmounted as vueOnUnmounted } from 'vue'

type LifecycleHook = (fn: (...args: any[]) => void) => void

function getRouteQuery(): Record<string, string> {
  const hash = window.location.hash
  const queryStart = hash.indexOf('?')
  if (queryStart === -1) return {}
  const qs = hash.slice(queryStart + 1)
  const query: Record<string, string> = {}
  qs.split('&').forEach(p => {
    const [k, v] = p.split('=')
    if (k) query[k] = decodeURIComponent(v || '')
  })
  return query
}

export const onLoad: LifecycleHook = (fn) => {
  const query = getRouteQuery()
  fn(query)
}

export const onLaunch: LifecycleHook = (fn) => fn()
// Vue Router mounts a fresh page component on navigation. Mapping onShow to
// onMounted keeps H5 aligned with uni-app pages without firing the hook during
// setup before refs and computed state are ready.
export const onShow: LifecycleHook = (fn) => onMounted(fn)
export const onHide: LifecycleHook = (fn) => onBeforeUnmount(fn)
export const onReady: LifecycleHook = (fn) => setTimeout(fn, 0)
export const onUnload: LifecycleHook = (fn) => onBeforeUnmount(fn)
export const onUnmounted: LifecycleHook = (fn) => vueOnUnmounted(fn)

// Provide a stub for uni-app page setup
export function definePageConfig() { return {} }
