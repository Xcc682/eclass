// H5 bundles the authored high-resolution scenes. Mini Program resolves the
// same filenames through MEDIA_BASE_URL so the package stays small.
// #ifdef H5
import history_1_01 from '@/assets/immersive/history-1-01.webp'
import history_1_02 from '@/assets/immersive/history-1-02.webp'
import history_1_03 from '@/assets/immersive/history-1-03.webp'
import history_1_04 from '@/assets/immersive/history-1-04.webp'
import history_1_05 from '@/assets/immersive/history-1-05.webp'
import history_1_06 from '@/assets/immersive/history-1-06.webp'
import history_2_01 from '@/assets/immersive/history-2-01.webp'
import history_2_02 from '@/assets/immersive/history-2-02.webp'
import history_2_03 from '@/assets/immersive/history-2-03.webp'
import history_2_04 from '@/assets/immersive/history-2-04.webp'
import history_2_05 from '@/assets/immersive/history-2-05.webp'
import history_2_06 from '@/assets/immersive/history-2-06.webp'
import history_3_01 from '@/assets/immersive/history-3-01.webp'
import history_3_02 from '@/assets/immersive/history-3-02.webp'
import history_3_03 from '@/assets/immersive/history-3-03.webp'
import history_3_04 from '@/assets/immersive/history-3-04.webp'
import history_3_05 from '@/assets/immersive/history-3-05.webp'
import history_3_06 from '@/assets/immersive/history-3-06.webp'
import history_4_01 from '@/assets/immersive/history-4-01.webp'
import history_4_02 from '@/assets/immersive/history-4-02.webp'
import history_4_03 from '@/assets/immersive/history-4-03.webp'
import history_4_04 from '@/assets/immersive/history-4-04.webp'
import history_4_05 from '@/assets/immersive/history-4-05.webp'
import history_4_06 from '@/assets/immersive/history-4-06.webp'
import history_5_01 from '@/assets/immersive/history-5-01.webp'
import history_5_02 from '@/assets/immersive/history-5-02.webp'
import history_5_03 from '@/assets/immersive/history-5-03.webp'
import history_5_04 from '@/assets/immersive/history-5-04.webp'
import history_5_05 from '@/assets/immersive/history-5-05.webp'
import history_5_06 from '@/assets/immersive/history-5-06.webp'
import tour_1_01 from '@/assets/immersive/tour-1-01.webp'
import tour_1_02 from '@/assets/immersive/tour-1-02.webp'
import tour_1_03 from '@/assets/immersive/tour-1-03.webp'
import tour_1_04 from '@/assets/immersive/tour-1-04.webp'
import tour_1_05 from '@/assets/immersive/tour-1-05.webp'
import tour_1_06 from '@/assets/immersive/tour-1-06.webp'
import tour_2_01 from '@/assets/immersive/tour-2-01.webp'
import tour_2_02 from '@/assets/immersive/tour-2-02.webp'
import tour_2_03 from '@/assets/immersive/tour-2-03.webp'
import tour_2_04 from '@/assets/immersive/tour-2-04.webp'
import tour_2_05 from '@/assets/immersive/tour-2-05.webp'
import tour_2_06 from '@/assets/immersive/tour-2-06.webp'
import tour_3_01 from '@/assets/immersive/tour-3-01.webp'
import tour_3_02 from '@/assets/immersive/tour-3-02.webp'
import tour_3_03 from '@/assets/immersive/tour-3-03.webp'
import tour_3_04 from '@/assets/immersive/tour-3-04.webp'
import tour_3_05 from '@/assets/immersive/tour-3-05.webp'
import tour_3_06 from '@/assets/immersive/tour-3-06.webp'
import tour_4_01 from '@/assets/immersive/tour-4-01.webp'
import tour_4_02 from '@/assets/immersive/tour-4-02.webp'
import tour_4_03 from '@/assets/immersive/tour-4-03.webp'
import tour_4_04 from '@/assets/immersive/tour-4-04.webp'
import tour_4_05 from '@/assets/immersive/tour-4-05.webp'
import tour_4_06 from '@/assets/immersive/tour-4-06.webp'
import tour_5_01 from '@/assets/immersive/tour-5-01.webp'
import tour_5_02 from '@/assets/immersive/tour-5-02.webp'
import tour_5_03 from '@/assets/immersive/tour-5-03.webp'
import tour_5_04 from '@/assets/immersive/tour-5-04.webp'
import tour_5_05 from '@/assets/immersive/tour-5-05.webp'
import tour_5_06 from '@/assets/immersive/tour-5-06.webp'
// #endif

const media: Record<string, string> = {}
// #ifdef H5
Object.assign(media, {
  'history-1-01.webp': history_1_01,
  'history-1-02.webp': history_1_02,
  'history-1-03.webp': history_1_03,
  'history-1-04.webp': history_1_04,
  'history-1-05.webp': history_1_05,
  'history-1-06.webp': history_1_06,
  'history-2-01.webp': history_2_01,
  'history-2-02.webp': history_2_02,
  'history-2-03.webp': history_2_03,
  'history-2-04.webp': history_2_04,
  'history-2-05.webp': history_2_05,
  'history-2-06.webp': history_2_06,
  'history-3-01.webp': history_3_01,
  'history-3-02.webp': history_3_02,
  'history-3-03.webp': history_3_03,
  'history-3-04.webp': history_3_04,
  'history-3-05.webp': history_3_05,
  'history-3-06.webp': history_3_06,
  'history-4-01.webp': history_4_01,
  'history-4-02.webp': history_4_02,
  'history-4-03.webp': history_4_03,
  'history-4-04.webp': history_4_04,
  'history-4-05.webp': history_4_05,
  'history-4-06.webp': history_4_06,
  'history-5-01.webp': history_5_01,
  'history-5-02.webp': history_5_02,
  'history-5-03.webp': history_5_03,
  'history-5-04.webp': history_5_04,
  'history-5-05.webp': history_5_05,
  'history-5-06.webp': history_5_06,
  'tour-1-01.webp': tour_1_01,
  'tour-1-02.webp': tour_1_02,
  'tour-1-03.webp': tour_1_03,
  'tour-1-04.webp': tour_1_04,
  'tour-1-05.webp': tour_1_05,
  'tour-1-06.webp': tour_1_06,
  'tour-2-01.webp': tour_2_01,
  'tour-2-02.webp': tour_2_02,
  'tour-2-03.webp': tour_2_03,
  'tour-2-04.webp': tour_2_04,
  'tour-2-05.webp': tour_2_05,
  'tour-2-06.webp': tour_2_06,
  'tour-3-01.webp': tour_3_01,
  'tour-3-02.webp': tour_3_02,
  'tour-3-03.webp': tour_3_03,
  'tour-3-04.webp': tour_3_04,
  'tour-3-05.webp': tour_3_05,
  'tour-3-06.webp': tour_3_06,
  'tour-4-01.webp': tour_4_01,
  'tour-4-02.webp': tour_4_02,
  'tour-4-03.webp': tour_4_03,
  'tour-4-04.webp': tour_4_04,
  'tour-4-05.webp': tour_4_05,
  'tour-4-06.webp': tour_4_06,
  'tour-5-01.webp': tour_5_01,
  'tour-5-02.webp': tour_5_02,
  'tour-5-03.webp': tour_5_03,
  'tour-5-04.webp': tour_5_04,
  'tour-5-05.webp': tour_5_05,
  'tour-5-06.webp': tour_5_06,
})
// #endif

export function resolveImmersiveMedia(value?: string): string {
  if (!value) return ''
  const filename = value.split('/').pop() || value
  if (media[filename]) return media[filename]
  const base = (import.meta.env.VITE_MEDIA_BASE_URL || 'http://127.0.0.1:8000/media/immersive').replace(/\/$/, '')
  return `${base}/images/${filename}`
}
