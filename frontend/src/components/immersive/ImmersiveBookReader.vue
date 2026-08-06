<template>
  <div class="reader" :class="[`reader--${book.module}`, { 'is-dragging': dragging, 'is-turning': turning }]">
    <header class="reader-toolbar">
      <button class="tool tool--exit" @click="exitReader"><span>←</span><b>退出</b></button>
      <div class="reader-toolbar__identity"><span>{{ book.module === 'history' ? '党史现场纪事' : '红色山河研学图志' }}</span><b>{{ book.title }}</b></div>
      <div class="reader-toolbar__actions">
        <button class="tool" @click="toggleCaptions"><span>字</span><b>{{ captionsEnabled ? '字幕开' : '字幕关' }}</b></button>
        <button class="tool" @click="toggleSound"><span>{{ soundEnabled ? '♪' : '×' }}</span><b>{{ soundEnabled ? '声音开' : '声音关' }}</b></button>
        <button class="tool" @click="drawerOpen = !drawerOpen"><span>☰</span><b>目录</b></button>
      </div>
    </header>

    <!-- #ifdef H5 -->
    <main
      class="book-stage"
      @pointerdown="onPointerDown"
      @pointermove="onPointerMove"
      @pointerup="onPointerUp"
      @pointercancel="onPointerCancel"
    >
      <div class="book-shadow"></div>
      <div class="book-shell" :style="bookTransform">
        <div class="book-shell__spine"></div>
        <div class="page-under page-under--left"></div><div class="page-under page-under--right"></div>
        <div class="book-page" :class="turnDirection ? `turn-${turnDirection}` : ''">
          <ImmersiveSpreadPage
            :spread="currentSpread"
            :module="book.module"
            :volume-label="book.source_id"
            :discovered="discovered"
            :selected-option="selectedOption"
            :route-hint="routeHint"
            :decision-locked="decisionLocked"
            :route-solved-count="route.solved_count"
            :route-required-count="route.required_count"
            :choosing="choosing"
            :note="note"
            :qa-history="qaHistory"
            :asking="asking"
            :completing="completing"
            :completed="completed"
            :captions-enabled="captionsEnabled"
            :report="report"
            @next="next"
            @discover="discover"
            @choose="choose"
            @ask="ask"
            @update-note="updateNote"
            @complete="complete"
          />
          <div class="page-gloss"></div>
        </div>
      </div>
      <button v-if="canGoBack" class="edge edge--prev" aria-label="上一页" @click.stop="previous"><span>‹</span></button>
      <button v-if="canAdvance" class="edge edge--next" aria-label="下一页" @click.stop="next"><span>›</span></button>
    </main>
    <!-- #endif -->

    <!-- #ifndef H5 -->
    <swiper class="mp-book" :current="currentIndex" :duration="reduceMotion ? 80 : 420" @change="onSwiperChange">
      <swiper-item v-for="spread in book.spreads" :key="spread.id">
        <ImmersiveSpreadPage
          :spread="spread"
          :module="book.module"
          :volume-label="book.source_id"
          :discovered="discovered"
          :selected-option="selectedOption"
          :route-hint="routeHint"
          :decision-locked="decisionLocked"
          :route-solved-count="route.solved_count"
          :route-required-count="route.required_count"
          :choosing="choosing"
          :note="note"
          :qa-history="qaHistory"
          :asking="asking"
          :completing="completing"
          :completed="completed"
          :captions-enabled="captionsEnabled"
          :report="report"
          @next="next"
          @discover="discover"
          @choose="choose"
          @ask="ask"
          @update-note="updateNote"
          @complete="complete"
        />
      </swiper-item>
    </swiper>
    <!-- #endif -->

    <footer class="reader-footer">
      <button :disabled="!canGoBack || navigating" @click="previous">上一幕</button>
      <div class="route-progress">
        <div v-for="item in route.milestones" :key="item.id" :class="{ solved: item.solved, active: currentSpread.scene.milestone === item.key }"><i>{{ item.solved ? '✓' : '○' }}</i><span>{{ item.label }}</span></div>
      </div>
      <button :disabled="!canAdvance || navigating" @click="next">{{ currentSpread.type === 'detour' ? '返回岔路' : '下一幕' }}</button>
    </footer>

    <Transition name="drawer">
      <aside v-if="drawerOpen" class="contents-drawer" @click.self="drawerOpen = false">
        <div>
          <header><span>CONTENTS</span><h2>{{ book.title }}</h2><button @click="drawerOpen = false">×</button></header>
          <button
            v-for="spread in unlockedSpreads"
            :key="spread.id"
            :class="{ active: currentSpreadId === spread.id, visited: route.visited_spread_ids.includes(spread.id) }"
            @click="jumpTo(spread.id)"
          >
            <b>{{ String(spread.order_index + 1).padStart(2, '0') }}</b><span><strong>{{ spread.scene.eyebrow || spread.type }}</strong><small>{{ spread.scene.title }}</small></span><i>{{ route.visited_spread_ids.includes(spread.id) ? '●' : '○' }}</i>
          </button>
          <footer><span>{{ completed ? '本卷已归档' : `证据链 ${route.solved_count}/3` }}</span><button @click="exitReader">保存并离开</button></footer>
        </div>
      </aside>
    </Transition>

    <div v-if="saveState === 'error'" class="save-toast" @click="persist({})">进度保存失败 · 点击重试</div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { immersiveApi, type ImmersiveBook, type ProgressPatch, type SceneHotspot, type SceneOption } from '@/api/immersive'
import ImmersiveSpreadPage from './ImmersiveSpreadPage.vue'

const props = defineProps<{ book: ImmersiveBook }>()
const emit = defineEmits<{ (event: 'progress', value: ImmersiveBook['progress']): void; (event: 'completed'): void }>()

const currentSpreadId = ref(props.book.progress.current_spread_id || props.book.spreads[props.book.progress.current_spread || 0]?.id || props.book.spreads[0].id)
const discovered = ref<string[]>([...(props.book.progress.discovered_hotspots || [])])
const route = ref(props.book.progress.route)
const note = ref(props.book.progress.note || '')
const qaHistory = ref([...(props.book.progress.qa_history || [])])
const soundEnabled = ref(Boolean(props.book.progress.sound_enabled))
const captionsEnabled = ref(props.book.progress.captions_enabled !== false)
const completed = ref(Boolean(props.book.progress.completed))
const report = ref('')
const asking = ref(false)
const completing = ref(false)
const choosing = ref(false)
const navigating = ref(false)
const routeHint = ref('')
const drawerOpen = ref(false)
const dragging = ref(false)
const dragStartX = ref(0)
const dragDelta = ref(0)
const turning = ref(false)
const turnDirection = ref<'next' | 'prev' | ''>('')
const saveState = ref<'idle' | 'saving' | 'error'>('idle')
const reduceMotion = ref(false)
let innerAudio: any = null
let noteTimer: ReturnType<typeof setTimeout> | undefined
let destroyed = false

const currentIndex = computed(() => Math.max(0, props.book.spreads.findIndex(item => item.id === currentSpreadId.value)))
const currentSpread = computed(() => props.book.spreads[currentIndex.value])
const selectedOption = computed(() => route.value.decisions[currentSpreadId.value] || '')
const unlockedSpreads = computed(() => props.book.spreads.filter(item => route.value.unlocked_spread_ids.includes(item.id)))
const canGoBack = computed(() => route.value.visited_spread_ids.length > 1)
const missingDecisionClues = computed(() => (currentSpread.value.scene.required_clues || []).filter(id => !discovered.value.includes(id)))
const decisionLocked = computed(() => currentSpread.value.type === 'decision' && missingDecisionClues.value.length > 0)
const canAdvance = computed(() => currentSpread.value.type !== 'ending' && currentSpread.value.type !== 'decision')
const bookTransform = computed(() => ({ '--drag-angle': `${Math.max(-12, Math.min(12, dragDelta.value / 24))}deg` }))

onMounted(() => {
  // #ifdef H5
  reduceMotion.value = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches || false
  // #endif
  preloadAround(currentIndex.value)
  playCurrentAudio()
})

onBeforeUnmount(() => {
  destroyed = true
  if (noteTimer) clearTimeout(noteTimer)
  stopAudio()
  stopSpeech()
})

watch(currentSpreadId, () => {
  const index = currentIndex.value
  preloadAround(index)
  playCurrentAudio()
})

function applyProgress(value: ImmersiveBook['progress'], syncCurrent = true) {
  route.value = value.route
  discovered.value = [...value.discovered_hotspots]
  if (syncCurrent && value.current_spread_id) currentSpreadId.value = value.current_spread_id
  emit('progress', value)
}
function animateTo(targetId: string, direction: 'next' | 'prev') {
  if (turning.value || targetId === currentSpreadId.value) return
  stopSpeech()
  turnDirection.value = direction
  if (reduceMotion.value) { currentSpreadId.value = targetId; turnDirection.value = ''; return }
  turning.value = true
  setTimeout(() => { currentSpreadId.value = targetId }, 180)
  setTimeout(() => { turning.value = false; turnDirection.value = '' }, 520)
}
async function navigate(direction: 'next' | 'back' | 'jump', target?: string) {
  if (navigating.value || turning.value) return
  navigating.value = true
  try {
    const result = await immersiveApi.advance(props.book.id, { from_spread_id: currentSpreadId.value, direction, target_spread_id: target })
    const before = currentSpreadId.value
    const oldIndex = currentIndex.value
    applyProgress(result.progress, false)
    animateTo(result.spread.id, direction === 'back' ? 'prev' : result.spread.order_index >= oldIndex ? 'next' : 'prev')
    if (before !== result.spread.id) routeHint.value = ''
  } catch (error: any) {
    uni.showToast({ title: error.message || '暂时无法继续', icon: 'none' })
  } finally { navigating.value = false }
}
function next() { if (canAdvance.value) navigate('next') }
function previous() { if (canGoBack.value) navigate('back') }
function jumpTo(spreadId: string) { drawerOpen.value = false; if (spreadId !== currentSpreadId.value) navigate('jump', spreadId) }

function onPointerDown(event: PointerEvent) {
  const target = event.target as HTMLElement
  if (target.closest('button,input,textarea,a,.clue-sheet,.archive-sheet,.notebook-sheet,.inquiry-sheet')) return
  dragging.value = true; dragStartX.value = event.clientX; dragDelta.value = 0
  ;(event.currentTarget as HTMLElement)?.setPointerCapture?.(event.pointerId)
}
function onPointerMove(event: PointerEvent) { if (dragging.value) dragDelta.value = event.clientX - dragStartX.value }
function onPointerUp() {
  if (!dragging.value) return
  if (dragDelta.value < -70) next()
  else if (dragDelta.value > 70) previous()
  dragging.value = false; dragDelta.value = 0
}
function onPointerCancel() { dragging.value = false; dragDelta.value = 0 }
function onSwiperChange(event: any) {
  const spread = props.book.spreads[Number(event.detail?.current || 0)]
  if (spread?.id && spread.id !== currentSpreadId.value && route.value.unlocked_spread_ids.includes(spread.id)) jumpTo(spread.id)
}

async function persist(patch: ProgressPatch) {
  if (destroyed) return
  saveState.value = 'saving'
  try {
    const value = await immersiveApi.updateProgress(props.book.id, patch)
    if (!destroyed) { saveState.value = 'idle'; applyProgress(value) }
  } catch { if (!destroyed) saveState.value = 'error' }
}

function discover(hotspot: SceneHotspot) {
  if (!discovered.value.includes(hotspot.id)) {
    discovered.value.push(hotspot.id)
    persist({ discovered_hotspot: hotspot.id })
  }
}
async function choose(option: SceneOption) {
  if (choosing.value) return
  choosing.value = true
  try {
    const result = await immersiveApi.choose(props.book.id, {
      decision_spread_id: currentSpreadId.value,
      option_id: option.id,
      submission_id: `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`,
    })
    applyProgress(result.progress, false)
    routeHint.value = result.result === 'detour' ? result.hint : ''
    animateTo(result.next_spread_id, 'next')
    if (result.result === 'correct') uni.showToast({ title: '证据链成立，路线已解锁', icon: 'none' })
  } catch (error: any) {
    uni.showToast({ title: error.message || '路线选择未保存', icon: 'none' })
  } finally { choosing.value = false }
}
function updateNote(value: string) {
  note.value = value
  if (noteTimer) clearTimeout(noteTimer)
  noteTimer = setTimeout(() => persist({ note: value }), 650)
}
async function ask(question: string) {
  if (asking.value) return
  asking.value = true
  try {
    const result = await immersiveApi.ask(props.book.id, question, currentSpread.value.id)
    qaHistory.value = result.qa_history || [...qaHistory.value, { q: question, a: result.answer }]
  } catch (error: any) {
    uni.showToast({ title: error.message || '史官暂时无法回答', icon: 'none' })
  } finally { asking.value = false }
}
async function complete() {
  if (completing.value || completed.value) return
  if (noteTimer) { clearTimeout(noteTimer); await persist({ note: note.value }) }
  completing.value = true
  try {
    const result = await immersiveApi.complete(props.book.id)
    completed.value = result.completed
    report.value = result.report || ''
    if (completed.value) { emit('completed'); uni.showToast({ title: result.already_completed ? '本卷已归档' : `归档成功${result.points ? ` +${result.points}积分` : ''}`, icon: 'none' }) }
  } catch (error: any) { uni.showToast({ title: error.message || '暂时无法归档', icon: 'none', duration: 3000 }) }
  finally { completing.value = false }
}

function toggleCaptions() { captionsEnabled.value = !captionsEnabled.value; persist({ captions_enabled: captionsEnabled.value }) }
function toggleSound() { soundEnabled.value = !soundEnabled.value; persist({ sound_enabled: soundEnabled.value }); soundEnabled.value ? playCurrentAudio() : (stopAudio(), stopSpeech()) }
function playCurrentAudio() {
  stopAudio(); stopSpeech()
  if (!soundEnabled.value) return
  const spread = currentSpread.value
  if (spread.audio_url) {
    try {
      innerAudio = uni.createInnerAudioContext()
      innerAudio.autoplay = true
      innerAudio.loop = spread.type === 'cinematic'
      innerAudio.src = spread.audio_url
      innerAudio.onError?.(() => { stopAudio(); speakNarration(spread.narration) })
      innerAudio.play()
      return
    } catch { /* fall through to narration */ }
  }
  speakNarration(spread.narration)
}
function stopAudio() { if (innerAudio) { try { innerAudio.stop(); innerAudio.destroy() } catch {} innerAudio = null } }
function speakNarration(text: string) {
  if (!text) return
  // #ifdef H5
  if ('speechSynthesis' in window) { const utterance = new SpeechSynthesisUtterance(text); utterance.lang = 'zh-CN'; utterance.rate = .88; window.speechSynthesis.speak(utterance) }
  // #endif
}
function stopSpeech() {
  // #ifdef H5
  if ('speechSynthesis' in window) window.speechSynthesis.cancel()
  // #endif
}
function preloadAround(index: number) {
  // #ifdef H5
  for (const spread of props.book.spreads.slice(Math.max(0, index - 1), Math.min(props.book.spreads.length, index + 3))) {
    if (spread.image_url) { const image = new Image(); image.src = spread.image_url }
  }
  // #endif
}
function exitReader() {
  if (noteTimer) { clearTimeout(noteTimer); persist({ note: note.value }) }
  stopAudio(); stopSpeech(); uni.navigateBack()
}
</script>

<style scoped>
.reader { --toolbar-height:64px; --footer-height:54px; position:fixed; z-index:99; inset:0; width:100vw; height:100vh; overflow:hidden; color:#f7edd7; background:#101210; font-family:var(--font-body); user-select:none; }
.reader::before { content:''; position:absolute; inset:0; opacity:.4; background:radial-gradient(circle at 50% 45%,#4a3328,transparent 44%),linear-gradient(120deg,#0d1110,#251d18 54%,#0d0e0d); }
.reader--tour::before { background:radial-gradient(circle at 50% 45%,#33483a,transparent 44%),linear-gradient(120deg,#0c1110,#1f2c25 54%,#0d0f0e); }
.reader-toolbar { position:absolute; z-index:40; top:0; left:0; right:0; height:var(--toolbar-height); display:grid; grid-template-columns:1fr auto 1fr; align-items:center; padding:0 25px; box-sizing:border-box; border-bottom:1px solid rgba(241,220,174,.11); background:linear-gradient(rgba(10,12,10,.83),rgba(10,11,10,.38)); backdrop-filter:blur(12px); }
.reader-toolbar__identity { text-align:center; line-height:1.2; }.reader-toolbar__identity span,.reader-toolbar__identity b { display:block; }.reader-toolbar__identity span { font-size:9px; letter-spacing:4px; color:#b99a5f; }.reader-toolbar__identity b { margin-top:4px; font:700 16px var(--font-display); letter-spacing:3px; }
.reader-toolbar__actions { justify-self:end; display:flex; gap:18px; }.tool { display:flex; align-items:center; gap:7px; color:rgba(255,244,219,.64); }.tool span { display:grid; place-items:center; width:27px; height:27px; border:1px solid rgba(232,205,146,.25); border-radius:50%; color:#e1bf77; font:14px var(--font-display); }.tool b { font-size:10px; font-weight:400; letter-spacing:1px; }.tool--exit { justify-self:start; }
.book-stage { position:absolute; top:var(--toolbar-height); bottom:var(--footer-height); left:0; right:0; display:grid; place-items:center; perspective:2200px; touch-action:pan-y; cursor:grab; }.is-dragging .book-stage { cursor:grabbing; }
.book-shadow { position:absolute; width:min(86vw,1280px); height:72%; bottom:3%; border-radius:50%; background:rgba(0,0,0,.55); filter:blur(45px); transform:scaleY(.18); }
.book-shell { --drag-angle:0deg; position:relative; width:min(88vw,1280px); aspect-ratio:1.78; max-height:82vh; background:#2d2118; box-shadow:0 36px 90px rgba(0,0,0,.66),0 0 0 8px #3b2a1e,0 0 0 10px rgba(211,169,91,.18); transform:rotateY(var(--drag-angle)); transform-style:preserve-3d; transition:transform .18s; }
.book-shell::before,.book-shell::after { content:''; position:absolute; z-index:5; top:0; bottom:0; width:23px; pointer-events:none; }.book-shell::before { left:0; background:linear-gradient(90deg,rgba(0,0,0,.42),transparent); }.book-shell::after { right:0; background:linear-gradient(-90deg,rgba(0,0,0,.42),transparent); }
.book-shell__spine { position:absolute; z-index:18; top:0; bottom:0; left:50%; width:28px; transform:translateX(-50%); pointer-events:none; background:linear-gradient(90deg,transparent,rgba(0,0,0,.44) 42%,rgba(255,239,201,.13) 50%,rgba(0,0,0,.36) 58%,transparent); mix-blend-mode:multiply; }
.page-under { position:absolute; z-index:0; top:7px; bottom:7px; width:14px; background:repeating-linear-gradient(0deg,#d8c7a5 0 2px,#a99470 3px 4px); }.page-under--left { left:-9px; transform:rotateY(1deg); }.page-under--right { right:-9px; transform:rotateY(-1deg); }
.book-page { position:absolute; z-index:3; inset:0; overflow:hidden; background:#17140f; transform-origin:center; transform-style:preserve-3d; backface-visibility:hidden; }.book-page::after { content:''; position:absolute; z-index:20; inset:0; pointer-events:none; opacity:0; background:linear-gradient(90deg,transparent 35%,rgba(0,0,0,.7)); }
.is-turning .book-page.turn-next { animation:pageNext .52s cubic-bezier(.65,0,.25,1); }.is-turning .book-page.turn-prev { animation:pagePrev .52s cubic-bezier(.65,0,.25,1); }.page-gloss { position:absolute; z-index:19; inset:0; pointer-events:none; background:linear-gradient(105deg,transparent 38%,rgba(255,255,255,.08) 49%,transparent 59%); mix-blend-mode:screen; }
.edge { position:absolute; z-index:25; top:10%; bottom:10%; width:7%; color:rgba(250,232,192,.42); opacity:.25; transition:opacity .2s,background .2s; }.edge:hover { opacity:1; background:linear-gradient(90deg,rgba(210,168,88,.07),transparent); }.edge span { font:54px/1 var(--font-display); text-shadow:0 3px 13px #000; }.edge--prev { left:0; }.edge--next { right:0; }.edge--next:hover { background:linear-gradient(-90deg,rgba(210,168,88,.07),transparent); }
.reader-footer { position:absolute; z-index:40; left:0; right:0; bottom:0; height:var(--footer-height); display:grid; grid-template-columns:100px minmax(180px,440px) 100px; justify-content:center; align-items:center; gap:28px; border-top:1px solid rgba(241,220,174,.1); background:rgba(8,10,9,.77); backdrop-filter:blur(12px); }.reader-footer>button { color:rgba(255,241,211,.57); font-size:11px; letter-spacing:2px; }.reader-footer>button:disabled { opacity:.18; }
.route-progress { display:grid; grid-template-columns:repeat(3,1fr); gap:8px; }.route-progress>div { display:flex; align-items:center; justify-content:center; gap:6px; padding:5px 8px; border-bottom:1px solid rgba(255,255,255,.14); color:rgba(255,241,211,.42); font-size:10px; letter-spacing:1px; }.route-progress i { display:grid; place-items:center; width:15px; height:15px; border:1px solid rgba(218,181,103,.3); border-radius:50%; color:#b99550; font:9px var(--font-body); }.route-progress .active { color:#edcf91; border-color:#c39b4d; }.route-progress .solved { color:#d5e3bf; border-color:rgba(164,197,139,.55); }.route-progress .solved i { color:#d5e3bf; border-color:#8da875; }
.contents-drawer { position:absolute; z-index:80; inset:0; display:flex; justify-content:flex-end; background:rgba(4,5,4,.62); backdrop-filter:blur(4px); }.contents-drawer>div { width:min(400px,90vw); height:100%; overflow:auto; box-sizing:border-box; padding:35px 31px; color:#34271c; background:#e7d8b9; box-shadow:-25px 0 70px rgba(0,0,0,.44); }.contents-drawer header { position:relative; padding-bottom:24px; border-bottom:1px solid rgba(83,58,32,.2); }.contents-drawer header span { color:#987039; font-size:9px; letter-spacing:5px; }.contents-drawer header h2 { margin:6px 0 0; font:700 28px var(--font-display); }.contents-drawer header>button { position:absolute; right:0; top:-8px; color:#7e2d26; font-size:31px; }.contents-drawer>div>button { width:100%; display:grid; grid-template-columns:38px 1fr 18px; align-items:center; gap:12px; padding:15px 3px; border-bottom:1px solid rgba(83,58,32,.12); color:#7e6d59; text-align:left; }.contents-drawer>div>button>b { font:700 13px var(--font-display); color:#a58a60; }.contents-drawer>div>button span strong,.contents-drawer>div>button span small { display:block; }.contents-drawer>div>button span strong { color:#3e3022; font:700 14px var(--font-display); }.contents-drawer>div>button span small { margin-top:2px; font-size:11px; }.contents-drawer>div>button i { color:#b6a283; font-style:normal; }.contents-drawer>div>button.active { color:#7b2a23; background:rgba(122,43,36,.06); }.contents-drawer>div>button.active b,.contents-drawer>div>button.active i { color:#7b2a23; }.contents-drawer>div>footer { display:flex; justify-content:space-between; align-items:center; margin-top:26px; font-size:11px; color:#76634d; }.contents-drawer>div>footer button { padding:10px 13px; color:#f6ead1; background:#752b25; }
.save-toast { position:absolute; z-index:90; left:50%; bottom:70px; transform:translateX(-50%); padding:9px 16px; color:#f5e8cf; background:#7d2b25; box-shadow:0 7px 25px rgba(0,0,0,.25); font-size:11px; }
.drawer-enter-active,.drawer-leave-active { transition:opacity .25s; }.drawer-enter-active>div,.drawer-leave-active>div { transition:transform .35s cubic-bezier(.2,.8,.2,1); }.drawer-enter-from,.drawer-leave-to { opacity:0; }.drawer-enter-from>div,.drawer-leave-to>div { transform:translateX(100%); }
.mp-book { position:absolute; top:var(--toolbar-height); bottom:var(--footer-height); left:0; right:0; height:auto; }
@keyframes pageNext { 0%{transform:perspective(1800px) rotateY(0);filter:brightness(1)} 48%{transform:perspective(1800px) rotateY(-12deg) scale(.985);filter:brightness(.55)} 51%{opacity:.3} 52%{transform:perspective(1800px) rotateY(10deg);opacity:.3} 100%{transform:perspective(1800px) rotateY(0);opacity:1;filter:brightness(1)} }
@keyframes pagePrev { 0%{transform:perspective(1800px) rotateY(0);filter:brightness(1)} 48%{transform:perspective(1800px) rotateY(12deg) scale(.985);filter:brightness(.55)} 51%{opacity:.3} 52%{transform:perspective(1800px) rotateY(-10deg);opacity:.3} 100%{transform:perspective(1800px) rotateY(0);opacity:1;filter:brightness(1)} }
/* #ifndef H5 */
@media (max-width: 700px) {
  .reader { --toolbar-height:58px; --footer-height:52px; }.reader-toolbar { grid-template-columns:64px 1fr 112px; padding:0 12px; }.reader-toolbar__identity span { display:none; }.reader-toolbar__identity b { font-size:14px; letter-spacing:2px; }.reader-toolbar__actions { gap:5px; }.tool { gap:0; }.tool span { width:26px;height:26px; }.tool b { display:none; }.tool--exit b { display:block;margin-left:6px; }.book-stage { align-items:center; }.book-shell { width:100vw; height:calc(100vh - var(--toolbar-height) - var(--footer-height)); max-height:none; aspect-ratio:auto; box-shadow:none; }.book-shell__spine,.page-under { display:none; }.edge { width:12%; }.edge span { font-size:40px; }.reader-footer { grid-template-columns:62px minmax(145px,1fr) 62px; gap:8px; padding:0 10px; }.reader-footer>button { font-size:9px; }.route-progress { gap:3px; }.route-progress>div { gap:3px; padding:4px 2px; font-size:8px; letter-spacing:0; }.route-progress i { width:12px; height:12px; font-size:7px; }.book-shadow { display:none; }
}
/* #endif */
/* #ifdef H5 */
@container (max-width: 700px) {
  .reader { --toolbar-height:58px; --footer-height:52px; }.reader-toolbar { grid-template-columns:64px 1fr 112px; padding:0 12px; }.reader-toolbar__identity span { display:none; }.reader-toolbar__identity b { font-size:14px; letter-spacing:2px; }.reader-toolbar__actions { gap:5px; }.tool { gap:0; }.tool span { width:26px;height:26px; }.tool b { display:none; }.tool--exit b { display:block;margin-left:6px; }.book-stage { align-items:center; }.book-shell { width:100vw; height:calc(100vh - var(--toolbar-height) - var(--footer-height)); max-height:none; aspect-ratio:auto; box-shadow:none; }.book-shell__spine,.page-under { display:none; }.edge { width:12%; }.edge span { font-size:40px; }.reader-footer { grid-template-columns:62px minmax(145px,1fr) 62px; gap:8px; padding:0 10px; }.reader-footer>button { font-size:9px; }.route-progress { gap:3px; }.route-progress>div { gap:3px; padding:4px 2px; font-size:8px; letter-spacing:0; }.route-progress i { width:12px; height:12px; font-size:7px; }.book-shadow { display:none; }
}
/* #endif */
@media (prefers-reduced-motion:reduce) { .book-shell,.book-page,.contents-drawer>div { transition:none!important; animation:none!important; } }
</style>
