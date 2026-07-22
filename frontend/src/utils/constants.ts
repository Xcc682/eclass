export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

export const POLITICAL_STATUS_OPTIONS = [
  { label: '群众', value: '群众' },
  { label: '共青团员', value: '共青团员' },
  { label: '入党积极分子', value: '入党积极分子' },
  { label: '预备党员', value: '预备党员' },
  { label: '中共党员', value: '中共党员' }
]

export const DIFFICULTY_LABELS: Record<string, string> = {
  beginner: '初级', intermediate: '中级', advanced: '高级'
}

export const GRADE_LABELS: Record<string, { label: string; color: string }> = {
  excellent: { label: '优秀', color: '#2E7D32' },
  good: { label: '良好', color: '#F57C00' },
  needs_improvement: { label: '需努力', color: '#D32F2F' }
}

export const STORAGE_KEYS = {
  TOKEN: 'token', USER_INFO: 'user_info', SETTINGS: 'app_settings'
}
