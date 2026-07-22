<template>
  <div class="archive-room">
    <div class="archive-room__backdrop" :style="archiveBackdrop ? { backgroundImage: `url(${archiveBackdrop})` } : {}"></div>
    <div class="archive-room__light"></div><div class="archive-room__dust"></div>
    <header class="archive-header">
      <button @click="goBack">← <span>返回</span></button>
      <div><span>THE ARCHIVE OF LIVING HISTORY</span><h1>党史现场纪事</h1><p>五卷历史场景书 · 以见证者视角抵达真实历史进程</p></div>
      <aside><b>{{ completedCount }}</b><span>/ 5 已归档</span></aside>
    </header>

    <main class="archive-shelf">
      <div class="archive-shelf__label"><span>馆藏 · 第一辑</span><i></i><b>点击书脊，抽出一卷历史</b></div>
      <div v-if="loading" class="archive-state"><i></i><span>管理员正在整理书架…</span></div>
      <button v-else-if="error" class="archive-state archive-state--error" @click="loadBooks">{{ error }} · 点击重试</button>
      <div v-else class="volumes">
        <button
          v-for="(book, index) in books"
          :key="book.id"
          class="volume"
          :class="[{ completed: book.progress.completed, started: book.progress.current_spread > 0 }, `volume--${index + 1}`]"
          @click="openBook(book)"
        >
          <div class="volume__cover" :style="{ backgroundImage: `url(${book.cover_url})` }"><div class="volume__wash"></div></div>
          <div class="volume__binding"><small>卷 {{ cnNumbers[index] }}</small><i></i><h2>{{ book.title }}</h2><p>{{ book.era }}</p><b>{{ book.progress.completed ? '已归档' : book.progress.current_spread ? `续读 ${book.progress.current_spread + 1}/8` : '未启封' }}</b></div>
          <div class="volume__edge"></div>
          <div v-if="book.progress.completed" class="volume__stamp">阅毕</div>
        </button>
      </div>
      <div class="archive-shelf__wood"><i></i></div>
    </main>

    <footer class="archive-note"><span>01</span><p>场景画面均标注“艺术化情景复原”。选择只改变观察顺序，不改变历史结果。</p><b>声音默认关闭</b></footer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { immersiveApi, type ImmersiveBookSummary } from '@/api/immersive'
// #ifdef H5
import historyHero from '@/assets/scenes/history-archive-hero.png'
// #endif

let archiveBackdrop = ''
// #ifdef H5
archiveBackdrop = historyHero
// #endif

const books = ref<ImmersiveBookSummary[]>([])
const loading = ref(true)
const error = ref('')
const cnNumbers = ['一', '二', '三', '四', '五']
const completedCount = computed(() => books.value.filter(item => item.progress.completed).length)

onMounted(loadBooks)
async function loadBooks() {
  loading.value = true; error.value = ''
  try { books.value = await immersiveApi.getBooks('history') }
  catch (err: any) { error.value = err.message || '书架加载失败' }
  finally { loading.value = false }
}
function openBook(book: ImmersiveBookSummary) { uni.navigateTo({ url: `/pages/history/scenario?bookId=${book.id}&id=${book.source_id}` }) }
function goBack() { uni.navigateBack() }
</script>

<style scoped>
.archive-room { position:relative; min-height:100vh; box-sizing:border-box; overflow:hidden; padding:45rpx clamp(30rpx,5vw,90rpx) 34rpx; color:#eee0c2; background:#0d100e; isolation:isolate; }.archive-room::before { content:'';position:absolute;z-index:-4;inset:0;background:linear-gradient(90deg,rgba(5,7,6,.95),rgba(17,18,15,.26) 50%,rgba(6,8,7,.9)),url('/static/images/scenes/history-archive-hero.png') center/cover;filter:saturate(.53) sepia(.15); }.archive-room::after { content:'';position:absolute;z-index:-2;inset:0;background:linear-gradient(0deg,#090b0a 0,transparent 35%),radial-gradient(ellipse at 50% -8%,rgba(241,212,150,.23),transparent 46%); }.archive-room__light { position:absolute;z-index:-1;left:27%;top:-25%;width:46%;height:105%;transform:skewX(-9deg);opacity:.17;background:linear-gradient(90deg,transparent,#ffe4a3,transparent);filter:blur(26px); }.archive-room__dust { position:absolute;inset:-20%;pointer-events:none;opacity:.13;background-image:radial-gradient(circle,#f6dda4 0 1px,transparent 1.5px);background-size:47px 59px;animation:dust 18s linear infinite; }
.archive-room__backdrop { position:absolute;z-index:-5;inset:0;background-position:center;background-size:cover;filter:saturate(.53) sepia(.15); }
.archive-header { position:relative;z-index:2;display:grid;grid-template-columns:120rpx 1fr 150rpx;align-items:start;gap:20rpx;max-width:1350px;margin:0 auto; }.archive-header>button { justify-self:start;color:#c7ac77;font-size:19rpx;letter-spacing:2rpx; }.archive-header>button span { margin-left:7rpx; }.archive-header>div { text-align:center; }.archive-header>div>span { color:#b99a5d;font-size:15rpx;letter-spacing:8rpx; }.archive-header h1 { margin:9rpx 0 4rpx;font:700 clamp(45rpx,5vw,72rpx)/1 var(--font-display);letter-spacing:12rpx;text-shadow:0 8rpx 28rpx #000; }.archive-header p { margin:11rpx 0 0;color:rgba(241,226,197,.55);font:19rpx var(--font-display);letter-spacing:2rpx; }.archive-header aside { justify-self:end;display:flex;align-items:baseline;gap:6rpx;color:#bba475; }.archive-header aside b { color:#e4c57e;font:700 38rpx var(--font-display); }.archive-header aside span { font-size:16rpx; }
.archive-shelf { position:relative;z-index:2;max-width:1320px;margin:50rpx auto 0;padding:0 24rpx 51rpx;background:linear-gradient(90deg,rgba(14,12,9,.75),rgba(46,35,25,.48),rgba(13,12,10,.75));border-left:14rpx solid #24180f;border-right:14rpx solid #24180f;box-shadow:inset 0 0 80rpx rgba(0,0,0,.72),0 25rpx 80rpx rgba(0,0,0,.5); }.archive-shelf__label { display:flex;align-items:center;gap:18rpx;padding:19rpx 5rpx 24rpx;color:#aa8c56;font-size:15rpx;letter-spacing:4rpx; }.archive-shelf__label i { flex:1;height:1px;background:linear-gradient(90deg,rgba(194,158,91,.38),transparent); }.archive-shelf__label b { color:rgba(232,214,180,.45);font-weight:400;letter-spacing:1rpx; }.volumes { display:flex;align-items:flex-end;justify-content:center;gap:clamp(8rpx,1.1vw,24rpx);min-height:490rpx;perspective:1400px; }.volume { position:relative;width:min(17%,210px);height:430rpx;display:grid;grid-template-columns:34% 1fr;overflow:visible;color:#ecdfc5;text-align:left;box-shadow:12rpx 10rpx 31rpx rgba(0,0,0,.48);transform-origin:bottom;transition:transform .45s cubic-bezier(.2,.8,.2,1),filter .35s; }.volume:nth-child(even){height:455rpx}.volume:hover { z-index:10;transform:translateY(-25rpx) rotateY(-6deg) scale(1.035);filter:brightness(1.13); }.volume__cover { position:absolute;inset:0;background-size:cover;background-position:center;filter:saturate(.45) sepia(.22); }.volume__wash { position:absolute;inset:0;background:linear-gradient(90deg,rgba(44,15,15,.84),rgba(91,31,25,.55) 32%,rgba(24,18,15,.36)); }.volume--2 .volume__wash { background:linear-gradient(90deg,rgba(15,38,32,.88),rgba(32,72,57,.57),rgba(20,20,16,.3)); }.volume--3 .volume__wash { background:linear-gradient(90deg,rgba(52,39,22,.88),rgba(121,79,32,.5),rgba(20,17,14,.3)); }.volume--4 .volume__wash { background:linear-gradient(90deg,rgba(38,22,31,.9),rgba(88,50,63,.55),rgba(20,17,18,.3)); }.volume--5 .volume__wash { background:linear-gradient(90deg,rgba(15,34,37,.9),rgba(34,69,74,.55),rgba(16,18,17,.3)); }.volume__binding { position:relative;z-index:2;grid-column:1;padding:24rpx 10rpx;display:flex;flex-direction:column;align-items:center;border-right:1px solid rgba(236,207,143,.18);background:linear-gradient(90deg,rgba(0,0,0,.35),transparent);writing-mode:vertical-rl; }.volume__binding small { color:#d0ad64;font-size:14rpx;letter-spacing:3rpx; }.volume__binding i { height:38rpx;width:1px;margin:14rpx 0;background:#b29151; }.volume__binding h2 { margin:0;font:700 27rpx/1 var(--font-display);letter-spacing:7rpx; }.volume__binding p { margin:auto 0 8rpx;color:rgba(255,239,210,.55);font-size:14rpx;letter-spacing:2rpx; }.volume__binding b { padding:6rpx 3rpx;color:#e4c37d;border:1px solid rgba(222,186,111,.34);font-size:13rpx;font-weight:400;letter-spacing:1rpx; }.volume__edge { position:absolute;z-index:3;right:-8rpx;top:7rpx;bottom:5rpx;width:8rpx;background:repeating-linear-gradient(0deg,#ddcda8 0 2rpx,#a89776 3rpx 4rpx);transform:skewY(-4deg); }.volume__stamp { position:absolute;z-index:5;right:13rpx;top:18rpx;display:grid;place-items:center;width:63rpx;height:63rpx;border:4rpx double #e29e82;border-radius:50%;color:#ffd4bf;font:700 17rpx var(--font-display);transform:rotate(10deg);text-shadow:0 1px 6px #38100d; }.archive-shelf__wood { position:absolute;left:-25rpx;right:-25rpx;bottom:0;height:49rpx;background:linear-gradient(#52351f,#26170e 60%,#100b07);border-top:4rpx solid #745039;box-shadow:0 18rpx 27rpx #000; }.archive-shelf__wood i { display:block;height:1px;margin-top:17rpx;background:rgba(224,177,105,.16); }.archive-state { min-height:490rpx;display:flex;flex-direction:column;align-items:center;justify-content:center;color:#bba577;font-size:19rpx; }.archive-state i { width:55rpx;height:75rpx;border:1px solid #ad8b50;border-left:8rpx solid #73522c;margin-bottom:20rpx;animation:lean 1.5s infinite alternate; }.archive-state--error { width:100%; }
.archive-note { position:relative;z-index:2;max-width:1000px;margin:31rpx auto 0;display:grid;grid-template-columns:42rpx 1fr auto;align-items:center;gap:19rpx;color:rgba(238,221,188,.47); }.archive-note>span { display:grid;place-items:center;width:36rpx;height:36rpx;border:1px solid rgba(200,165,95,.35);color:#be9a56;font-size:14rpx; }.archive-note p { margin:0;font-size:16rpx; }.archive-note b { color:#aa8e5a;font-size:15rpx;font-weight:400;letter-spacing:2rpx; }
@keyframes dust{to{transform:translate3d(10%,16%,0)}}@keyframes lean{to{transform:rotateY(-15deg) translateY(-5rpx)}}
@media(max-width:700px){.archive-room{padding:29rpx 18rpx 25rpx;overflow:auto}.archive-header{grid-template-columns:68rpx 1fr 68rpx}.archive-header>div>span{font-size:11rpx;letter-spacing:4rpx}.archive-header h1{font-size:40rpx;letter-spacing:6rpx}.archive-header p{font-size:16rpx}.archive-header aside{display:block;text-align:right}.archive-header aside b{font-size:28rpx}.archive-header aside span{display:block;font-size:12rpx}.archive-shelf{margin-top:36rpx;padding:0 12rpx 43rpx}.archive-shelf__label b{display:none}.volumes{min-height:600rpx;display:grid;grid-template-columns:repeat(5,1fr);align-items:end;gap:5rpx}.volume,.volume:nth-child(even){width:100%;height:520rpx;grid-template-columns:1fr}.volume__cover{display:none}.volume__binding{grid-column:1;background:linear-gradient(90deg,#351b17,#762c25 55%,#311b17)}.volume--2 .volume__binding{background:linear-gradient(90deg,#172820,#365b49,#14251e)}.volume--3 .volume__binding{background:linear-gradient(90deg,#3d2d19,#8c612f,#332214)}.volume--4 .volume__binding{background:linear-gradient(90deg,#2d1d27,#674052,#2b1923)}.volume--5 .volume__binding{background:linear-gradient(90deg,#17272b,#31545b,#142327)}.volume__binding h2{font-size:24rpx;letter-spacing:6rpx}.volume__stamp{right:50%;top:14rpx;transform:translateX(50%) rotate(10deg);width:49rpx;height:49rpx;font-size:14rpx}.archive-note{grid-template-columns:33rpx 1fr}.archive-note b{display:none}}
</style>
