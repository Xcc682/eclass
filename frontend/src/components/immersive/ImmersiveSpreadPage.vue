<template>
  <div class="spread" :class="[`spread--${spread.type}`, `spread--${module}`, { 'is-cover': spread.type === 'cover' }]">
    <div
      class="spread__scene"
      :class="{ 'spread__scene--missing': imageFailed }"
      :style="sceneStyle"
    ></div>
    <div class="spread__veil"></div>
    <div v-if="spread.scene.particles" class="particles" :class="`particles--${spread.scene.particles}`"></div>
    <div class="paper-grain"></div>

    <button class="reconstruction-badge" @click.stop="boundaryOpen = !boundaryOpen">
      <i></i>{{ spread.scene.contemporary ? '当代场景示意' : '情景复原' }}<b>?</b>
    </button>
    <Transition name="clue">
      <aside v-if="boundaryOpen" class="reconstruction-note" @click.stop>
        <button @click.stop="boundaryOpen = false">×</button>
        <span>史实边界</span>
        <p v-if="spread.scene.contemporary">本页用于呈现今天的参访环境。地点与遗存依据公开资料，具体镜头为场景示意。</p>
        <p v-else>本页依据权威资料复原时间、地点与事件环境；人物形象和镜头调度用于叙事，不作为历史照片或人物原话。</p>
        <small>本卷史料来源可在“史料插页”中查看。</small>
      </aside>
    </Transition>
    <button v-if="imageFailed" class="media-retry" @click.stop="checkImage">画面加载失败 · 重试</button>

    <section v-if="spread.type === 'cover'" class="cover-copy">
      <span>{{ spread.scene.eyebrow }}</span>
      <div class="cover-copy__rule"></div>
      <h1 class="cover-copy__title">{{ spread.scene.title }}</h1>
      <p>{{ spread.scene.caption }}</p>
      <div v-if="spread.scene.timeline?.length" class="cover-timeline">
        <article v-for="(event, index) in spread.scene.timeline" :key="`${event.date}-${index}`">
          <i>{{ String(index + 1).padStart(2, '0') }}</i><span>{{ event.date }}</span><b>{{ event.title }}</b>
        </article>
      </div>
      <button @click="$emit('next')"><b>第 {{ volumeLabel }} 卷</b><em>{{ spread.scene.cta || '翻开书卷' }} →</em></button>
    </section>

    <section v-else-if="spread.type === 'exploration'" class="exploration-copy">
      <header class="scene-heading">
        <div v-if="spread.scene.event" class="event-meta"><b>{{ spread.scene.event.date }}</b><i></i><span>{{ spread.scene.event.place }}</span></div>
        <span>{{ spread.scene.eyebrow }}<template v-if="spread.scene.event"> · {{ spread.scene.event.title }}</template></span><h2>{{ spread.scene.title }}</h2>
        <p>{{ spread.scene.event?.summary || spread.scene.caption }}</p>
        <small>{{ spread.scene.caption }}</small>
      </header>
      <button
        v-for="(hotspot, index) in spread.scene.hotspots || []"
        :key="hotspot.id"
        class="hotspot"
        :class="{ discovered: isDiscovered(hotspot.id), active: activeHotspot?.id === hotspot.id }"
        :style="{ left: `${hotspot.x}%`, top: `${hotspot.y}%` }"
        @click.stop="openHotspot(hotspot)"
      >
        <i></i><span>{{ String(index + 1).padStart(2, '0') }}</span>
      </button>
      <Transition name="clue">
        <article v-if="activeHotspot" class="clue-sheet">
          <button class="clue-sheet__close" @click.stop="activeHotspot = null">×</button>
          <span>现场证据 · {{ activeHotspot.id.replace('clue-', '').padStart(2, '0') }}</span>
          <h3>{{ activeHotspot.title }}</h3>
          <p>{{ activeHotspot.content }}</p>
          <small>已收入本卷线索册</small>
        </article>
      </Transition>
      <div class="exploration-progress">
        <span>{{ discoveredCount }}/{{ spread.scene.hotspots?.length || 0 }} 条线索</span>
        <i><b :style="{ width: `${discoveredPercent}%` }"></b></i>
      </div>
    </section>

    <section v-else-if="spread.type === 'decision'" class="decision-copy">
      <div v-if="spread.scene.event" class="event-meta"><b>{{ spread.scene.event.date }}</b><i></i><span>{{ spread.scene.event.place }}</span></div>
      <span>{{ spread.scene.eyebrow }}<template v-if="spread.scene.event"> · {{ spread.scene.event.title }}</template></span>
      <h2>{{ spread.scene.title }}</h2>
      <div v-if="spread.scene.event" class="event-brief"><p>{{ spread.scene.event.summary }}</p><small>这意味着 · {{ spread.scene.event.meaning }}</small></div>
      <p>{{ spread.narration }}</p>
      <div class="decision-list">
        <button
          v-for="(option, index) in spread.scene.options || []"
          :key="option.id"
          :class="{ selected: selectedOption === option.id }"
          :disabled="decisionLocked || choosing"
          @click.stop="choose(option)"
        >
          <b>{{ String.fromCharCode(65 + index) }}</b><span>{{ option.label }}</span><i>→</i>
        </button>
      </div>
      <Transition name="clue"><div v-if="decisionLocked" class="choice-feedback">判断尚未解锁：请返回现场找齐标记线索。</div></Transition>
      <small>{{ choosing ? '正在核对证据链…' : spread.scene.caption }}</small>
    </section>

    <section v-else-if="spread.type === 'detour'" class="detour-copy">
      <span>{{ spread.scene.eyebrow }}</span>
      <h2>{{ spread.scene.title }}</h2>
      <p>{{ spread.scene.detour_body || spread.narration }}</p>
      <div class="detour-copy__break"><i></i><b>线索无法闭合</b><i></i></div>
      <aside v-if="routeHint"><strong>史料提示</strong><span>{{ routeHint }}</span></aside>
      <button @click.stop="$emit('next')">{{ spread.scene.return_label || '回到岔路口' }} ↩</button>
    </section>

    <section v-else-if="spread.type === 'archive'" class="archive-sheet">
      <div class="archive-sheet__mark">ARCHIVE<br>{{ volumeLabel }}</div>
      <span>{{ spread.scene.eyebrow }}</span>
      <h2>{{ spread.scene.title }}</h2>
      <blockquote>{{ spread.scene.archive_excerpt || spread.narration }}</blockquote>
      <p v-if="spread.scene.event" class="archive-conclusion"><b>{{ spread.scene.event.title }}</b> · {{ spread.scene.event.meaning }}</p>
      <footer>
        <b>{{ spread.scene.caption }}</b>
        <a v-if="spread.sources?.[0]?.url" :href="spread.sources[0].url" target="_blank" rel="noreferrer">查看权威来源 ↗</a>
      </footer>
    </section>

    <section v-else-if="spread.type === 'reflection' && spread.scene.note_placeholder" class="notebook-sheet">
      <div v-if="spread.scene.event" class="paper-context"><b>{{ spread.scene.event.date }}</b><span>{{ spread.scene.event.title }}</span></div>
      <span>{{ spread.scene.eyebrow }}</span>
      <h2>{{ spread.scene.title }}</h2>
      <p>{{ spread.narration }}</p>
      <textarea
        :value="note"
        maxlength="5000"
        :placeholder="spread.scene.note_placeholder"
        @input="$emit('update-note', ($event.target as HTMLTextAreaElement).value)"
      />
      <footer><span>{{ note.length }} / 5000</span><b>{{ note.length >= 20 ? '手记已达到归档要求' : '写满 20 字即可归档' }}</b></footer>
    </section>

    <section v-else-if="spread.type === 'reflection'" class="inquiry-sheet">
      <div v-if="spread.scene.event" class="paper-context"><b>{{ spread.scene.event.date }}</b><span>{{ spread.scene.event.title }}</span></div>
      <span>{{ spread.scene.eyebrow }}</span>
      <h2>{{ spread.scene.title }}</h2>
      <p>{{ spread.narration }}</p>
      <div v-if="qaHistory.length" class="qa-log">
        <article v-for="(row, index) in qaHistory.slice(-2)" :key="index"><b>问</b><strong>{{ row.q }}</strong><p>{{ row.a }}</p></article>
      </div>
      <div class="ask-row">
        <input v-model="question" :disabled="asking" maxlength="1000" :placeholder="spread.scene.prompt || '向随行史官追问…'" @keyup.enter="submitQuestion" />
        <button :disabled="asking || !question.trim()" @click.stop="submitQuestion">{{ asking ? '查阅中' : '追问' }}</button>
      </div>
      <small>线索不足时，史官会带你回到本卷史料。</small>
    </section>

    <section v-else-if="spread.type === 'ending'" class="ending-copy">
      <div class="ending-copy__seal" :class="{ stamped: completed }"><span>{{ completed ? '已归档' : '待归档' }}</span><b>{{ module === 'history' ? '纪事' : '研学' }}</b></div>
      <span>{{ spread.scene.eyebrow }}</span>
      <h2>{{ spread.scene.title }}</h2>
      <p>{{ spread.narration }}</p>
      <div v-if="module === 'history' && spread.scene.prompt" class="ending-inquiry">
        <div v-if="lastAnswer" class="ending-inquiry__answer"><b>史官答</b><span>{{ lastAnswer.a }}</span></div>
        <div class="ask-row">
          <input v-model="question" :disabled="asking" maxlength="1000" :placeholder="spread.scene.prompt" @keyup.enter="submitQuestion" />
          <button :disabled="asking || !question.trim()" @click.stop="submitQuestion">{{ asking ? '查阅中' : '追问' }}</button>
        </div>
      </div>
      <div class="ending-checks">
        <span :class="{ done: hasClue }">{{ hasClue ? '✓' : '○' }} {{ module === 'history' ? '现场寻证' : '现场寻迹' }}</span>
        <span :class="{ done: hasRoute }">{{ hasRoute ? '✓' : '○' }} 三段证据路线</span>
        <span v-if="module === 'tour'" :class="{ done: hasTourReflection }">{{ hasTourReflection ? '✓' : '○' }} 追问或手记</span>
      </div>
      <div v-if="report" class="report-preview"><strong>本次研学报告</strong><p>{{ report }}</p></div>
      <button class="complete-button" :disabled="completing || completed || !canComplete" @click.stop="$emit('complete')">
        {{ completed ? '本卷已归档' : completing ? '正在整理档案…' : spread.scene.cta || '完成本卷' }}
      </button>
      <small v-if="!completed">{{ completionHint }}</small>
    </section>

    <section v-else class="cinematic-copy" :class="{ 'cinematic-copy--dialogue': spread.type === 'dialogue' }">
      <div v-if="spread.scene.event" class="event-meta"><b>{{ spread.scene.event.date }}</b><i></i><span>{{ spread.scene.event.place }}</span></div>
      <span>{{ spread.scene.eyebrow }}<template v-if="spread.type === 'dialogue' && spread.scene.event"> · {{ spread.scene.event.title }}</template></span>
      <h2>{{ spread.type === 'dialogue' ? spread.scene.title : (spread.scene.event?.title || spread.scene.title) }}</h2>
      <p v-if="captionsEnabled">{{ spread.type === 'dialogue' ? spread.narration : (spread.scene.event?.summary || spread.narration) }}</p>
      <small v-if="captionsEnabled && spread.scene.event" class="event-meaning">这意味着 · {{ spread.scene.event.meaning }}</small>
      <blockquote v-if="spread.scene.dialogue">{{ spread.scene.dialogue }}</blockquote>
      <small>{{ spread.scene.caption }}</small>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { ImmersiveModule, ImmersiveProgress, ImmersiveSpread, SceneHotspot, SceneOption } from '@/api/immersive'

const props = defineProps<{
  spread: ImmersiveSpread
  module: ImmersiveModule
  volumeLabel: string
  discovered: string[]
  selectedOption?: string
  routeHint?: string
  decisionLocked?: boolean
  choosing?: boolean
  routeSolvedCount: number
  routeRequiredCount: number
  note: string
  qaHistory: ImmersiveProgress['qa_history']
  asking: boolean
  completing: boolean
  completed: boolean
  captionsEnabled: boolean
  report?: string
}>()

const emit = defineEmits<{
  (event: 'next'): void
  (event: 'discover', hotspot: SceneHotspot): void
  (event: 'choose', option: SceneOption): void
  (event: 'ask', question: string): void
  (event: 'update-note', note: string): void
  (event: 'complete'): void
}>()

const activeHotspot = ref<SceneHotspot | null>(null)
const question = ref('')
const imageFailed = ref(false)
const boundaryOpen = ref(false)

const sceneStyle = computed(() => ({
  backgroundImage: imageFailed.value ? '' : `url(${props.spread.image_url})`,
  backgroundPosition: props.spread.scene.position || 'center',
  transform: `scale(${props.spread.scene.scale || 1})`,
}))
const discoveredCount = computed(() => (props.spread.scene.hotspots || []).filter(item => props.discovered.includes(item.id)).length)
const discoveredPercent = computed(() => {
  const total = props.spread.scene.hotspots?.length || 1
  return Math.round(discoveredCount.value / total * 100)
})
const hasClue = computed(() => props.discovered.length > 0)
const hasRoute = computed(() => props.routeRequiredCount > 0 && props.routeSolvedCount >= props.routeRequiredCount)
const hasTourReflection = computed(() => props.note.trim().length >= 20 || props.qaHistory.length > 0)
const canComplete = computed(() => hasClue.value && hasRoute.value && (props.module === 'history' || hasTourReflection.value))
const completionHint = computed(() => {
  if (canComplete.value) return '本卷已具备归档条件；积分仅发放一次。'
  if (!hasRoute.value) return `请先完成路线、证据与判断（${props.routeSolvedCount}/${props.routeRequiredCount}）。`
  if (props.module === 'history') return '请返回目录，完成仍标记为 ○ 的现场寻证。'
  return '请完成现场寻迹，并提交一次追问或手记。'
})
const lastAnswer = computed(() => props.qaHistory.length ? props.qaHistory[props.qaHistory.length - 1] : null)

watch(() => props.spread.id, () => {
  activeHotspot.value = null
  question.value = ''
  imageFailed.value = false
  boundaryOpen.value = false
})
watch(() => props.spread.image_url, checkImage, { immediate: true })

function checkImage() {
  imageFailed.value = false
  if (!props.spread.image_url) { imageFailed.value = true; return }
  // #ifdef H5
  const probe = new Image()
  probe.onload = () => { imageFailed.value = false }
  probe.onerror = () => { imageFailed.value = true }
  probe.src = props.spread.image_url
  // #endif
  // #ifndef H5
  uni.getImageInfo({ src: props.spread.image_url, success: () => { imageFailed.value = false }, fail: () => { imageFailed.value = true } })
  // #endif
}

function isDiscovered(id: string) { return props.discovered.includes(id) }
function openHotspot(hotspot: SceneHotspot) {
  activeHotspot.value = hotspot
  emit('discover', hotspot)
}
function choose(option: SceneOption) {
  if (props.decisionLocked || props.choosing) return
  emit('choose', option)
}
function submitQuestion() {
  const value = question.value.trim()
  if (!value || props.asking) return
  question.value = ''
  emit('ask', value)
}
</script>

<style scoped>
.spread { position: relative; width: 100%; height: 100%; overflow: hidden; color: #f8f0df; background: #1b1712; isolation: isolate; }
.spread__scene,.spread__veil,.paper-grain,.particles { position: absolute; inset: 0; }
.spread__scene { z-index: 0; background-color: #2e2921; background-size: cover; transition: transform 9s ease-out, filter .5s; filter: saturate(.75) contrast(1.04) sepia(.06); }
.spread__scene--missing { background: radial-gradient(circle at 62% 32%, #796b52, transparent 32%), linear-gradient(135deg,#25241f,#53382c 55%,#111917); }
.spread__veil { z-index: 1; background: linear-gradient(90deg, rgba(8,9,8,.78), rgba(12,13,11,.12) 55%, rgba(8,8,7,.4)), linear-gradient(0deg, rgba(6,7,6,.83), transparent 56%); }
.spread--tour .spread__veil { background: linear-gradient(90deg, rgba(11,16,13,.72), rgba(12,15,13,.08) 60%), linear-gradient(0deg, rgba(7,12,9,.82), transparent 58%); }
.paper-grain { z-index: 6; opacity: .12; pointer-events: none; mix-blend-mode: screen; background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 180 180' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='.34'/%3E%3C/svg%3E"); }
.spread > section { z-index: 3; }
.reconstruction-badge { position: absolute; z-index: 8; top: 76rpx; right: 28rpx; display: flex; align-items: center; gap: 8rpx; padding: 9rpx 11rpx; border: 1px solid rgba(239,214,159,.26); background: rgba(14,15,13,.42); backdrop-filter: blur(10px); color: rgba(255,244,219,.7); font-size: 15rpx; letter-spacing: 1rpx; }
.reconstruction-badge i { width: 8rpx; height: 8rpx; border-radius: 50%; background: #d9b66b; box-shadow: 0 0 12rpx #d9b66b; }
.reconstruction-badge b { display:grid; place-items:center; width:20rpx; height:20rpx; border:1px solid rgba(242,218,164,.38); border-radius:50%; font:12rpx var(--font-display); }
.reconstruction-note { position:absolute; z-index:14; top:118rpx; right:28rpx; width:min(440rpx,78%); padding:25rpx 28rpx; box-sizing:border-box; border:1px solid rgba(226,193,123,.28); color:#ead9b5; background:rgba(17,18,15,.9); backdrop-filter:blur(16px); box-shadow:0 18rpx 55rpx rgba(0,0,0,.5); }
.reconstruction-note>button { position:absolute; right:13rpx; top:8rpx; color:rgba(242,224,187,.58); font-size:28rpx; }.reconstruction-note span { color:#d5ad5c; font:15rpx var(--font-display); letter-spacing:4rpx; }.reconstruction-note p { margin:10rpx 0 8rpx; color:#eee0c2; font:18rpx/1.65 var(--font-display); }.reconstruction-note small { color:rgba(238,220,184,.48); font-size:14rpx; }
.media-retry { position:absolute; z-index:10; top:120rpx; left:50%; transform:translateX(-50%); padding:10rpx 16rpx; border:1px solid rgba(236,210,155,.35); color:#f0d9aa; background:rgba(20,17,13,.72); backdrop-filter:blur(8px); font-size:16rpx; }
.scene-heading { position: absolute; top: 110rpx; left: 7%; max-width: 58%; text-shadow: 0 2px 18px #000; }
.spread--exploration .scene-heading { box-sizing:border-box; padding:14rpx 17rpx 16rpx; border-left:2px solid rgba(221,183,95,.72); background:linear-gradient(90deg,rgba(9,12,10,.76),rgba(9,12,10,.38) 72%,transparent); backdrop-filter:blur(3px); }
.scene-heading span,.cinematic-copy>span,.decision-copy>span,.detour-copy>span,.archive-sheet>span,.notebook-sheet>span,.inquiry-sheet>span,.ending-copy>span { font-size: 17rpx; letter-spacing: 5rpx; color: #e3bf71; }
.scene-heading h2,.cinematic-copy h2,.decision-copy h2,.detour-copy h2,.archive-sheet h2,.notebook-sheet h2,.inquiry-sheet h2,.ending-copy h2 { margin: 8rpx 0; font: 700 43rpx/1.15 var(--font-display); letter-spacing: 2rpx; }
.scene-heading p { margin: 0; color: rgba(255,246,226,.76); font-size: 19rpx; line-height:1.55; }
.scene-heading small { display:block; max-width:620rpx; margin-top:9rpx; padding-left:12rpx; border-left:1px solid rgba(226,187,102,.5); color:#e5c98e; font:16rpx/1.5 var(--font-display); }
.cover-copy { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 8%; text-align: center; background: linear-gradient(90deg, rgba(40,18,15,.88), rgba(63,31,24,.52), rgba(21,16,13,.77)); }
.cover-copy>span { font-size: 18rpx; letter-spacing: 7rpx; color: #d6af62; }
.cover-copy__rule { width: 1px; height: 68rpx; margin: 25rpx 0; background: linear-gradient(transparent,#d9ba75,transparent); }
.cover-copy__title { margin: 0; font: 700 clamp(58rpx,8vw,108rpx)/1 var(--font-display); letter-spacing: 14rpx; text-shadow: 0 7rpx 32rpx rgba(0,0,0,.45); }
.cover-copy p { margin: 23rpx 0 44rpx; font: 24rpx/1.55 var(--font-display); letter-spacing: 3rpx; color: rgba(255,244,221,.72); }
.cover-timeline { width:min(930rpx,92%); display:grid; grid-template-columns:repeat(5,1fr); margin:-12rpx 0 30rpx; border-top:1px solid rgba(226,194,124,.28); }
.cover-timeline article { position:relative; display:grid; gap:3rpx; padding:17rpx 9rpx 0; text-align:left; border-left:1px solid rgba(226,194,124,.15); }
.cover-timeline article::before { content:''; position:absolute; top:-5rpx; left:12rpx; width:8rpx; height:8rpx; border-radius:50%; background:#d5ae5f; box-shadow:0 0 14rpx rgba(226,184,98,.7); }
.cover-timeline i { color:#b88d43; font:13rpx var(--font-display); font-style:normal; }.cover-timeline span { color:rgba(255,238,203,.54); font-size:13rpx; }.cover-timeline b { color:#f1dfba; font:600 16rpx/1.35 var(--font-display); }
.cover-copy button { min-width: 250rpx; padding: 18rpx 24rpx; border: 1px solid rgba(231,198,126,.45); background: rgba(20,13,10,.38); color: #f5e7c8; backdrop-filter: blur(8px); }
.cover-copy button b,.cover-copy button em { display: block; font-style: normal; }.cover-copy button b { font-size: 15rpx; letter-spacing: 4rpx; color: #c89b47; }.cover-copy button em { margin-top: 3rpx; font-size: 20rpx; }
.cinematic-copy { position: absolute; left: 6%; bottom: 9%; width: min(600rpx,68%); padding-left: 23rpx; border-left: 2px solid #caa454; text-shadow: 0 3rpx 20rpx #000; }
.cinematic-copy p { margin: 14rpx 0 7rpx; max-width: 690rpx; font: 24rpx/1.72 var(--font-display); color: rgba(255,247,229,.88); }
.cinematic-copy small { font-size: 17rpx; letter-spacing: 2rpx; color: rgba(255,244,218,.5); }
.cinematic-copy blockquote { display: inline-block; margin: 13rpx 0 0; padding: 12rpx 16rpx; background: rgba(17,20,17,.55); border: 1px solid rgba(220,188,115,.2); color: #edd8a8; font: 22rpx/1.55 var(--font-display); }
.event-meta { display:flex; align-items:center; gap:10rpx; margin-bottom:9rpx; color:rgba(255,239,207,.72); font:15rpx var(--font-display); letter-spacing:1rpx; }
.event-meta b { padding:5rpx 9rpx; color:#2a2117; background:#ddb968; font-weight:700; text-shadow:none; }.event-meta i { width:22rpx; height:1px; background:#d4ad5b; }.event-meta span { color:rgba(255,239,207,.67); }
.event-meaning { display:block; margin:7rpx 0 5rpx; padding-left:12rpx; border-left:1px solid rgba(226,187,102,.5); color:#e5c98e !important; font:16rpx/1.5 var(--font-display) !important; letter-spacing:0 !important; }
.event-brief { margin:4rpx 0 14rpx; padding:11rpx 14rpx; border-left:2px solid #d3aa58; background:rgba(14,16,14,.48); }.event-brief p { margin:0 !important; font-size:18rpx !important; }.event-brief small { color:#e4c98f; font-size:15rpx; line-height:1.45; }
.cinematic-copy--dialogue { left: auto; right: 7%; bottom: 11%; width: min(530rpx,55%); padding: 27rpx; border: 1px solid rgba(236,215,168,.24); background: rgba(17,19,16,.58); backdrop-filter: blur(8px); }
.hotspot { position: absolute; z-index: 9; display: grid; place-items: center; width: 52rpx; height: 52rpx; transform: translate(-50%,-50%); border-radius: 50%; color: #17120d; background: rgba(241,205,125,.9); box-shadow: 0 0 0 10rpx rgba(231,188,96,.12),0 0 35rpx rgba(231,188,96,.62); }
.hotspot::before { content:''; position:absolute; inset:-14rpx; border:1px solid rgba(244,211,137,.4); border-radius:50%; animation: pulse 2.1s infinite; }.hotspot span { font-size: 15rpx; font-weight: 800; }.hotspot.discovered { color:#efdfbd; background:#6d2a24; }.hotspot.active { box-shadow:0 0 0 12rpx rgba(255,225,153,.23),0 0 50rpx #e5bb66; }
.clue-sheet { position: absolute; z-index: 12; left: 6%; bottom: 8%; width: min(570rpx,77%); padding: 27rpx 30rpx; box-sizing: border-box; color: #34291e; background: #eee2c7; box-shadow: 0 18rpx 55rpx rgba(0,0,0,.45); transform: rotate(-.4deg); }
.clue-sheet::before { content:''; position:absolute; inset:9rpx; border:1px solid rgba(91,63,38,.17); pointer-events:none; }.clue-sheet__close { position:absolute; right:16rpx; top:10rpx; color:#7a2a22; font-size:31rpx; }.clue-sheet>span { color:#8b662b; font-size:14rpx; letter-spacing:3rpx; }.clue-sheet h3 { margin:7rpx 0; font:700 29rpx var(--font-display); }.clue-sheet p { margin:0; font:21rpx/1.65 var(--font-display); }.clue-sheet small { display:block; margin-top:13rpx; color:#7e5e31; font-size:16rpx; }
.exploration-progress { position:absolute; right:5%; bottom:7%; width:190rpx; font-size:16rpx; color:rgba(255,245,222,.68); text-align:right; }.exploration-progress i { display:block; height:2px; margin-top:8rpx; background:rgba(255,255,255,.2); }.exploration-progress b { display:block; height:100%; background:#ddb75f; transition:width .3s; }
.decision-copy { position:absolute; left:5.5%; top:50%; width:min(620rpx,58%); transform:translateY(-48%); }.decision-copy>p { margin:12rpx 0 22rpx; font:23rpx/1.6 var(--font-display); color:rgba(255,244,222,.78); }.decision-list { display:grid; gap:10rpx; }.decision-list button { display:grid; grid-template-columns:42rpx 1fr 28rpx; align-items:center; gap:13rpx; padding:15rpx 18rpx; color:#f5ead2; border:1px solid rgba(237,211,156,.21); background:rgba(15,17,14,.57); text-align:left; backdrop-filter:blur(8px); }.decision-list button b { display:grid; place-items:center; width:36rpx; height:36rpx; border:1px solid #bd9750; color:#dbb865; font-size:16rpx; }.decision-list button span { font:20rpx/1.4 var(--font-display); }.decision-list button i { color:#d2a954; font-style:normal; }.decision-list button.selected { color:#2b2116; background:#ead8b0; border-color:#f2d38f; }.decision-list button.selected b { background:#7a2720; color:#fff2d8; }.decision-list button:disabled { cursor:not-allowed; opacity:.44; }.choice-feedback { margin-top:12rpx; padding:13rpx 16rpx; color:#ead5aa; background:rgba(117,35,29,.72); font-size:18rpx; line-height:1.5; }.decision-copy>small { display:block; margin-top:12rpx; color:rgba(255,242,212,.5); font-size:16rpx; }
.detour-copy { position:absolute; left:7%; bottom:10%; width:min(590rpx,72%); box-sizing:border-box; padding:27rpx 29rpx; border-left:3rpx solid #b38d49; color:#f5e8cf; background:linear-gradient(110deg,rgba(20,18,15,.9),rgba(28,25,20,.66)); box-shadow:0 20rpx 60rpx rgba(0,0,0,.42); backdrop-filter:blur(8px); }
.detour-copy>p { margin:13rpx 0 17rpx; color:rgba(255,244,221,.8); font:21rpx/1.65 var(--font-display); }
.detour-copy__break { display:grid; grid-template-columns:1fr auto 1fr; align-items:center; gap:10rpx; color:#d1aa62; font-size:15rpx; letter-spacing:2rpx; }.detour-copy__break i { height:1px; background:rgba(216,178,101,.28); }
.detour-copy aside { display:grid; grid-template-columns:auto 1fr; gap:10rpx; margin:15rpx 0; padding:12rpx 14rpx; border:1px solid rgba(226,190,111,.2); background:rgba(112,39,31,.34); }.detour-copy aside strong { color:#e3bd6d; font-size:15rpx; }.detour-copy aside span { color:#ead9b7; font-size:16rpx; line-height:1.5; letter-spacing:0; }
.detour-copy>button { margin-top:15rpx; padding:13rpx 17rpx; border:1px solid rgba(226,190,111,.42); color:#2b2117; background:#ddbb72; font:700 17rpx var(--font-display); }
.archive-sheet,.notebook-sheet,.inquiry-sheet { position:absolute; left:7%; right:7%; top:50%; max-height:76%; transform:translateY(-48%) rotate(-.25deg); box-sizing:border-box; padding:42rpx 49rpx; overflow:auto; color:#35291e; background:#efe4ca; box-shadow:0 25rpx 75rpx rgba(0,0,0,.55); }.archive-sheet::after,.notebook-sheet::after,.inquiry-sheet::after { content:''; position:absolute; inset:12rpx; border:1px solid rgba(83,60,36,.17); pointer-events:none; }.archive-sheet__mark { position:absolute; right:37rpx; top:32rpx; width:74rpx; height:74rpx; display:grid; place-items:center; border:3rpx double rgba(119,36,30,.55); border-radius:50%; color:#7d2a23; font:700 14rpx/1.2 var(--font-display); text-align:center; transform:rotate(8deg); }.archive-sheet>span,.notebook-sheet>span,.inquiry-sheet>span { color:#986d31; }.archive-sheet h2,.notebook-sheet h2,.inquiry-sheet h2 { color:#34271b; max-width:80%; }.archive-sheet blockquote { margin:29rpx 0; padding:21rpx 25rpx; border-left:3px solid #8b2e27; background:rgba(255,252,238,.55); font:24rpx/1.85 var(--font-display); }.archive-sheet footer { display:flex; justify-content:space-between; gap:20rpx; font-size:16rpx; color:#77634c; }.archive-sheet a { color:#7b2c25; }
.archive-conclusion { margin:0 0 18rpx; padding:12rpx 15rpx; color:#68533c; background:rgba(118,85,44,.08); font:17rpx/1.55 var(--font-display); }.archive-conclusion b { color:#7b2c25; }
.notebook-sheet { background-color:#f2e7cf; background-image:repeating-linear-gradient(transparent,transparent 52rpx,rgba(77,61,43,.11) 53rpx); }.notebook-sheet>p,.inquiry-sheet>p { color:#735f49; font:20rpx/1.65 var(--font-display); }.notebook-sheet textarea { position:relative; z-index:2; width:100%; min-height:210rpx; padding:12rpx 2rpx; border:0; background:transparent; box-shadow:none; color:#3a2e22; font:23rpx/53rpx var(--font-display); resize:none; }.notebook-sheet footer { position:relative; z-index:2; display:flex; justify-content:space-between; font-size:16rpx; color:#80684d; }.notebook-sheet footer b { color:#38604a; }
.paper-context { position:relative; z-index:2; display:flex; align-items:center; gap:10rpx; margin:-5rpx 0 18rpx; padding-bottom:12rpx; border-bottom:1px solid rgba(100,72,42,.16); color:#7a6042; font-size:15rpx; }.paper-context b { padding:4rpx 8rpx; color:#f3e7cc; background:#7b342b; }.paper-context span { font-weight:600; }
.inquiry-sheet { background:#eee1c5; }.qa-log { position:relative; z-index:2; max-height:200rpx; overflow:auto; margin:15rpx 0; }.qa-log article { display:grid; grid-template-columns:31rpx 1fr; gap:8rpx 11rpx; padding:10rpx 0; border-top:1px solid rgba(81,57,34,.13); }.qa-log article>b { grid-row:1/3; display:grid; place-items:center; width:29rpx; height:29rpx; border-radius:50%; color:#f8ead0; background:#792c25; font-size:14rpx; }.qa-log strong { font:700 18rpx var(--font-display); }.qa-log p { grid-column:2; margin:0; color:#6f5b45; font-size:17rpx; line-height:1.5; }.ask-row { position:relative; z-index:2; display:flex; gap:8rpx; }.ask-row input { flex:1; min-width:0; border:1px solid rgba(80,58,37,.2); background:rgba(255,253,243,.65); }.ask-row button { width:91rpx; color:#faecd1; background:#742b25; }.ask-row button:disabled { opacity:.45; }.inquiry-sheet>small { position:relative; z-index:2; display:block; margin-top:9rpx; color:#806d58; font-size:15rpx; }
.ending-copy { position:absolute; top:50%; left:50%; width:min(640rpx,78%); max-height:78%; overflow:auto; transform:translate(-50%,-47%); padding:38rpx; text-align:center; border:1px solid rgba(231,204,147,.26); background:rgba(14,17,14,.69); backdrop-filter:blur(13px); box-shadow:0 25rpx 70rpx rgba(0,0,0,.45); }.ending-copy__seal { display:grid; place-items:center; align-content:center; width:112rpx; height:112rpx; margin:0 auto 22rpx; border:4rpx double #a77e46; border-radius:50%; color:#d3ad67; transform:rotate(-7deg); }.ending-copy__seal.stamped { border-color:#c85548; color:#f3b3a7; box-shadow:0 0 30rpx rgba(186,51,42,.2); }.ending-copy__seal span { font-size:14rpx; letter-spacing:2rpx; }.ending-copy__seal b { font:700 25rpx var(--font-display); }.ending-copy>p { margin:12rpx auto 21rpx; max-width:520rpx; color:rgba(255,244,222,.72); font:21rpx/1.65 var(--font-display); }.complete-button { min-width:260rpx; padding:17rpx 25rpx; border:1px solid #d0a352; color:#2b1c12; background:#e5c176; font:700 20rpx var(--font-display); }.complete-button:disabled { color:rgba(255,247,229,.5); border-color:rgba(255,255,255,.18); background:rgba(255,255,255,.08); }.ending-copy>small { display:block; margin-top:11rpx; color:rgba(255,243,218,.45); font-size:15rpx; }.report-preview { max-height:170rpx; overflow:auto; margin:15rpx 0; padding:15rpx; color:#39291d; background:#ede0c4; text-align:left; }.report-preview strong { color:#7c2a24; }.report-preview p { margin:5rpx 0 0; color:#604e3b; font:17rpx/1.6 var(--font-display); }
.ending-inquiry { margin:14rpx auto; max-width:560rpx; text-align:left; }
.ending-inquiry .ask-row input { color:#3a2c20; }
.ending-inquiry .ask-row input::placeholder { color:#806d58; opacity:1; }
.ending-inquiry__answer { display:grid; grid-template-columns:auto 1fr; gap:10rpx; max-height:92rpx; margin-bottom:9rpx; padding:11rpx 13rpx; overflow:auto; color:#37291d; background:#eadcbd; font:16rpx/1.5 var(--font-display); }
.ending-inquiry__answer b { color:#7a2922; white-space:nowrap; }
.ending-checks { display:flex; justify-content:center; flex-wrap:wrap; gap:8rpx; margin:12rpx 0 15rpx; }
.ending-checks span { padding:7rpx 11rpx; border:1px solid rgba(255,255,255,.16); color:rgba(255,244,219,.48); background:rgba(6,8,7,.28); font-size:15rpx; }
.ending-checks span.done { border-color:rgba(188,217,167,.35); color:#cce1b8; background:rgba(43,78,49,.35); }
.particles { z-index:-1; pointer-events:none; }.particles::before { content:''; position:absolute; inset:-60%; opacity:.25; animation:drift 12s linear infinite; }.particles--dust::before { background-image:radial-gradient(circle,#f2d79d 0 1px,transparent 1.5px); background-size:43px 53px; }.particles--mist::before { filter:blur(30px); background:radial-gradient(ellipse at 30% 50%,rgba(235,237,216,.35),transparent 28%),radial-gradient(ellipse at 70% 40%,rgba(226,230,213,.22),transparent 25%); }.particles--rain::before { transform:rotate(12deg); background:repeating-linear-gradient(90deg,transparent 0 28px,rgba(218,229,221,.22) 29px 30px,transparent 31px 58px); }
@keyframes pulse { 0%{transform:scale(.8);opacity:.8} 100%{transform:scale(1.55);opacity:0} } @keyframes drift { to{transform:translate3d(14%,18%,0) rotate(4deg)} }
.particles { z-index: 2; }
.clue-enter-active,.clue-leave-active { transition:opacity .25s,transform .35s cubic-bezier(.2,.8,.2,1); }.clue-enter-from,.clue-leave-to { opacity:0; transform:translateY(20rpx) rotate(1deg); }
/* #ifndef H5 */
@media (max-width: 700px) {
  .cover-timeline { grid-template-columns:repeat(5,minmax(0,1fr)); width:100%; margin:-20rpx 0 24rpx; }.cover-timeline article { padding:14rpx 5rpx 0; }.cover-timeline i,.cover-timeline span { font-size:10rpx; }.cover-timeline b { font-size:12rpx; line-height:1.25; }
  .event-meta { flex-wrap:wrap; gap:6rpx; }.event-meta i { width:12rpx; }
  .reconstruction-badge { top:70rpx; right:18rpx; }
  .scene-heading { top:105rpx; left:7%; max-width:80%; }.scene-heading h2,.cinematic-copy h2,.decision-copy h2,.detour-copy h2 { font-size:37rpx; }
  .cinematic-copy,.cinematic-copy--dialogue { left:7%; right:7%; bottom:10%; width:auto; box-sizing:border-box; }
  .decision-copy { left:7%; width:86%; }.decision-list button { padding:14rpx; }.detour-copy { left:6%; width:88%; bottom:9%; }
  .archive-sheet,.notebook-sheet,.inquiry-sheet { left:5%; right:5%; padding:36rpx 29rpx; max-height:74%; }.archive-sheet h2,.notebook-sheet h2,.inquiry-sheet h2 { font-size:35rpx; }
  .ending-copy { width:84%; box-sizing:border-box; padding:30rpx 24rpx; }
  .exploration-progress { right:6%; bottom:5%; }.clue-sheet { left:5%; width:90%; bottom:12%; }
}
/* #endif */
/* #ifdef H5 */
@container (max-width: 700px) {
  .cover-timeline { grid-template-columns:repeat(5,minmax(0,1fr)); width:100%; margin:-20rpx 0 24rpx; }.cover-timeline article { padding:14rpx 5rpx 0; }.cover-timeline i,.cover-timeline span { font-size:10rpx; }.cover-timeline b { font-size:12rpx; line-height:1.25; }
  .event-meta { flex-wrap:wrap; gap:6rpx; }.event-meta i { width:12rpx; }
  .reconstruction-badge { top:70rpx; right:18rpx; }
  .scene-heading { top:105rpx; left:7%; max-width:80%; }.scene-heading h2,.cinematic-copy h2,.decision-copy h2,.detour-copy h2 { font-size:37rpx; }
  .cinematic-copy,.cinematic-copy--dialogue { left:7%; right:7%; bottom:10%; width:auto; box-sizing:border-box; }
  .decision-copy { left:7%; width:86%; }.decision-list button { padding:14rpx; }.detour-copy { left:6%; width:88%; bottom:9%; }
  .archive-sheet,.notebook-sheet,.inquiry-sheet { left:5%; right:5%; padding:36rpx 29rpx; max-height:74%; }.archive-sheet h2,.notebook-sheet h2,.inquiry-sheet h2 { font-size:35rpx; }
  .ending-copy { width:84%; box-sizing:border-box; padding:30rpx 24rpx; }
  .exploration-progress { right:6%; bottom:5%; }.clue-sheet { left:5%; width:90%; bottom:12%; }
}
/* #endif */
@media (prefers-reduced-motion: reduce) { .spread__scene { transition:none; }.particles,.hotspot::before { display:none; } }
</style>
