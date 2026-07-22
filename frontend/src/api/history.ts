import { api } from './request'

export interface HistoryScenario {
  id: string
  year: number
  era: string
  title: string
  description: string
  background: string
  duration: number
  completed?: boolean
  progress?: number
  choice_index?: number | null
  qa_history?: Array<{ q: string; a: string }>
  knowledge_points: Array<{ title: string; content: string }>
  decision_points?: {
    text: string
    options: Array<{ label: string; feedback: string }>
  }
}

export const historyApi = {
  getScenarios: () => api.get<HistoryScenario[]>('/history/scenarios'),
  getScenario: (id: string) => api.get<HistoryScenario>(`/history/scenarios/${id}`),
  ask: (scenario_id: string, question: string) => api.post<{ answer: string }>('/history/ask', { scenario_id, question }),
  complete: (id: string) => api.post<{ completed: boolean; progress: number }>(`/history/scenarios/${id}/complete`),
  choose: (id: string, option_index: number) => api.post<{ option_index: number; feedback: string; progress: number }>(`/history/scenarios/${id}/choice`, { option_index }),
}
