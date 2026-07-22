// API 请求封装
const TOKEN_KEY = 'token'

type RequestOptions = {
  url: string
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  data?: any
  loading?: boolean
  toast?: boolean
  timeout?: number
  raw?: boolean
}

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

function normalizeErrorMessage(error: any, fallback = '请求失败，请稍后重试') {
  const raw = typeof error === 'string' ? error : error?.message || error?.errMsg || error?.detail
  if (!raw) return fallback
  if (typeof raw === 'object') return raw.message || fallback
  if (/timeout|timed out|超时/i.test(raw)) return '请求超时，请稍后重试'
  if (/Network Error|request:fail|Failed to fetch|ERR_NETWORK/i.test(raw)) return '网络连接异常，请检查后重试'
  return raw
}

export async function request<T = any>(options: RequestOptions): Promise<T> {
  const { url, method = 'GET', data, loading = false, toast = true, timeout = 30000 } = options

  loading && uni.showLoading({ title: '加载中...', mask: true })

  try {
    const token = uni.getStorageSync(TOKEN_KEY)
    const header: Record<string, string> = {
      'Content-Type': 'application/json'
    }
    if (token) {
      header['Authorization'] = `Bearer ${token}`
    }

    const response = await uni.request({
      url: `${BASE_URL}${url}`,
      method: method as any,
      data,
      header,
      timeout
    })

    const result = response.data as any
    const statusCode = (response as any).statusCode || 200

    if (statusCode === 401) {
      uni.removeStorageSync(TOKEN_KEY)
      uni.reLaunch({ url: '/pages/login/login' })
      throw new Error(normalizeErrorMessage(result.detail, '登录已过期，请重新登录'))
    }
    if (statusCode >= 400) {
      const fallback = statusCode === 503 ? '服务暂不可用，请稍后重试' : `请求失败（${statusCode}）`
      throw new Error(normalizeErrorMessage(result.detail || result.message, fallback))
    }

    if (result.code === 0 || result.code === 200) {
      return (options.raw ? result : result.data) as T
    }

    throw new Error(result.message || '请求失败')
  } catch (err: any) {
    const message = normalizeErrorMessage(err)
    if (toast && message) {
      uni.showToast({ title: message, icon: 'none' })
    }
    throw new Error(message)
  } finally {
    loading && uni.hideLoading()
  }
}

// 便捷方法
export const api = {
  get: <T = any>(url: string, data?: any, options: Omit<RequestOptions, 'url' | 'method' | 'data'> = {}) => request<T>({ ...options, url, method: 'GET', data }),
  post: <T = any>(url: string, data?: any, options: Omit<RequestOptions, 'url' | 'method' | 'data'> = {}) => request<T>({ ...options, url, method: 'POST', data }),
  put: <T = any>(url: string, data?: any, options: Omit<RequestOptions, 'url' | 'method' | 'data'> = {}) => request<T>({ ...options, url, method: 'PUT', data }),
  patch: <T = any>(url: string, data?: any, options: Omit<RequestOptions, 'url' | 'method' | 'data'> = {}) => request<T>({ ...options, url, method: 'PATCH', data }),
  delete: <T = any>(url: string, data?: any, options: Omit<RequestOptions, 'url' | 'method' | 'data'> = {}) => request<T>({ ...options, url, method: 'DELETE', data })
}
