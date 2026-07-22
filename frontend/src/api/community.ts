import { api } from './request'

export interface CommunityPost {
  id: string
  title: string
  content: string
  excerpt: string
  category: string
  is_question: boolean
  resolved: boolean
  accepted_reply_id?: string | null
  author_id: string
  author: string
  likes: number
  replies: number
  views: number
  created_at: string
  reply_list?: Array<{ id: string; content: string; author: string; author_id: string; is_teacher: boolean; accepted: boolean; created_at: string }>
}

export interface TeacherTask { id: string; title: string; description: string; deadline: string; status: string; submission?: { id: string; status: string; score?: number; feedback?: string } | null }

export const communityApi = {
  getPosts: (kind = 'all') => api.get<CommunityPost[]>(`/community/posts?kind=${kind}`),
  getPost: (id: string) => api.get<CommunityPost>(`/community/posts/${id}`),
  createPost: (data: { title: string; content: string; category: string; is_question: boolean }) => api.post<CommunityPost>('/community/posts', data),
  reply: (id: string, content: string) => api.post(`/community/posts/${id}/replies`, { content }),
  like: (id: string) => api.post<{ likes: number; liked: boolean }>(`/community/posts/${id}/like`),
  unlike: (id: string) => api.delete<{ likes: number; liked: boolean }>(`/community/posts/${id}/like`),
  resolve: (postId: string, replyId: string) => api.post(`/community/posts/${postId}/resolve/${replyId}`),
  updatePost: (id: string, data: { title: string; content: string; category: string }) => api.put<CommunityPost>(`/community/posts/${id}`, data),
  deletePost: (id: string) => api.delete(`/community/posts/${id}`),
  getTasks: () => api.get<TeacherTask[]>('/community/tasks'),
  createTask: (data: { title: string; description: string; deadline: string }) => api.post<TeacherTask>('/community/tasks', data),
  submitTask: (id: string, content: string) => api.post(`/community/tasks/${id}/submissions`, { content }),
}
