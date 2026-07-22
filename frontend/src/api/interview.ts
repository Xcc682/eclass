import { api } from './request'

export interface InterviewScenario {
  id: string
  title: string
  description: string
  difficulty: 'beginner' | 'intermediate' | 'advanced' | 'random'
  estimated_duration: number
  cover_image?: string
  ai_role_name: string
  ai_role_title: string
  completion_status?: 'not_started' | 'in_progress' | 'completed'
  best_score?: number
}

export interface InterviewMessage {
  id: string
  role: 'ai' | 'user'
  content: string
  ai_analysis?: {
    dimension_scores: Record<string, number>
    strengths: string[]
    weaknesses: string[]
  }
  round_number: number
  created_at: string
}

export interface InterviewReport {
  overall_score: number
  grade: string
  dimension_scores: Record<string, number>
  dimension_analysis: Array<{
    name: string
    score: number
    suggestion: string
  }>
  strengths: string[]
  weaknesses: string[]
  suggestion: string
  total_rounds: number
  conversation: InterviewMessage[]
}

export const interviewApi = {
  getScenarios: () => api.get<InterviewScenario[]>('/interviews/scenarios'),

  getScenario: (id: string) => api.get<InterviewScenario>(`/interviews/scenarios/${id}`),

  startPractice: (scenario_id: string) =>
    api.post<{ id: string; first_question: string }>('/interviews/practice/start', { scenario_id }),

  submitResponse: (practiceId: string, content: string) =>
    api.post<{ question: string; analysis: any; is_completed: boolean }>(
      `/interviews/practice/${practiceId}/respond`, { content }
    ),

  endPractice: (practiceId: string) =>
    api.post<InterviewReport>(`/interviews/practice/${practiceId}/end`),

  getReport: (practiceId: string) =>
    api.get<InterviewReport>(`/interviews/practice/${practiceId}/report`),

  getHint: (practiceId: string) =>
    api.post<{ hint: string }>(`/interviews/practice/${practiceId}/hint`),

  getHistory: () => api.get('/interviews/history'),
  getPractice: (id: string) => api.get(`/interviews/practice/${id}`),
}
