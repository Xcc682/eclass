import { api } from './request'

export type DebateMode = 'quick' | 'full'
export type DebateStage = 'opening' | 'cross_exam' | 'rebuttal' | 'closing' | 'finished'
export type DebateStatus = 'in_progress' | 'awaiting_feedback' | 'completed' | 'abandoned'

export interface DebateTopic {
  id: string; title: string; category: string
  difficulty: string; context: string
  pro_hint: string; con_hint: string
}

export interface DebateEvidence {
  chunk_id: string; chunk_index: number
  document_id: string; document_title: string
  source: string; source_url?: string; excerpt: string
}

export interface ArgumentMap {
  claims?: string[]; evidence?: string[]; reasoning?: string[]; gaps?: string[]
}

export interface CoachFeedback {
  stage_fit?: string; strength?: string; next_action?: string
}

export interface DebateMessage {
  id: string; role: 'ai' | 'user'; content: string; stage: DebateStage
  round?: number; analysis?: Record<string, any>; evidence?: DebateEvidence[]
  local_status?: 'pending' | 'sent' | 'failed'; created_at?: string
  submission_id?: string; delivery_status?: 'pending' | 'sent' | 'failed'
  images?: string[]
}

export interface DebateSession {
  id: string; status: DebateStatus; stage: DebateStage
  step: string; step_label: string; step_index: number; total_steps: number
  completed_steps: number
  mode: DebateMode; stance: string; topic: DebateTopic
  messages: DebateMessage[]; resumed: boolean; is_finished: boolean
  first_argument?: string; stage_label?: string; stance_label?: string
  flow_version: number; is_legacy: boolean; has_report: boolean
  report_status: 'idle' | 'generating' | 'failed' | 'completed'
}

export interface DebateFeedback {
  overall_score: number; grade?: string
  dimension_scores: Record<string, number>
  dimension_analysis?: Array<{ name: string; score: number; suggestion: string }>
  strengths: string[]; weaknesses: string[]; suggestion: string
  key_exchanges?: Array<{ title: string; summary: string; edge: string; improvement: string; message_ids?: string[]; round?: number }>
}

export interface DebateArgumentResponse {
  argument: string; round: number; stage: DebateStage; next_stage: DebateStage
  step: string; step_label: string; next_step: string; step_index: number; total_steps: number
  completed_steps: number
  stage_complete: boolean; phase_transition: string; is_finished: boolean; status: DebateStatus
  coach_feedback: CoachFeedback; argument_map: ArgumentMap; citations: DebateEvidence[]
  user_message_id: string; ai_message_id: string
}

export interface DebateHistoryItem {
  id: string; topic_id: string; topic_title: string; stance: string
  status: DebateStatus; stage: DebateStage; mode: DebateMode
  completed_steps?: number; total_steps?: number; step_index?: number; rounds?: number; score?: number | null
  is_legacy?: boolean; has_report?: boolean; report_status?: string; started_at: string
}

export const debateApi = {
  getTopics: () => api.get<DebateTopic[]>('/debates/topics'),
  generateTopics: () => api.post<DebateTopic[]>('/debates/topics/generate'),
  startDebate: (topic_id: string, stance: string, mode: DebateMode = 'full', restart = false) =>
    api.post<DebateSession>('/debates/practice/start', { topic_id, stance, mode, restart }, { timeout: 65000, toast: false }),
  getPractice: (sessionId: string) => api.get<DebateSession>(`/debates/practice/${sessionId}`),
  searchEvidence: (sessionId: string, query: string) =>
    api.post<DebateEvidence[]>(`/debates/practice/${sessionId}/evidence/search`, { query }, { timeout: 30000, toast: false }),
  submitArgument: (sessionId: string, argument: string, submission_id: string, evidence_refs: Array<{chunk_id:string}> = [], images: string[] = []) =>
    api.post<DebateArgumentResponse>(`/debates/practice/${sessionId}/argue`, { argument, evidence_refs, submission_id, images }, { timeout: 65000, toast: false }),
  endDebate: (sessionId: string) =>
    api.post<DebateFeedback>(`/debates/practice/${sessionId}/end`, undefined, { timeout: 65000, toast: false }),
  getFeedback: (sessionId: string) => api.get<DebateFeedback>(`/debates/practice/${sessionId}/feedback`),
  getHistory: () => api.get<DebateHistoryItem[]>('/debates/history'),
}
