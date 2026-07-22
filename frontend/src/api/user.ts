import { api } from './request'

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
  growth: {
    total_interviews: number
    total_history_scenarios: number
    total_debates: number
    total_tours: number
    total_reports: number
    total_points: number
    average_interview_score?: number | null
    streak_days: number
    rank: number
    ability_dimensions: Array<{ name: string; score: number }>
    activities: Array<{ id: string; type: string; title: string; score?: number | null; time: string }>
  }
}

export interface LoginResult { token: string; user: UserInfo }

export const userApi = {
  login: (data: { phone: string; password: string }) =>
    api.post<LoginResult>('/auth/login', data),

  yibanLogin: (data: { auth_code: string }) =>
    api.post<LoginResult>('/auth/yiban-login', data),

  getYibanStatus: () => api.get<{ configured: boolean; bound: boolean; yiban_id?: string | null; available: boolean; message: string }>('/auth/yiban/status'),

  getProfile: () => api.get<UserInfo>('/users/profile'),

  updateProfile: (data: Partial<UserInfo>) =>
    api.put<UserInfo>('/users/profile', data),

  getGrowth: () => api.get<UserInfo['growth']>('/users/growth'),

  getAchievements: () => api.get('/users/achievements'),

  getReports: () => api.get('/users/reports')
}
