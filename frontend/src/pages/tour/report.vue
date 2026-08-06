<template>
  <div class="report">
    <header class="report-hero">
      <div class="report-hero__image" :style="{ backgroundImage: `url(${tourHero})` }"></div>
      <div class="report-hero__shade"></div>
      <div class="report-hero__copy"><span>EXPEDITION ARCHIVE</span><h1>研学现场报告</h1><p>{{ siteName }}</p></div>
    </header>

    <main class="report__main">
      <section class="report-ticket">
        <div><span>档案类型</span><strong>红色研学手记</strong></div>
        <div><span>生成状态</span><strong>{{ loading ? '正在整理' : reportError ? '生成失败' : '已归档' }}</strong></div>
        <div><span>研学印章</span><strong>{{ reportError ? '未点亮' : loading ? '待确认' : '已点亮' }}</strong></div>
      </section>

      <section v-if="loading" class="report-loading">
        <div class="report-loading__seal">研</div>
        <h2>正在整理你的现场档案</h2>
        <p>AI 正在结合地标资料、追问记录与研学手记组织报告，请暂候。</p>
        <div><i></i></div>
      </section>

      <section v-else-if="reportError" class="report-error">
        <span>生成未完成</span><h2>{{ reportError }}</h2><p>本次不会产生虚假积分或空报告，你可以保留手记后重新尝试。</p>
        <button @click="loadReport">{{ viewOnly ? '重新读取' : '重新生成' }}</button>
      </section>

      <template v-else>
        <section class="report-paper">
          <div class="report-paper__masthead"><span>研学记录 · {{ today }}</span><span>NO. {{ shortId }}</span></div>
          <h2>{{ siteName }}研学心得</h2>
          <div class="report-paper__rule"><i></i><span>FIELD NOTES</span><i></i></div>
          <p>{{ reportText }}</p>
          <div class="report-paper__stamp"><strong>研学<br />归档</strong><span>{{ todayShort }}</span></div>
          <div class="report-paper__footer">本报告由个人研学过程与 AI 辅助整理生成，请结合权威史料进一步学习。</div>
        </section>

        <section v-if="fieldNote" class="source-note">
          <span>我的原始手记</span><p>{{ fieldNote }}</p>
        </section>

        <div class="report__actions">
          <button class="report__action report__action--primary" @click="copyReport">复制报告</button>
          <button class="report__action" @click="backToSites">返回研学路线</button>
        </div>
      </template>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { tourApi } from '@/api/tour'
import tourHero from '@/static/images/scenes/tour-expedition-hero.png'

const siteName = ref('红色景点')
const siteId = ref('1')
const reportText = ref('')
const loading = ref(true)
const reportError = ref('')
const recordId = ref('')
const fieldNote = ref('')
const viewOnly = ref(false)
const now = new Date()
const today = now.toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' })
const todayShort = `${now.getFullYear()}.${String(now.getMonth() + 1).padStart(2, '0')}.${String(now.getDate()).padStart(2, '0')}`
const shortId = computed(() => recordId.value ? recordId.value.slice(0, 8).toUpperCase() : 'PENDING')

onLoad((query: any) => {
  siteId.value = query.siteId || '1'
  siteName.value = decodeURIComponent(query.siteName || '红色景点')
  recordId.value = query.recordId || ''
  viewOnly.value = query.view === '1'
  loadReport()
})

async function loadReport() {
  if (!recordId.value) { loading.value = false; reportError.value = '研学记录尚未建立'; return }
  loading.value = true; reportError.value = ''
  try {
    if (viewOnly.value) {
      const session = await tourApi.getSession(recordId.value)
      if (!session?.completed || !session.report?.trim()) throw new Error('这份研学记录尚未形成正式报告')
      reportText.value = session.report
      fieldNote.value = session.note || ''
      return
    }
    // 手记由后端从沉浸式进度中读取并一并喂给 AI，前端无需再上传。
    fieldNote.value = ''
    const res = await tourApi.generateReport(siteId.value, [], recordId.value)
    if (!res?.report?.trim()) throw new Error('AI 未返回有效报告')
    reportText.value = res.report
  } catch (error: any) { reportError.value = error.message || '报告生成失败，请稍后重试' }
  finally { loading.value = false }
}

function copyReport() {
  uni.setClipboardData({ data: reportText.value, success: () => uni.showToast({ title: '报告已复制', icon: 'success' }), fail: () => uni.showToast({ title: '复制失败', icon: 'none' }) })
}
function backToSites() { uni.redirectTo({ url: '/pages/tour/tour' }) }
</script>

<style scoped>
.report { min-height: 100vh; padding-bottom: 60rpx; background: var(--color-bg); }.report-hero { height: 390rpx; position: relative; overflow: hidden; color: #fffaf0; background: #1d2923; }.report-hero__image { position: absolute; inset: 0; width: 100%; height: 100%; background-size: cover; background-position: 48% center; filter: saturate(.62) sepia(.1); }.report-hero__shade { position: absolute; inset: 0; background: linear-gradient(0deg, rgba(20,27,23,.92), rgba(21,29,24,.27)), linear-gradient(90deg, rgba(20,28,23,.65), transparent); }.report-hero__copy { position: absolute; left: var(--page-gutter); bottom: 48rpx; }.report-hero__copy span { font-size: 17rpx; letter-spacing: 5rpx; color: #e6cc88; }.report-hero h1 { margin: 8rpx 0 5rpx; font: 700 45rpx var(--font-display); }.report-hero p { margin: 0; font-size: 21rpx; color: rgba(255,250,240,.66); letter-spacing: 2rpx; }.report__main { padding: 0 var(--page-gutter); }.report-ticket { position: relative; z-index: 2; display: grid; grid-template-columns: repeat(3,1fr); margin-top: -25rpx; padding: 23rpx; background: #fffaf0; border: 1px solid rgba(72,25,22,.14); box-shadow: 0 12rpx 32rpx rgba(43,31,22,.1); }.report-ticket div { padding: 0 13rpx; border-right: 1px solid rgba(72,25,22,.12); }.report-ticket div:last-child { border: 0; }.report-ticket span,.report-ticket strong { display: block; }.report-ticket span { font-size: 15rpx; color: var(--color-text-muted); }.report-ticket strong { margin-top: 5rpx; font: 700 20rpx var(--font-display); color: var(--color-text); }
.report-loading,.report-error { margin-top: 45rpx; padding: 48rpx 35rpx; text-align: center; background: #fffaf0; border: 1px solid rgba(72,25,22,.13); }.report-loading__seal { display: grid; place-items: center; width: 90rpx; height: 90rpx; margin: 0 auto 22rpx; border: 4rpx double var(--color-green); border-radius: 50%; font: 700 31rpx var(--font-display); color: var(--color-green); animation: seal-pulse 1.8s ease-in-out infinite; }.report-loading h2,.report-error h2 { margin: 0 0 9rpx; font: 700 29rpx var(--font-display); color: var(--color-text); }.report-loading p,.report-error p { margin: 0 auto; max-width: 510rpx; font-size: 20rpx; line-height: 1.6; color: var(--color-text-muted); }.report-loading > div:last-child { height: 3rpx; margin-top: 28rpx; overflow: hidden; background: rgba(49,91,73,.1); }.report-loading i { display: block; width: 38%; height: 100%; background: var(--color-green); animation: report-progress 1.6s ease-in-out infinite; }.report-error > span { display: block; margin-bottom: 7rpx; font-size: 16rpx; letter-spacing: 3rpx; color: var(--color-primary); }.report-error button { margin-top: 24rpx; padding: 17rpx 30rpx; color: white; background: var(--color-primary); border-radius: 2rpx; font-size: 21rpx; }
.report-paper { position: relative; margin-top: 44rpx; padding: 35rpx 32rpx 120rpx; overflow: hidden; background-color: #fffaf0; background-image: linear-gradient(rgba(181,138,63,.035) 1px, transparent 1px), linear-gradient(90deg, rgba(181,138,63,.035) 1px, transparent 1px); background-size: 28rpx 28rpx; border: 1px solid rgba(72,25,22,.15); box-shadow: 8rpx 10rpx 0 rgba(127,33,29,.045); }.report-paper__masthead { display: flex; justify-content: space-between; padding-bottom: 16rpx; border-bottom: 2rpx solid var(--color-text); font-size: 16rpx; letter-spacing: 2rpx; color: var(--color-text-muted); }.report-paper h2 { margin: 32rpx 0 18rpx; text-align: center; font: 700 36rpx var(--font-display); letter-spacing: 3rpx; color: var(--color-text); }.report-paper__rule { display: flex; align-items: center; gap: 13rpx; margin-bottom: 27rpx; color: var(--color-gold); font-size: 15rpx; letter-spacing: 3rpx; }.report-paper__rule i { flex: 1; height: 1px; background: rgba(181,138,63,.3); }.report-paper > p { margin: 0; white-space: pre-wrap; text-align: justify; font: 24rpx/1.95 var(--font-display); color: var(--color-text-secondary); }.report-paper__stamp { position: absolute; right: 34rpx; bottom: 44rpx; display: grid; place-items: center; align-content: center; width: 100rpx; height: 100rpx; border: 4rpx double var(--color-primary); border-radius: 50%; color: var(--color-primary); transform: rotate(-8deg); }.report-paper__stamp strong { font: 700 21rpx/1.15 var(--font-display); text-align: center; }.report-paper__stamp span { margin-top: 3rpx; font-size: 12rpx; }.report-paper__footer { position: absolute; left: 32rpx; right: 155rpx; bottom: 35rpx; padding-top: 12rpx; border-top: 1px dashed rgba(72,25,22,.17); font-size: 15rpx; line-height: 1.45; color: var(--color-text-muted); }.source-note { margin-top: 20rpx; padding: 25rpx; border-left: 5rpx solid var(--color-gold); background: rgba(255,250,240,.7); }.source-note span { font-size: 16rpx; letter-spacing: 3rpx; color: var(--color-gold); }.source-note p { margin: 8rpx 0 0; white-space: pre-wrap; font-size: 20rpx; line-height: 1.7; color: var(--color-text-muted); }.report__actions { display: flex; gap: 15rpx; margin-top: 25rpx; }.report__action { flex: 1; margin: 0; padding: 21rpx 12rpx; border: 1px solid rgba(72,25,22,.18); border-radius: 2rpx; color: var(--color-text); background: #fffaf0; font-size: 21rpx; }.report__action--primary { color: white; background: var(--color-primary); border-color: var(--color-primary); }
@keyframes seal-pulse { 50% { opacity: .55; transform: scale(.96) rotate(-5deg); } } @keyframes report-progress { from { transform: translateX(-110%); } to { transform: translateX(290%); } }
@media (prefers-reduced-motion: reduce) { .report-loading__seal,.report-loading i { animation: none; } }
</style>
