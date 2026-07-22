import { api } from './request'

export interface DebateTopic {
  id: string; title: string; category: string
  difficulty: string; context: string
  pro_hint: string; con_hint: string
}

export interface DebateFeedback {
  overall_score: number
  dimension_scores: Record<string, number>
  dimension_analysis?: Array<{
    name: string
    score: number
    suggestion: string
  }>
  strengths: string[]; weaknesses: string[]
  suggestion: string
}

export interface DebateStartResponse {
  id: string
  first_argument: string
  stage: string
  stage_label: string
  stance: string
  stance_label: string
  topic: DebateTopic
}

export interface DebateArgumentResponse {
  argument: string
  round: number
  stage: string
  next_stage: string
  stage_complete: boolean
  phase_transition: string
  is_finished: boolean
}

export const debateApi = {
  getTopics: () => api.get<DebateTopic[]>('/debates/topics'),
  generateTopics: () => api.post<DebateTopic[]>('/debates/topics/generate'),
  startDebate: (topic_id: string, stance: string) =>
    api.post<DebateStartResponse>('/debates/practice/start', { topic_id, stance }),
  submitArgument: (sessionId: string, argument: string) =>
    api.post<DebateArgumentResponse>(`/debates/practice/${sessionId}/argue`, { argument }),
  endDebate: (sessionId: string) =>
    api.post<DebateFeedback>(`/debates/practice/${sessionId}/end`),
  getFeedback: (sessionId: string) =>
    api.get<DebateFeedback>(`/debates/practice/${sessionId}/feedback`),
}
