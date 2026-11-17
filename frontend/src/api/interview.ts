import { api } from './request'

export type InterviewStatus = 'in_progress' | 'awaiting_report' | 'completed' | 'abandoned'

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
  has_active_practice?: boolean
}

export interface LiveDimension {
  score: number | null
  evidence_count: number
  trend: 'pending' | 'up' | 'down' | 'stable'
  latest_evidence: string
}

export interface LiveEvaluation {
  dimensions: Record<string, LiveDimension>
  disclaimer: string
}

export interface InterviewMessage {
  id: string
  role: 'ai' | 'user'
  content: string
  analysis?: Record<string, any>
  ai_analysis?: Record<string, any>
  round_number: number
  created_at?: string
  local_status?: 'pending' | 'sent' | 'failed'
  submission_id?: string
  delivery_status?: 'pending' | 'sent' | 'failed'
}

export interface InterviewPractice {
  id: string
  scenario: InterviewScenario
  first_question: string
  messages: InterviewMessage[]
  status: InterviewStatus
  phase: string
  phase_index: number
  question_index: number
  answered_count: number
  current_question_number: number | null
  total_questions: number
  is_completed: boolean
  resumed: boolean
  live_evaluation: LiveEvaluation
  flow_version: number
  is_legacy: boolean
  has_report: boolean
  report_status: 'idle' | 'generating' | 'failed' | 'completed'
}

export interface InterviewTurn {
  question: string
  analysis: Record<string, any>
  is_completed: boolean
  status: InterviewStatus
  phase: string
  phase_index: number
  question_index: number
  answered_count: number
  current_question_number: number | null
  total_questions: number
  live_evaluation: LiveEvaluation
  user_message: InterviewMessage
  ai_message: InterviewMessage
}

export interface InterviewHistoryItem {
  id: string
  scenario_id: string
  requested_scenario_id?: string
  scenario_title: string
  status: InterviewStatus
  phase: string
  answered_count: number
  total_questions: number
  rounds?: number
  score?: number | null
  is_legacy: boolean
  has_report?: boolean
  report_status: string
  started_at: string
}

export interface InterviewReport {
  overall_score: number
  grade: string
  dimension_scores: Record<string, number>
  dimension_analysis: Array<{ name: string; score: number; suggestion: string }>
  strengths: string[]
  weaknesses: string[]
  suggestion: string
  total_rounds: number
  delta?: Record<string, number>
  has_previous?: boolean
  disclaimer?: string
  conversation?: InterviewMessage[]
}

export const interviewApi = {
  getScenarios: () => api.get<InterviewScenario[]>('/interviews/scenarios'),
  getScenario: (id: string) => api.get<InterviewScenario>(`/interviews/scenarios/${id}`),
  startPractice: (scenario_id: string, restart = false) =>
    api.post<InterviewPractice>('/interviews/practice/start', { scenario_id, restart }),
  submitResponse: (practiceId: string, content: string, submission_id: string, images?: string[]) =>
    api.post<InterviewTurn>(`/interviews/practice/${practiceId}/respond`, { content, submission_id, ...(images?.length ? { images } : {}) }, { timeout: 65000, toast: false }),
  endPractice: (practiceId: string) =>
    api.post<InterviewReport>(`/interviews/practice/${practiceId}/end`, undefined, { timeout: 65000, toast: false }),
  getReport: (practiceId: string) => api.get<InterviewReport>(`/interviews/practice/${practiceId}/report`),
  getHint: (practiceId: string) => api.post<{ hint: string }>(`/interviews/practice/${practiceId}/hint`, undefined, { timeout: 45000, toast: false }),
  getHistory: () => api.get<InterviewHistoryItem[]>('/interviews/history'),
  getPractice: (id: string) => api.get<InterviewPractice>(`/interviews/practice/${id}`),
}
