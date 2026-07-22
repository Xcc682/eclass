import { api } from './request'
import { resolveImmersiveMedia } from '@/assets/immersiveMedia'

export type ImmersiveModule = 'history' | 'tour'
export type SpreadType = 'cover' | 'cinematic' | 'exploration' | 'dialogue' | 'decision' | 'archive' | 'reflection' | 'ending'

export interface SourceReference {
  title: string
  organization: string
  url?: string
  excerpt?: string
}

export interface SceneHotspot {
  id: string
  x: number
  y: number
  title: string
  content: string
}

export interface SceneOption {
  id: string
  label: string
  feedback: string
}

export interface ImmersiveEventAnchor {
  date: string
  place: string
  title: string
  summary: string
  meaning: string
}

export interface ImmersiveScene {
  eyebrow?: string
  title?: string
  caption?: string
  cta?: string
  prompt?: string
  dialogue?: string
  archive_excerpt?: string
  note_placeholder?: string
  position?: string
  scale?: number
  particles?: 'rain' | 'dust' | 'mist' | string
  reconstruction?: boolean
  contemporary?: boolean
  hotspots?: SceneHotspot[]
  options?: SceneOption[]
  event?: ImmersiveEventAnchor
  timeline?: ImmersiveEventAnchor[]
  timeline_index?: number
}

export interface ImmersiveSpread {
  id: string
  order_index: number
  type: SpreadType
  layout: string
  image_url: string
  thumbnail_url: string
  audio_url: string
  narration: string
  scene: ImmersiveScene
  sources: SourceReference[]
}

export interface ImmersiveProgress {
  current_spread: number
  discovered_hotspots: string[]
  choice: { spread_id?: string; option_id?: string }
  note: string
  qa_history: Array<{ q: string; a: string; spread_id?: string; created_at?: string }>
  sound_enabled: boolean
  captions_enabled: boolean
  completed: boolean
  related_record_id?: string | null
  updated_at?: string | null
}

export interface ImmersiveBookSummary {
  id: string
  module: ImmersiveModule
  source_id: string
  title: string
  subtitle: string
  era: string
  location: string
  cover_url: string
  version: number
  duration: number
  order_index: number
  progress: ImmersiveProgress
}

export interface ImmersiveBook extends ImmersiveBookSummary {
  spreads: ImmersiveSpread[]
}

export interface ProgressPatch {
  current_spread?: number
  discovered_hotspot?: string
  choice_spread_id?: string
  choice_option_id?: string
  note?: string
  sound_enabled?: boolean
  captions_enabled?: boolean
}

export const immersiveApi = {
  getBooks: async (module: ImmersiveModule) => (await api.get<ImmersiveBookSummary[]>('/immersive/books', { module })).map(book => ({ ...book, cover_url: resolveImmersiveMedia(book.cover_url) })),
  getBook: async (bookId: string) => {
    const book = await api.get<ImmersiveBook>(`/immersive/books/${bookId}`)
    return {
      ...book,
      cover_url: resolveImmersiveMedia(book.cover_url),
      spreads: book.spreads.map(spread => ({ ...spread, image_url: resolveImmersiveMedia(spread.image_url), thumbnail_url: resolveImmersiveMedia(spread.thumbnail_url) })),
    }
  },
  updateProgress: (bookId: string, data: ProgressPatch) => api.patch<ImmersiveProgress>(`/immersive/books/${bookId}/progress`, data, { toast: false }),
  ask: (bookId: string, question: string, spreadId?: string) => api.post<{ answer: string; qa_history: ImmersiveProgress['qa_history'] }>(`/immersive/books/${bookId}/ask`, { question, spread_id: spreadId }, { timeout: 55000 }),
  complete: (bookId: string) => api.post<{ completed: boolean; already_completed: boolean; points?: number; report: string; record_id?: string | null }>(`/immersive/books/${bookId}/complete`, {}, { timeout: 60000 }),
}
