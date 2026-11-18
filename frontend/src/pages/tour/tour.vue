<template>
  <div class="atlas-desk">
    <div class="atlas-desk__backdrop" :style="atlasBackdrop ? { backgroundImage: `url(${atlasBackdrop})` } : {}"></div>
    <div class="desk-grain"></div>
    <header class="atlas-header">
      <button @click="goBack">← <span>收起地图</span></button>
      <div><span>FIELD ATLAS · VOLUME I</span><h1>红色山河研学图志</h1><p>沿五个真实地标，打开五扇历史之窗</p></div>
      <aside><b>{{ completedCount }}</b><span>枚印章</span></aside>
    </header>

    <main class="fold-map">
      <div class="fold-map__fold fold-map__fold--one"></div><div class="fold-map__fold fold-map__fold--two"></div>
      <svg class="route-line" viewBox="0 0 1000 510" preserveAspectRatio="none" aria-hidden="true"><path d="M105,405 C180,330 214,198 326,225 S436,420 541,348 S625,104 738,144 S839,315 920,232"/><path class="route-dash" d="M105,405 C180,330 214,198 326,225 S436,420 541,348 S625,104 738,144 S839,315 920,232"/></svg>
      <div v-if="loading" class="atlas-state"><i>✦</i><span>正在展开路线图…</span></div>
      <button v-else-if="error" class="atlas-state" @click="loadBooks">{{ error }} · 点击重试</button>
      <template v-else>
        <button
          v-for="(book, index) in books"
          :key="book.id"
          class="map-stop"
          :class="[{ completed: book.progress.completed }, `map-stop--${index + 1}`]"
          @click="openBook(book)"
        >
          <div class="map-stop__pin"><i></i><b>{{ index + 1 }}</b></div>
          <article>
            <span>STOP {{ String(index + 1).padStart(2, '0') }} · {{ provinces[index] }}</span>
            <h2>{{ book.title }}</h2><p>{{ book.subtitle }}</p>
            <small>{{ book.progress.completed ? '行程已归档' : book.progress.current_spread ? `从第 ${book.progress.current_spread + 1} 页继续` : '等待抵达' }}</small>
          </article>
          <div v-if="book.progress.completed" class="map-stop__stamp">到访</div>
        </button>
      </template>
      <div class="map-legend"><span><i></i>当代地标</span><span><i></i>历史复原</span><b>非 GPS 打卡</b></div>
      <div class="map-compass"><i>N</i><b>✦</b><span>S</span></div>
    </main>

    <footer class="journey-slip"><span>TRAVEL NOTE</span><p>每站包含当代抵达、历史之窗、现场寻迹、随行追问与研学手记。</p><b>声音与旁白需主动开启</b></footer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { immersiveApi, type ImmersiveBookSummary } from '@/api/immersive'
// #ifdef H5
import tourHero from '@/assets/scenes/tour-expedition-hero.png'
// #endif

let atlasBackdrop = ''
// #ifdef H5
atlasBackdrop = tourHero
// #endif

const books = ref<ImmersiveBookSummary[]>([])
const loading = ref(true)
const error = ref('')
const provinces = ['江西', '陕西', '河北', '湖南', '贵州']
const completedCount = computed(() => books.value.filter(item => item.progress.completed).length)

onMounted(loadBooks)
async function loadBooks() {
  loading.value = true; error.value = ''
  try { books.value = await immersiveApi.getBooks('tour') }
  catch (err: any) { error.value = err.message || '地图加载失败' }
  finally { loading.value = false }
}
function openBook(book: ImmersiveBookSummary) { uni.navigateTo({ url: `/pages/tour/site?bookId=${book.id}&id=${book.source_id}` }) }
function goBack() { uni.navigateBack() }
</script>

<style scoped>
.atlas-desk { position:relative;min-height:100vh;box-sizing:border-box;overflow:hidden;padding:37rpx clamp(28rpx,4vw,75rpx) 27rpx;color:#e9ddc0;background:#1d1712;isolation:isolate; }.atlas-desk::before { content:'';position:absolute;z-index:-4;inset:0;background:linear-gradient(rgba(17,13,10,.58),rgba(12,10,8,.82)),url('/static/images/scenes/tour-expedition-hero.jpg') center/cover;filter:saturate(.5) sepia(.32); }.desk-grain { position:absolute;z-index:-2;inset:0;opacity:.35;background-image:repeating-linear-gradient(7deg,transparent 0 16rpx,rgba(255,229,183,.018) 17rpx 18rpx); }.atlas-header { position:relative;z-index:3;max-width:1390px;margin:0 auto;display:grid;grid-template-columns:150rpx 1fr 130rpx;align-items:start; }.atlas-header>button { color:#c8aa72;font-size:18rpx;letter-spacing:2rpx; }.atlas-header>div { text-align:center; }.atlas-header>div>span { color:#b79559;font-size:14rpx;letter-spacing:7rpx; }.atlas-header h1 { margin:7rpx 0 2rpx;font:700 clamp(42rpx,4.5vw,66rpx)/1.1 var(--font-display);letter-spacing:8rpx;text-shadow:0 7rpx 24rpx #000; }.atlas-header p { margin:8rpx 0 0;color:rgba(239,224,194,.55);font-size:18rpx;letter-spacing:2rpx; }.atlas-header aside { justify-self:end;text-align:center;color:#bfa26a; }.atlas-header aside b { display:block;font:700 38rpx var(--font-display);color:#e0bf78; }.atlas-header aside span { font-size:14rpx; }
.atlas-desk__backdrop { position:absolute;z-index:-5;inset:0;background-position:center;background-size:cover;filter:saturate(.5) sepia(.32); }
.fold-map { position:relative;z-index:2;max-width:1400px;height:min(69vh,690px);min-height:520rpx;margin:29rpx auto 0;overflow:hidden;color:#3d382b;background-color:#d7c9a8;background-image:radial-gradient(circle at 16% 78%,rgba(79,115,80,.23),transparent 22%),radial-gradient(circle at 73% 24%,rgba(117,84,48,.18),transparent 19%),linear-gradient(21deg,transparent 48%,rgba(89,70,46,.05) 49% 51%,transparent 52%);border:1px solid #9f8960;box-shadow:0 31rpx 80rpx rgba(0,0,0,.62),inset 0 0 100rpx rgba(80,55,26,.18);transform:rotate(-.25deg); }.fold-map::before { content:'';position:absolute;inset:0;opacity:.24;background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 180 180' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.65' numOctaves='3'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='.3'/%3E%3C/svg%3E"); }.fold-map__fold { position:absolute;z-index:1;top:0;bottom:0;width:2px;box-shadow:-18rpx 0 24rpx rgba(73,53,29,.13),18rpx 0 20rpx rgba(255,246,218,.16); }.fold-map__fold--one{left:33.333%}.fold-map__fold--two{left:66.666%}.route-line { position:absolute;z-index:2;inset:8% 3%;width:94%;height:84%;overflow:visible;pointer-events:none; }.route-line path { fill:none;stroke:#7d352d;stroke-width:3;opacity:.25; }.route-line .route-dash { stroke:#9b4439;stroke-width:2;stroke-dasharray:5 8;opacity:.7;animation:route 20s linear infinite; }
.map-stop { position:absolute;z-index:6;width:210rpx;color:#3a3024;text-align:left;transition:transform .3s; }.map-stop:hover { z-index:10;transform:translateY(-10rpx) scale(1.03); }.map-stop--1{left:7%;top:61%}.map-stop--2{left:25%;top:28%}.map-stop--3{left:45%;top:56%}.map-stop--4{left:65%;top:14%}.map-stop--5{left:82%;top:39%}.map-stop__pin { position:absolute;left:-37rpx;top:4rpx;width:44rpx;height:52rpx;color:#f2dfb7;filter:drop-shadow(0 5rpx 5rpx rgba(0,0,0,.25)); }.map-stop__pin i { position:absolute;inset:0;background:#77352e;border-radius:50% 50% 50% 0;transform:rotate(-45deg); }.map-stop__pin b { position:absolute;inset:0 0 8rpx;display:grid;place-items:center;color:#f8e7c4;font:700 16rpx var(--font-display); }.map-stop article { position:relative;padding:14rpx 16rpx 13rpx;background:rgba(240,229,201,.91);border:1px solid rgba(95,67,34,.26);box-shadow:5rpx 8rpx 16rpx rgba(71,51,28,.18);transform:rotate(-1deg); }.map-stop:nth-of-type(even) article{transform:rotate(1.2deg)}.map-stop article::before { content:'';position:absolute;top:-9rpx;left:36%;width:54rpx;height:16rpx;background:rgba(205,184,141,.65);transform:rotate(-3deg); }.map-stop article>span { color:#91652b;font-size:11rpx;letter-spacing:2rpx; }.map-stop h2 { margin:3rpx 0 2rpx;font:700 29rpx var(--font-display);letter-spacing:3rpx; }.map-stop p { overflow:hidden;margin:0;color:#786752;font-size:14rpx;line-height:1.35;white-space:nowrap;text-overflow:ellipsis; }.map-stop small { display:block;margin-top:8rpx;padding-top:6rpx;border-top:1px solid rgba(85,61,36,.14);color:#7d332c;font-size:12rpx; }.map-stop__stamp { position:absolute;z-index:4;right:-15rpx;top:-21rpx;display:grid;place-items:center;width:52rpx;height:52rpx;border:4rpx double #a74136;border-radius:50%;color:#a33d33;font:700 14rpx var(--font-display);transform:rotate(12deg); }.map-stop.completed .map-stop__pin i{background:#365b49}.map-stop.completed article{box-shadow:5rpx 8rpx 20rpx rgba(46,81,62,.24)}
.map-legend { position:absolute;z-index:4;left:28rpx;top:24rpx;display:flex;gap:18rpx;padding:9rpx 13rpx;border:1px solid rgba(89,65,36,.18);background:rgba(237,224,193,.55);font-size:12rpx;color:#695c48; }.map-legend span{display:flex;align-items:center;gap:6rpx}.map-legend i{width:8rpx;height:8rpx;border-radius:50%;background:#365b49}.map-legend span:nth-child(2) i{background:#833a32}.map-legend b{color:#8b6740;font-weight:400}.map-compass { position:absolute;right:25rpx;bottom:19rpx;width:72rpx;height:72rpx;border:1px solid rgba(77,61,41,.33);border-radius:50%;text-align:center;color:#715b3e; }.map-compass::after { content:'';position:absolute;left:50%;top:12rpx;bottom:12rpx;width:1px;background:rgba(88,66,39,.3); }.map-compass i,.map-compass span { position:absolute;z-index:2;left:0;right:0;font-size:10rpx;font-style:normal; }.map-compass i{top:-2rpx}.map-compass span{bottom:-2rpx}.map-compass b{position:absolute;z-index:3;inset:0;display:grid;place-items:center;color:#8a3d33;font-size:25rpx}.atlas-state { position:absolute;z-index:5;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;color:#6f5a3e;font-size:18rpx; }.atlas-state i { margin-bottom:12rpx;color:#833b32;font-size:38rpx;animation:compass 2s linear infinite; }
.journey-slip { position:relative;z-index:3;max-width:1000px;margin:22rpx auto 0;display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:20rpx;color:rgba(239,221,187,.46); }.journey-slip>span { color:#bb9655;font-size:13rpx;letter-spacing:4rpx; }.journey-slip p { margin:0;font-size:15rpx; }.journey-slip b { color:#b99b66;font-size:14rpx;font-weight:400; }
@keyframes route{to{stroke-dashoffset:-130}}@keyframes compass{to{transform:rotate(360deg)}}
/* #ifndef H5 */
@media (max-width: 700px){.atlas-desk{padding:24rpx 13rpx;overflow:auto}.atlas-header{grid-template-columns:68rpx 1fr 61rpx}.atlas-header>button span{display:none}.atlas-header>div>span{font-size:10rpx;letter-spacing:4rpx}.atlas-header h1{font-size:35rpx;letter-spacing:4rpx}.atlas-header p{font-size:14rpx}.atlas-header aside b{font-size:27rpx}.fold-map{height:69vh;min-height:950rpx;margin-top:23rpx}.route-line{inset:2%;height:96%;transform:rotate(90deg) scale(.9)}.map-stop{width:220rpx}.map-stop--1{left:13%;top:74%}.map-stop--2{left:49%;top:58%}.map-stop--3{left:14%;top:42%}.map-stop--4{left:50%;top:24%}.map-stop--5{left:18%;top:8%}.map-stop article>span{font-size:11rpx}.map-stop h2{font-size:26rpx}.map-stop p{font-size:13rpx}.map-legend{left:13rpx;top:auto;bottom:12rpx;gap:9rpx}.map-compass{right:12rpx;bottom:10rpx}.journey-slip{grid-template-columns:auto 1fr}.journey-slip b{display:none}}
/* #endif */
/* #ifdef H5 */
@container (max-width: 700px){.atlas-desk{padding:24rpx 13rpx;overflow:auto}.atlas-header{grid-template-columns:68rpx 1fr 61rpx}.atlas-header>button span{display:none}.atlas-header>div>span{font-size:10rpx;letter-spacing:4rpx}.atlas-header h1{font-size:35rpx;letter-spacing:4rpx}.atlas-header p{font-size:14rpx}.atlas-header aside b{font-size:27rpx}.fold-map{height:69vh;min-height:950rpx;margin-top:23rpx}.route-line{inset:2%;height:96%;transform:rotate(90deg) scale(.9)}.map-stop{width:220rpx}.map-stop--1{left:13%;top:74%}.map-stop--2{left:49%;top:58%}.map-stop--3{left:14%;top:42%}.map-stop--4{left:50%;top:24%}.map-stop--5{left:18%;top:8%}.map-stop article>span{font-size:11rpx}.map-stop h2{font-size:26rpx}.map-stop p{font-size:13rpx}.map-legend{left:13rpx;top:auto;bottom:12rpx;gap:9rpx}.map-compass{right:12rpx;bottom:10rpx}.journey-slip{grid-template-columns:auto 1fr}.journey-slip b{display:none}}
/* #endif */
</style>
