import { api } from './request'

export interface TourSite {
  id: string; name: string; location: string
  description: string; emoji: string
  facts: string[]
}

export interface TourHistoryItem {
  id: string
  site_id: string
  site_name: string
  completed: boolean
  qa_count: number
  created_at: string
}

export const tourApi = {
  getSites: () => api.get<TourSite[]>('/tours/sites'),
  getSite: (id: string) => api.get<TourSite>(`/tours/sites/${id}`),
  startSession: (site_id: string) => api.post<{ id: string; site_id: string; qa_history: Array<{q:string;a:string}>; completed: boolean; resumed: boolean }>('/tours/sessions/start', { site_id }),
  getIntro: (site_id: string) =>
    api.post<{ intro: string }>('/tours/intro', { site_id }),
  askQuestion: (site_id: string, question: string, record_id?: string) =>
    api.post<{ answer: string }>('/tours/ask', { site_id, question, record_id }),
  generateReport: (site_id: string, qa_history: string[] = [], record_id?: string) =>
    api.post<{ id: string; report: string }>('/tours/generate-report', { site_id, qa_history, record_id }),
  getSession: (id: string) => api.get<{ id: string; site_id: string; qa_history: Array<{q:string;a:string}>; report: string; completed: boolean; note?: string }>(`/tours/sessions/${id}`),
  getHistory: () => api.get<TourHistoryItem[]>('/tours/history'),
}
