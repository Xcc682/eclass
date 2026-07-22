// Navigation compatibility layer for H5 mode
// In mini-program mode, uses uni.navigateTo/switchTab
// In H5 mode, uses Vue Router

let routerInstance: any = null

export function setRouter(router: any) {
  routerInstance = router
}

export function navigateTo(options: { url: string }) {
  if (routerInstance) {
    const path = options.url.split('?')[0]
    const query: Record<string, string> = {}
    const queryStr = options.url.split('?')[1]
    if (queryStr) {
      queryStr.split('&').forEach(p => {
        const [k, v] = p.split('=')
        query[k] = decodeURIComponent(v || '')
      })
    }
    routerInstance.push({ path, query })
  } else {
    // @ts-ignore
    uni.navigateTo(options)
  }
}

export function switchTab(options: { url: string }) {
  if (routerInstance) {
    routerInstance.push(options.url)
  } else {
    // @ts-ignore
    uni.switchTab(options)
  }
}

export function navigateBack() {
  if (routerInstance) {
    routerInstance.back()
  } else {
    // @ts-ignore
    uni.navigateBack()
  }
}

export function reLaunch(options: { url: string }) {
  if (routerInstance) {
    routerInstance.replace(options.url)
  } else {
    // @ts-ignore
    uni.reLaunch(options)
  }
}
