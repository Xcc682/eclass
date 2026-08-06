import { api } from './request'

export interface PointTransaction {
  id: string
  module: string
  module_label: string
  event_type: string
  source_id: string
  points: number
  description: string
  rule_version: string
  created_at: string
}

export interface ModuleGrowth {
  key: 'interview' | 'debate' | 'history' | 'tour'
  label: string
  description: string
  weight: number
  points: number
  completed_count: number
  total_available: number | null
  mastery_score: number
  average_score: number | null
  level: string
}

export type PracticeModule = 'interview' | 'debate' | 'history' | 'tour'
export type PracticeArchiveStatus = 'in_progress' | 'awaiting_report' | 'completed' | 'legacy'

export interface PracticeArchiveItem {
  id: string
  module: PracticeModule
  source_id: string
  title: string
  status: PracticeArchiveStatus
  score: number | null
  completed_steps: number
  total_steps: number
  progress_percent: number
  has_report: boolean
  is_legacy: boolean
  updated_at: string
  context: {
    practice_id?: string
    scenario_id?: string
    session_id?: string
    topic_id?: string
    topic_title?: string
    stance?: 'pro' | 'con'
    mode?: 'quick' | 'full'
    book_id?: string
    record_id?: string | null
    site_id?: string
    site_name?: string
  }
}

export interface PracticeArchive {
  summary: {
    total: number
    in_progress: number
    awaiting_report: number
    completed: number
    legacy: number
  }
  items: PracticeArchiveItem[]
}

export interface FormalReportItem {
  id: string
  type: 'interview' | 'debate' | 'tour'
  title: string
  score: number | null
  content: string | Record<string, unknown>
  source_record_id: string
  is_legacy: boolean
  context: PracticeArchiveItem['context']
  created_at: string
}

export interface UserInfo {
  id: string
  nickname: string
  avatar_url: string
  school: string
  college: string
  political_status: string
  role: 'student' | 'teacher' | 'admin'
  yiban_id?: string | null
  total_points: number
  features?: {
    notifications_available: boolean
    yiban_binding_available: boolean
    yiban_bound: boolean
  }
  growth: {
    total_interviews: number
    total_history_scenarios: number
    total_debates: number
    total_tours: number
    total_reports: number
    current_reports?: number
    legacy_interviews?: number
    legacy_debates?: number
    total_points: number
    average_interview_score?: number | null
    streak_days: number
    rank: number
    ability_dimensions: Array<{ name: string; score: number; evidence?: string[] }>
    ability_profile?: {
      dimensions: Array<{ name: string; score: number; evidence?: string[] }>
      coverage: number
      disclaimer: string
    }
    module_growth?: ModuleGrowth[]
    growth_index?: {
      score: number
      coverage: number
      covered_modules: number
      total_modules: number
      weights: Record<string, number>
      method: string
    }
    point_summary?: {
      total: number
      ledger_total: number
      traceable_points: number
      legacy_balance: number
      by_module: Record<string, number>
      is_reconciled: boolean
      recent_transactions: PointTransaction[]
    }
    activities: Array<{ id: string; type: string; title: string; score?: number | null; time: string }>
  }
}

export interface LoginResult { token: string; user: UserInfo }

export const userApi = {
  login: (data: { phone: string; password: string }) =>
    api.post<LoginResult>('/auth/login', data),

  register: (data: { phone: string; password: string }) =>
    api.post<LoginResult>('/auth/register', data),

  yibanLogin: (data: { auth_code: string }) =>
    api.post<LoginResult>('/auth/yiban-login', data),

  getYibanStatus: () => api.get<{ configured: boolean; bound: boolean; yiban_id?: string | null; available: boolean; message: string }>('/auth/yiban/status'),

  getProfile: () => api.get<UserInfo>('/users/profile'),

  updateProfile: (data: Partial<UserInfo>) =>
    api.put<UserInfo>('/users/profile', data),

  getGrowth: () => api.get<UserInfo['growth']>('/users/growth'),

  getPoints: () => api.get<NonNullable<UserInfo['growth']['point_summary']>>('/users/points'),

  getAchievements: () => api.get('/users/achievements'),

  getPractices: () => api.get<PracticeArchive>('/users/practices'),

  getReports: (scope: 'current' | 'legacy' = 'current') =>
    api.get<FormalReportItem[]>(`/users/reports?scope=${scope}`)
}
