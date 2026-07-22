// @dcloudio/uni-app shim for H5 mode
// Provides lifecycle hooks compatible with Vue Router

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
export const onShow: LifecycleHook = (fn) => {}
export const onHide: LifecycleHook = (fn) => {}
export const onReady: LifecycleHook = (fn) => setTimeout(fn, 0)
export const onUnload: LifecycleHook = (fn) => {}
export const onUnmounted: LifecycleHook = (fn) => {}

// Provide a stub for uni-app page setup
export function definePageConfig() { return {} }
