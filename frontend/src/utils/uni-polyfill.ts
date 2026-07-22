// ===== uni-app API 兼容层 (H5 模式) =====
let _router: any = null

export function injectRouter(router: any) { _router = router }

// Storage
const getStorageSync = (key: string) => localStorage.getItem(key) || ''
const setStorageSync = (key: string, value: string) => localStorage.setItem(key, value)
const removeStorageSync = (key: string) => localStorage.removeItem(key)

// Navigation
const navigateTo = (opts: { url: string }) => {
  if (!_router) return
  const [path, qs] = opts.url.split('?')
  const query: Record<string, string> = {}
  if (qs) qs.split('&').forEach(p => { const [k, v] = p.split('='); if (k) query[k] = decodeURIComponent(v || '') })
  _router.push({ path, query })
}
const switchTab = (opts: { url: string }) => { if (_router) _router.push({ path: opts.url.split('?')[0] }) }
const navigateBack = () => { if (_router) _router.back() }
const reLaunch = (opts: { url: string }) => { if (_router) { const [path, qs] = opts.url.split('?'); const query: Record<string,string> = {}; if (qs) qs.split('&').forEach(p => { const [k,v] = p.split('='); if (k) query[k] = decodeURIComponent(v||'') }); _router.replace({ path, query }) } }
const redirectTo = (opts: { url: string }) => { if (_router) { const [path, qs] = opts.url.split('?'); const query: Record<string,string> = {}; if (qs) qs.split('&').forEach(p => { const [k,v] = p.split('='); if (k) query[k] = decodeURIComponent(v||'') }); _router.replace({ path, query }) } }

// Toast / Loading
const showToast = (opts: { title: string; icon?: string; duration?: number }) => {
  const type = opts.icon || 'none'
  const colors: Record<string, { bg: string; icon: string }> = {
    success: { bg: '#2E7D32', icon: '✓' },
    error:   { bg: '#D32F2F', icon: '✕' },
    warning: { bg: '#F57C00', icon: '!' },
    loading: { bg: '#1976D2', icon: '◌' },
    none:    { bg: 'rgba(0,0,0,0.8)', icon: '' },
  }
  const c = colors[type] || colors.none
  const el = document.createElement('div')
  el.innerHTML = `<div style="display:flex;align-items:center;gap:10px"><span style="font-weight:700;font-size:18px">${c.icon}</span><span>${opts.title}</span></div>`
  el.style.cssText = `position:fixed;top:48px;left:50%;transform:translateX(-50%);background:${c.bg};color:#fff;padding:12px 24px;border-radius:8px;font-size:14px;z-index:99999;box-shadow:0 4px 12px rgba(0,0,0,0.2);transition:all 0.3s ease;opacity:0;`
  document.body.appendChild(el)
  requestAnimationFrame(() => { el.style.opacity = '1' })
  // Each toast manages its own timer — no singleton that gets cleared by subsequent toasts
  const timer = setTimeout(() => {
    el.style.opacity = '0'
    setTimeout(() => el.remove(), 300)
  }, opts.duration || 2000)
  ;(el as any).__toastTimer = timer
}
const showLoading = (opts: { title: string }) => {
  const el = document.createElement('div')
  el.className = 'uni-loading-overlay'
  el.innerHTML = `<div style="display:flex;flex-direction:column;align-items:center;gap:12px;color:white"><div class="uni-loading-spinner"></div><span>${opts.title}</span></div>`
  el.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.3);display:flex;align-items:center;justify-content:center;z-index:99999;'
  const ss = document.createElement('style')
  ss.textContent = '.uni-loading-spinner{width:48px;height:48px;border:4px solid rgba(255,255,255,.3);border-top-color:#C41E1A;border-radius:50%;animation:uni-spin 0.8s linear infinite}@keyframes uni-spin{to{transform:rotate(360deg)}}'
  el.appendChild(ss)
  document.body.appendChild(el)
}
const hideLoading = () => { document.querySelectorAll('.uni-loading-overlay').forEach(el => el.remove()) }

// Modal
const showModal = (opts: { title?: string; content: string; showCancel?: boolean; success?: (result: { confirm: boolean; cancel: boolean }) => void }) => {
  const confirmed = confirm(`${opts.title || '提示'}\n\n${opts.content}`)
  const result = { confirm: confirmed, cancel: !confirmed }
  opts.success?.(result)
  return Promise.resolve(result)
}

// Request
const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1'
const request = (opts: { url: string; method?: string; data?: any; header?: Record<string, string>; timeout?: number }) => {
  const method = (opts.method || 'GET').toUpperCase()
  let url = opts.url.startsWith('http') || opts.url.startsWith('/api/') ? opts.url : API_BASE + opts.url
  if (method === 'GET' && opts.data && Object.keys(opts.data).length) {
    const query = new URLSearchParams()
    Object.entries(opts.data).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') query.set(key, String(value))
    })
    url += `${url.includes('?') ? '&' : '?'}${query.toString()}`
  }
  const headers: Record<string, string> = { 'Content-Type': 'application/json', ...(opts.header || {}) }
  const token = localStorage.getItem('token')
  if (token) headers['Authorization'] = `Bearer ${token}`
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), opts.timeout || 30000)
  return fetch(url, {
    method,
    headers,
    body: opts.data && method !== 'GET' ? JSON.stringify(opts.data) : undefined,
    signal: controller.signal,
  }).then(async res => ({ data: await res.json(), statusCode: res.status })).finally(() => clearTimeout(timeout))
}

const chooseFile = (opts: any = {}) => {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = opts.extension?.map((item: string) => `.${item}`).join(',') || '.pdf,.docx,.txt,.md'
  input.onchange = () => {
    const files = Array.from(input.files || []).slice(0, opts.count || 1)
    const result = {
      tempFiles: files.map(file => ({ name: file.name, size: file.size, path: file.name, file })),
      tempFilePaths: files.map(file => file.name),
    }
    opts.success?.(result)
    opts.complete?.(result)
  }
  input.click()
}

const uploadFile = (opts: any) => {
  const form = new FormData()
  const selected = opts.file instanceof File ? opts.file : null
  if (!selected) { opts.fail?.({ errMsg: '请选择文件' }); return }
  form.append(opts.name || 'file', selected, selected.name)
  Object.entries(opts.formData || {}).forEach(([key, value]) => form.append(key, String(value)))
  const headers: Record<string, string> = { ...(opts.header || {}) }
  const token = localStorage.getItem('token')
  if (token && !headers.Authorization) headers.Authorization = `Bearer ${token}`
  fetch(opts.url, { method: 'POST', headers, body: form }).then(async response => {
    const result = { data: await response.text(), statusCode: response.status }
    opts.success?.(result)
    opts.complete?.(result)
  }).catch(error => { opts.fail?.({ errMsg: error.message }); opts.complete?.(error) })
}

const downloadFile = (opts: any) => {
  const headers: Record<string, string> = { ...(opts.header || {}) }
  const token = localStorage.getItem('token')
  if (token && !headers.Authorization) headers.Authorization = `Bearer ${token}`
  fetch(opts.url, { headers }).then(async response => {
    if (!response.ok) throw new Error('下载失败')
    const tempFilePath = URL.createObjectURL(await response.blob())
    const result = { tempFilePath, statusCode: response.status }
    opts.success?.(result); opts.complete?.(result)
  }).catch(error => { opts.fail?.({ errMsg: error.message }); opts.complete?.(error) })
}

const openDocument = (opts: any) => {
  const anchor = document.createElement('a')
  anchor.href = opts.filePath
  anchor.download = opts.fileName || '资料文件'
  anchor.click()
  setTimeout(() => URL.revokeObjectURL(opts.filePath), 1000)
  opts.success?.()
}

const setClipboardData = (opts: any) => navigator.clipboard.writeText(opts.data || '').then(() => opts.success?.()).catch(error => opts.fail?.(error))

// Selector
const createSelectorQuery = () => ({
  selectViewport() { return this },
  select(s: string) {
    return {
      boundingClientRect(cb: Function) {
        const el = document.querySelector(s)
        if (el && cb) { const r = el.getBoundingClientRect(); cb({ width: r.width, height: r.height, top: r.top, left: r.left, right: r.right, bottom: r.bottom }) }
        return this
      },
      fields(_f: any, _cb?: any) { return this },
      scrollOffset(_cb: any) { return this },
      exec() { return [] }
    }
  },
  exec() { return [] }
})

// Canvas
const createCanvasContext = (canvasId: string) => {
  const canvas = document.querySelector(`canvas[canvas-id="${canvasId}"], #${canvasId}, [data-canvas-id="${canvasId}"]`) as HTMLCanvasElement | null
  const ctx = canvas?.getContext('2d')
  if (!ctx) {
    return new Proxy({} as any, { get: () => () => {} })
  }
  return {
    clearRect(x: number, y: number, w: number, h: number) { ctx.clearRect(x, y, w, h) },
    beginPath() { ctx.beginPath() },
    moveTo(x: number, y: number) { ctx.moveTo(x, y) },
    lineTo(x: number, y: number) { ctx.lineTo(x, y) },
    closePath() { ctx.closePath() },
    fill() { ctx.fill() },
    stroke() { ctx.stroke() },
    arc(x: number, y: number, r: number, s: number, e: number, ccw?: boolean) { ctx.arc(x, y, r, s, e, ccw) },
    setStrokeStyle(s: string) { ctx.strokeStyle = s },
    setFillStyle(s: string) { ctx.fillStyle = s },
    setLineWidth(w: number) { ctx.lineWidth = w },
    setFontSize(s: number) { ctx.font = `${s}px sans-serif` },
    setTextAlign(a: string) { ctx.textAlign = a as CanvasTextAlign },
    setTextBaseline(b: string) { ctx.textBaseline = b as CanvasTextBaseline },
    fillText(text: string, x: number, y: number) { ctx.fillText(text, x, y) },
    measureText(text: string) { return ctx.measureText(text) },
    arcTo() {},
    bezierCurveTo() {},
    quadraticCurveTo() {},
    rect() {},
    scale() {},
    rotate() {},
    translate() {},
    save() { ctx.save() },
    restore() { ctx.restore() },
    draw(reserve?: boolean, cb?: Function) { if (cb) cb(); },
  }
}

const getSystemInfoSync = () => ({
  windowWidth: window.innerWidth, windowHeight: window.innerHeight, pixelRatio: 1, platform: 'h5'
})

// ===== 挂载到 window =====
export function createUniPolyfill(router: any) {
  injectRouter(router)
  ;(window as any).uni = {
    getStorageSync, setStorageSync, removeStorageSync,
    navigateTo, switchTab, navigateBack, reLaunch, redirectTo,
    showToast, showLoading, hideLoading, showModal,
    request, chooseFile, uploadFile, downloadFile, openDocument, setClipboardData, createSelectorQuery, getSystemInfoSync,
    createCanvasContext,
    setNavigationBarTitle() {},
    setNavigationBarColor() {},
    onKeyboardHeightChange() {},
    getMenuButtonBoundingClientRect() { return { width: 48, height: 32, top: 8, right: 16, left: 16 } },
  }
}
