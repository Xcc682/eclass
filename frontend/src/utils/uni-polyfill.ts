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

// ===== Modal / ActionSheet / Preview / Scroll (overlay-based) =====
const _overlays: HTMLElement[] = []
function _createOverlay(): HTMLElement {
  const el = document.createElement('div')
  el.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;z-index:99998;display:flex;align-items:center;justify-content:center;background:rgba(18,14,10,.48);animation:uni-overlay-in .16s ease;'
  document.body.appendChild(el)
  _overlays.push(el)
  return el
}
function _removeOverlay(el: HTMLElement) {
  const index = _overlays.indexOf(el)
  if (index >= 0) _overlays.splice(index, 1)
  el.remove()
}
function _overlayButton(label: string, primary: boolean, onClick: () => void): HTMLButtonElement {
  const btn = document.createElement('button')
  btn.textContent = label
  btn.style.cssText = `flex:none;min-width:92px;padding:10px 18px;border:0;border-radius:8px;font-size:14px;line-height:1.4;cursor:pointer;transition:opacity .15s;${primary ? 'background:#C41E1A;color:#fff;' : 'background:#efe9de;color:#4a443e;'}`
  btn.addEventListener('click', onClick)
  return btn
}
if (!document.getElementById('uni-polyfill-styles')) {
  const style = document.createElement('style')
  style.id = 'uni-polyfill-styles'
  style.textContent = '@keyframes uni-overlay-in{from{opacity:0}to{opacity:1}}'
  document.head.appendChild(style)
}

// Modal — custom overlay that supports editable input and custom button labels.
const showModal = (opts: { title?: string; content?: string; showCancel?: boolean; editable?: boolean; placeholderText?: string; confirmText?: string; cancelText?: string; success?: (result: { confirm: boolean; cancel: boolean; content: string }) => void; fail?: (err: { errMsg: string }) => void }) => {
  const title = opts.title || '提示'
  const content = typeof opts.content === 'string' ? opts.content : ''
  const editable = Boolean(opts.editable)
  const showCancel = opts.showCancel !== false
  const confirmText = opts.confirmText || '确定'
  const cancelText = opts.cancelText || '取消'
  return new Promise<{ confirm: boolean; cancel: boolean; content: string }>((resolve) => {
    const overlay = _createOverlay()
    const panel = document.createElement('div')
    panel.style.cssText = 'width:min(360px,86vw);max-height:78vh;overflow:auto;box-sizing:border-box;padding:22px 20px 16px;border-radius:12px;background:#fffdf7;box-shadow:0 20px 64px rgba(0,0,0,.32);'
    panel.addEventListener('click', (event) => event.stopPropagation())
    const titleEl = document.createElement('div')
    titleEl.textContent = title
    titleEl.style.cssText = 'font:700 17px/1.4 var(--font-display,serif);margin-bottom:12px;color:#28231e;'
    panel.appendChild(titleEl)
    let inputEl: HTMLInputElement | null = null
    if (editable) {
      inputEl = document.createElement('input')
      inputEl.value = content
      inputEl.placeholder = opts.placeholderText || ''
      inputEl.style.cssText = 'width:100%;box-sizing:border-box;padding:10px 12px;border:1px solid #ddd2c4;border-radius:8px;font-size:14px;outline:none;background:#f8f4eb;'
      panel.appendChild(inputEl)
    } else if (content) {
      const bodyEl = document.createElement('div')
      bodyEl.textContent = content
      bodyEl.style.cssText = 'margin-bottom:14px;color:#5c544b;font-size:14px;line-height:1.6;white-space:pre-wrap;'
      panel.appendChild(bodyEl)
    }
    const actions = document.createElement('div')
    actions.style.cssText = 'display:flex;gap:10px;margin-top:16px;justify-content:flex-end;'
    const done = (confirm: boolean) => {
      const result = { confirm, cancel: !confirm, content: inputEl ? inputEl.value : content }
      _removeOverlay(overlay)
      opts.success?.(result)
      resolve(result)
    }
    if (showCancel) actions.appendChild(_overlayButton(cancelText, false, () => done(false)))
    actions.appendChild(_overlayButton(confirmText, true, () => done(true)))
    panel.appendChild(actions)
    overlay.appendChild(panel)
    if (inputEl) setTimeout(() => inputEl?.focus(), 20)
  })
}

// ActionSheet — vertical item list, resolves with tapIndex.
const showActionSheet = (opts: { itemList: string[]; itemColor?: string; title?: string; alertText?: string; cancelText?: string; success?: (result: { tapIndex: number; tapText: string; cancel: boolean }) => void; fail?: (err: { errMsg: string }) => void; complete?: (result: any) => void }) => {
  const itemList = Array.isArray(opts.itemList) ? opts.itemList : []
  const itemColor = opts.itemColor || '#28231e'
  return new Promise<{ tapIndex: number; tapText: string; cancel: boolean }>((resolve) => {
    const overlay = _createOverlay()
    const panel = document.createElement('div')
    panel.style.cssText = 'width:min(340px,84vw);overflow:hidden;border-radius:12px;background:#fffdf7;box-shadow:0 20px 64px rgba(0,0,0,.32);'
    panel.addEventListener('click', (event) => event.stopPropagation())
    const headerText = opts.alertText || opts.title || ''
    if (headerText) {
      const header = document.createElement('div')
      header.textContent = headerText
      header.style.cssText = 'padding:15px 18px 8px;color:#8a7f70;font-size:12px;text-align:center;'
      panel.appendChild(header)
    }
    const finish = (result: { tapIndex: number; tapText: string; cancel: boolean }, cancelled: boolean) => {
      _removeOverlay(overlay)
      if (cancelled) opts.fail?.({ errMsg: 'showActionSheet:fail cancel' })
      else opts.success?.(result)
      opts.complete?.(result)
      resolve(result)
    }
    itemList.forEach((label, index) => {
      const item = document.createElement('button')
      item.textContent = label
      item.style.cssText = `display:block;width:100%;box-sizing:border-box;padding:15px;border:0;border-top:1px solid #eee6da;background:#fffdf7;color:${itemColor};font-size:15px;cursor:pointer;text-align:center;`
      item.addEventListener('click', () => finish({ tapIndex: index, tapText: label, cancel: false }, false))
      panel.appendChild(item)
    })
    const cancel = document.createElement('button')
    cancel.textContent = opts.cancelText || '取消'
    cancel.style.cssText = 'display:block;width:100%;box-sizing:border-box;padding:15px;border:0;border-top:8px solid #f0ebe2;background:#fffdf7;color:#6b6155;font-size:15px;cursor:pointer;text-align:center;'
    cancel.addEventListener('click', () => finish({ tapIndex: -1, tapText: '', cancel: true }, true))
    panel.appendChild(cancel)
    overlay.appendChild(panel)
  })
}

// PreviewImage — full-screen image viewer with swipe-free prev/next buttons.
const previewImage = (opts: { urls?: string[]; current?: string; success?: () => void; fail?: (err: { errMsg: string }) => void }) => {
  const urls = (Array.isArray(opts.urls) && opts.urls.length ? opts.urls : opts.current ? [opts.current] : []).filter(Boolean)
  if (!urls.length) { opts.fail?.({ errMsg: 'previewImage:fail 无图片可预览' }); return Promise.resolve({}) }
  let current = urls.indexOf(opts.current || '')
  if (current < 0) current = 0
  return new Promise((resolve) => {
    const overlay = _createOverlay()
    overlay.style.background = 'rgba(0,0,0,.92)'
    overlay.style.cursor = 'zoom-out'
    const img = document.createElement('img')
    img.style.cssText = 'max-width:94vw;max-height:84vh;border-radius:4px;object-fit:contain;transition:opacity .16s;user-select:none;'
    const counter = document.createElement('div')
    counter.style.cssText = 'position:absolute;top:18px;left:0;right:0;text-align:center;color:rgba(255,255,255,.75);font-size:13px;'
    const show = (index: number) => {
      img.src = urls[index]
      img.style.opacity = '0'
      counter.textContent = urls.length > 1 ? `${index + 1} / ${urls.length}` : ''
      requestAnimationFrame(() => { img.style.opacity = '1' })
    }
    const close = () => { document.removeEventListener('keydown', onKey); _removeOverlay(overlay); opts.success?.(); resolve({}) }
    const step = (delta: number) => { if (urls.length > 1) { current = (current + delta + urls.length) % urls.length; show(current) } }
    function onKey(e: KeyboardEvent) { if (e.key === 'Escape') close(); if (e.key === 'ArrowLeft') step(-1); if (e.key === 'ArrowRight') step(1) }
    const prevBtn = document.createElement('button')
    const nextBtn = document.createElement('button')
    ;[prevBtn, nextBtn].forEach((btn, index) => {
      btn.textContent = index === 0 ? '‹' : '›'
      btn.style.cssText = `position:absolute;top:50%;transform:translateY(-50%);${index === 0 ? 'left:14px' : 'right:14px'};width:46px;height:46px;border:1px solid rgba(255,255,255,.35);border-radius:50%;background:rgba(0,0,0,.42);color:#fff;font-size:26px;line-height:1;cursor:pointer;`
      btn.addEventListener('click', (e) => { e.stopPropagation(); step(index === 0 ? -1 : 1) })
    })
    overlay.addEventListener('click', close)
    img.addEventListener('click', (e) => e.stopPropagation())
    overlay.appendChild(img)
    overlay.appendChild(counter)
    if (urls.length > 1) { overlay.appendChild(prevBtn); overlay.appendChild(nextBtn) }
    document.addEventListener('keydown', onKey)
    show(current)
  })
}

// PageScrollTo — scroll the target selector (or a numeric scrollTop) into view.
const pageScrollTo = (opts: { selector?: string; scrollTop?: number; duration?: number; success?: () => void; fail?: (err: { errMsg: string }) => void }) => {
  const behavior: ScrollBehavior = opts.duration ? 'smooth' : 'auto'
  if (opts.selector) {
    const el = document.querySelector(opts.selector) as HTMLElement | null
    if (el) el.scrollIntoView({ behavior, block: 'start' })
    else opts.fail?.({ errMsg: 'pageScrollTo:fail 未找到目标元素' })
  } else if (typeof opts.scrollTop === 'number') {
    window.scrollTo({ top: opts.scrollTop, behavior })
  }
  opts.success?.()
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
  // Accept both a real File and the chooseFile() wrapper {name,size,path,file}.
  const selected =
    opts.file instanceof File ? opts.file :
    opts.file && opts.file.file instanceof File ? opts.file.file :
    null
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

const setClipboardData = (opts: any) => {
  const data = opts.data || ''
  const done = () => { opts.success?.(); return Promise.resolve({}) }
  const failed = (error: any) => { opts.fail?.({ errMsg: String((error && error.message) || error || '复制失败') }); return Promise.resolve({}) }
  // navigator.clipboard 仅在安全上下文（HTTPS / localhost）可用
  if (navigator.clipboard && window.isSecureContext) {
    try {
      return navigator.clipboard.writeText(data).then(done).catch((error) => failed(error))
    } catch (error) {
      return failed(error)
    }
  }
  // 非安全上下文（如 http 内网穿透）fallback：隐藏 textarea + execCommand
  try {
    const textarea = document.createElement('textarea')
    textarea.value = data
    textarea.style.position = 'fixed'
    textarea.style.top = '0'
    textarea.style.opacity = '0'
    document.body.appendChild(textarea)
    textarea.focus()
    textarea.select()
    const ok = document.execCommand('copy')
    textarea.remove()
    return ok ? done() : failed(new Error('execCommand copy 失败'))
  } catch (error) {
    return failed(error)
  }
}

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

// InnerAudioContext — minimal HTMLAudioElement wrapper for H5.
const createInnerAudioContext = () => {
  let audio: HTMLAudioElement | null = new Audio()
  const handlers: Record<string, ((event: Event) => void)[]> = {}
  const bind = (name: string, fn: ((event: Event) => void) | undefined) => {
    if (!fn || !audio) return
    if (handlers[name]) { handlers[name]!.forEach((item) => audio?.removeEventListener(name, item)); handlers[name] = [] }
    handlers[name] = [fn]
    audio.addEventListener(name, fn)
  }
  const api: any = {
    _audio: audio,
    get src() { return audio?.src || '' },
    set src(value: string) { if (audio) audio.src = value },
    get loop() { return audio?.loop || false },
    set loop(value: boolean) { if (audio) audio.loop = value },
    set autoplay(value: boolean) { if (audio) audio.autoplay = value },
    get paused() { return audio?.paused ?? true },
    set volume(value: number) { if (audio) audio.volume = value },
    play() { audio?.play().catch(() => {}) },
    pause() { audio?.pause() },
    stop() { if (audio) { audio.pause(); audio.currentTime = 0 } },
    seek(position: number) { if (audio) audio.currentTime = position },
    destroy() { bind('error', undefined); bind('ended', undefined); if (audio) { audio.pause(); audio.src = '' } audio = null },
    onCanplay(fn: (event: Event) => void) { bind('canplay', fn) },
    onPlay(fn: (event: Event) => void) { bind('play', fn) },
    onError(fn: (event: Event) => void) { bind('error', fn) },
    onEnded(fn: (event: Event) => void) { bind('ended', fn) },
  }
  return api
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
    showToast, showLoading, hideLoading, showModal, showActionSheet, previewImage, pageScrollTo,
    request, chooseFile, uploadFile, downloadFile, openDocument, setClipboardData, createSelectorQuery, getSystemInfoSync,
    createCanvasContext, createInnerAudioContext,
    setNavigationBarTitle() {},
    setNavigationBarColor() {},
    onKeyboardHeightChange() {},
    getMenuButtonBoundingClientRect() { return { width: 48, height: 32, top: 8, right: 16, left: 16 } },
  }
}
