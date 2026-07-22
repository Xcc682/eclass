import { api } from './request'

export interface KnowledgeDocument {
  id: string
  title: string
  category: string
  summary: string
  source: string
  source_url: string
  content?: string
  status: string
  version: number
  file_name?: string
  mime_type?: string
  view_count: number
  chunk_count: number
  processing_error?: string
  is_favorite: boolean
  created_at: string
  published_at?: string
  viewed_at?: string
}

export interface KnowledgeTemplate { id: string; name: string; desc: string; prompt?: string }
export interface Citation {
  index: number
  document_id: string
  document_title: string
  source: string
  source_url: string
  chunk_id: string
  chunk_index: number
  excerpt: string
  relevance_score?: number
  relevance_reason?: string
}
export interface KnowledgeMessage { id: string; role: 'user' | 'assistant'; content: string; citations: Citation[]; created_at: string }
export interface KnowledgeSession { id: string; title: string; created_at: string; updated_at: string; messages?: KnowledgeMessage[] }
export interface KnowledgeIngestionJob {
  id: string
  document_id: string
  document_title: string
  file_name?: string
  document_status?: string
  status: 'queued' | 'processing' | 'completed' | 'failed'
  progress: number
  error?: string
  updated_at?: string
}

export interface KnowledgeDocumentPage {
  data: KnowledgeDocument[]
  pagination: { page: number; page_size: number; total: number }
}

export interface KnowledgeDocumentUpdate {
  title: string
  category: string
  source: string
  source_url: string
  summary: string
  version: number
}

export class DuplicateKnowledgeDocumentError extends Error {
  code = 'DUPLICATE_DOCUMENT'
  document?: KnowledgeDocument

  constructor(message: string, document?: KnowledgeDocument) {
    super(message)
    this.name = 'DuplicateKnowledgeDocumentError'
    this.document = document
  }
}

function queryString(params: Record<string, string | number | undefined>) {
  const value = Object.entries(params).filter(([, item]) => item !== undefined && item !== '').map(([key, item]) => `${encodeURIComponent(key)}=${encodeURIComponent(String(item))}`).join('&')
  return value ? `?${value}` : ''
}

function upload<T>(file: any, formData: Record<string, string | number>): Promise<T> {
  return new Promise((resolve, reject) => {
    const token = uni.getStorageSync('token')
    ;(uni as any).uploadFile({
      url: `${import.meta.env.VITE_API_BASE_URL || '/api/v1'}/knowledge/documents/upload`,
      filePath: typeof file === 'string' ? file : undefined,
      file,
      name: 'file',
      formData,
      header: token ? { Authorization: `Bearer ${token}` } : {},
      success: (response: any) => {
        let result: any
        try { result = typeof response.data === 'string' ? JSON.parse(response.data) : response.data } catch { reject(new Error('上传响应格式错误')); return }
        if ((response.statusCode || 200) >= 400) {
          const detail = result.detail
          if (detail?.code === 'DUPLICATE_DOCUMENT') {
            reject(new DuplicateKnowledgeDocumentError(detail.message || '相同文件已上传', detail.document))
          } else {
            reject(new Error(typeof detail === 'string' ? detail : detail?.message || '上传失败'))
          }
          return
        }
        resolve(result.data as T)
      },
      fail: (error: any) => reject(new Error(error.errMsg || '上传失败')),
    })
  })
}

export const knowledgeApi = {
  getDocuments: (params: { category?: string; q?: string; page?: number; page_size?: number; sort?: string } | string = {}) => {
    const values = typeof params === 'string' ? { category: params } : params
    return api.get<KnowledgeDocument[]>(`/knowledge/documents${queryString(values)}`)
  },
  getDocumentPage: (params: { category?: string; q?: string; page?: number; page_size?: number; sort?: string } = {}) =>
    api.get<KnowledgeDocumentPage>(`/knowledge/documents${queryString(params)}`, undefined, { raw: true }),
  getDocument: (id: string) => api.get<KnowledgeDocument>(`/knowledge/documents/${id}`),
  getDocumentChunk: (id: string, index: number) => api.get<{ id: string; document_id: string; chunk_index: number; content: string }>(`/knowledge/documents/${id}/chunks/${index}`),
  getTemplates: () => api.get<KnowledgeTemplate[]>('/knowledge/templates'),
  search: (query: string, category?: string) => api.post<KnowledgeDocument[]>('/knowledge/search', { query, category }),
  ask: (question: string, session_id?: string, category?: string) => api.post<{ answer: string; session_id: string; citations: Citation[] }>('/knowledge/ask', { question, session_id, category }, { timeout: 65000, toast: false }),
  sessions: () => api.get<KnowledgeSession[]>('/knowledge/sessions'),
  session: (id: string) => api.get<KnowledgeSession>(`/knowledge/sessions/${id}`),
  deleteSession: (id: string) => api.delete<{ id: string; deleted: boolean }>(`/knowledge/sessions/${id}`),
  favorite: (id: string) => api.post(`/knowledge/favorites/${id}`),
  unfavorite: (id: string) => api.delete(`/knowledge/favorites/${id}`),
  favorites: () => api.get<KnowledgeDocument[]>('/knowledge/favorites'),
  recent: () => api.get<KnowledgeDocument[]>('/knowledge/recent'),
  generate: (template_id: string, requirements = '', personal_background = '') => api.post<{ id: string; title: string; content: string }>('/knowledge/templates/generate', { template_id, requirements, personal_background }),
  templateHistory: () => api.get<Array<{ id: string; title: string; content: string; created_at: string }>>('/knowledge/templates/history'),
  updateTemplateHistory: (id: string, content: string) => api.put<{ id: string; content: string }>(`/knowledge/templates/history/${id}`, { content }),
  deleteTemplateHistory: (id: string) => api.delete<{ id: string; deleted: boolean }>(`/knowledge/templates/history/${id}`),
  manageDocuments: (status?: string) => api.get<KnowledgeDocument[]>(`/knowledge/manage/documents${queryString({ status })}`),
  uploadDocument: (file: any, fields: { title: string; category: string; source: string; source_url?: string; version?: number }) => upload<{ document: KnowledgeDocument; job_id: string }>(file, fields as any),
  ingestionJob: (id: string) => api.get<KnowledgeIngestionJob>(`/knowledge/ingestion-jobs/${id}`),
  publish: (id: string) => api.post(`/knowledge/documents/${id}/publish`),
  reject: (id: string, reason: string) => api.post(`/knowledge/documents/${id}/reject`, { reason }),
  updateDocument: (id: string, fields: KnowledgeDocumentUpdate) => api.put<KnowledgeDocument>(`/knowledge/documents/${id}`, fields),
  resubmit: (id: string) => api.post<KnowledgeDocument>(`/knowledge/documents/${id}/resubmit`),
  deleteDocument: (id: string) => api.delete<{ id: string; deleted: boolean; warnings: string[] }>(`/knowledge/documents/${id}`),
  reindex: (id: string) => api.post<{ job_id: string; document_id: string; document_status: string }>(`/knowledge/documents/${id}/reindex`),
}
