<template>
  <!-- #ifdef H5 -->
  <div class="app-shell" :class="{ 'app-shell--bare': route.meta.immersive || route.path === '/pages/login/login', 'app-shell--locked': route.meta.lockViewport }">
    <div class="app-frame" :class="{ 'app-frame--immersive': route.meta.immersive, 'app-frame--locked': route.meta.lockViewport }">
      <NavBar
        v-if="!route.meta.hideNav"
        :title="String(route.meta.title || '思政情景工坊')"
        :showBack="route.meta.tab === undefined && route.path !== '/pages/index/index' && route.path !== '/pages/login/login'"
        :statusBarHeight="0"
        :root="route.meta.tab !== undefined"
      />
      <div
        class="page-content"
        :class="{
          'has-tab': !route.meta.hideTab,
          'page-content--locked': route.meta.lockViewport,
          [`page-content--${String(route.meta.layout || 'dashboard')}`]: !route.meta.immersive,
        }"
      >
        <router-view v-slot="{ Component }">
          <Transition name="page" mode="out-in">
            <component :is="Component" />
          </Transition>
        </router-view>
      </div>
    </div>
    <!-- TabBar 放在 .app-frame 之外：.app-frame 的 container-type 会让 fixed 定位
         相对容器而不是视口，导致滚动时长内容 TabBar 被带着滚出屏幕。 -->
    <TabBar v-if="!route.meta.hideTab" />
  </div>
  <!-- #endif -->
  <!-- #ifndef H5 -->
  <view />
  <!-- #endif -->
</template>

<script setup lang="ts">
// #ifdef H5
import { useRoute } from 'vue-router'
import NavBar from './components/layout/NavBar.vue'
import TabBar from './components/layout/TabBar.vue'

const route = useRoute()
// #endif
</script>

<style>
:root {
  --font-display: 'STSong', 'Songti SC', 'Noto Serif SC', serif;
  --font-body: 'PingFang SC', 'Microsoft YaHei', sans-serif;
  --color-bg: #f1ede4;
  --color-paper: #fffdf7;
  --color-card: #fffdf7;
  --color-border: #ded5c7;
  --color-primary: #7f211d;
  --color-primary-light: #a82d27;
  --color-primary-dark: #481916;
  --color-accent: #b58a3f;
  --color-green: #315b49;
  --color-text: #28231e;
  --color-text-secondary: #675d53;
  --color-text-muted: #968a7d;
  --radius-card: 18rpx;
  --shadow-card: 0 12rpx 34rpx rgba(68, 48, 30, .07);
  --shadow-card-hover: 0 18rpx 48rpx rgba(68, 48, 30, .12);
  --page-gutter: 28rpx;
  --tabbar-space: 116rpx;
  --desktop-dashboard: 1180px;
  --desktop-workspace: 1280px;
  --desktop-reading: 800px;
  --page-title-size: clamp(30px, 2.5vw, 38px);
  --section-title-size: clamp(21px, 2vw, 28px);
}

page, body, #app { margin: 0; padding: 0; width: 100%; min-height: 100vh; }
html, body { overflow-x: hidden; }
body {
  font-family: var(--font-body);
  color: var(--color-text);
  font-size: 26rpx;
  line-height: 1.65;
  -webkit-font-smoothing: antialiased;
  background: #d9d1c4;
}

.app-shell { width: 100%; min-height: 100vh; display:flex;justify-content:center;background: radial-gradient(circle at 50% -10%, #eee8dc, #d7cec0 58%, #cbc0b1); }
.app-frame { container-type:inline-size;width: 100%; max-width:480px;min-height: 100vh; position: relative; overflow-x: hidden; background: var(--color-bg);box-shadow:0 0 80px rgba(50,33,21,.18); }
.app-shell--locked,.app-frame--locked{height:100dvh;min-height:0;overflow:hidden}
.app-frame--immersive { max-width:none;height: 100vh; overflow: hidden; background: #0d100e;box-shadow:none; }
.app-frame--immersive .page-content { height: 100vh; overflow: hidden; max-width:none; }
.page-content { min-height: 100vh; position: relative; z-index: 1; background: transparent; }
.page-content--locked{height:calc(100dvh - 92rpx);min-height:0;overflow:hidden}
.page-content--dashboard,.page-content--workspace,.page-content--reading{width:100%;max-width:none;margin:0 auto;background:var(--color-bg);box-sizing:border-box}
.page-content.has-tab { padding-bottom: var(--tabbar-space); }

h1, h2, h3, .section-title { font-family: var(--font-display); }
button { border: 0; outline: 0; margin: 0; background: none; padding: 0; font: inherit; cursor: pointer; }
button, .clickable, [role='button'] { -webkit-tap-highlight-color: transparent; }
button:active, .clickable:active { transform: translateY(1px); }
::-webkit-scrollbar { width: 0; height: 0; }

input, textarea {
  width: 100%; box-sizing: border-box; outline: none; border: 1rpx solid #e2d8ca;
  border-radius: 12rpx; background: #f7f2e9; padding: 17rpx 20rpx;
  color: var(--color-text); font: 24rpx/1.6 var(--font-body); transition: border-color .2s, background .2s, box-shadow .2s;
}
input::placeholder, textarea::placeholder { color: #aa9f92; }
input:focus, textarea:focus { border-color: rgba(127,33,29,.5); background: #fffdf8; box-shadow: 0 0 0 5rpx rgba(127,33,29,.06); }
textarea { min-height: 90rpx; resize: vertical; }

.card-accent, .list-card {
  position: relative; overflow: hidden; border: 1rpx solid var(--color-border); border-radius: var(--radius-card);
  background: var(--color-paper); box-shadow: var(--shadow-card);
}
.card-accent::before, .list-card::before { content: ''; position: absolute; left: 0; top: 0; width: 5rpx; height: 46rpx; background: var(--color-primary); }
.card-accent { padding: 26rpx; }
.list-card { margin-bottom: 16rpx; padding: 24rpx 26rpx; }
.card-accent:active, .list-card:active { box-shadow: var(--shadow-card-hover); }

.section-title { display: flex; align-items: center; gap: 12rpx; margin: 0 0 18rpx; color: var(--color-text); font-size: 29rpx; font-weight: 700; }
.section-title::before { content: ''; width: 24rpx; height: 5rpx; border-radius: 999rpx; background: var(--color-primary); }
.pill { display: inline-flex; align-items: center; padding: 7rpx 16rpx; border: 1rpx solid #ddcfc0; border-radius: 999rpx; background: #f7f0e6; color: #795f4a; font-size: 19rpx; }
.pill--active { border-color: var(--color-primary); background: var(--color-primary); color: #fff; }
.filter-bar { margin: 0 var(--page-gutter) 18rpx; padding: 8rpx; border: 1rpx solid #dfd5c7; border-radius: 16rpx; background: rgba(255,253,247,.76); }

.input-bar { display: flex; align-items: center; gap: 12rpx; padding: 18rpx var(--page-gutter); border-top: 1rpx solid var(--color-border); background: rgba(255,253,247,.96); }
.input-bar input, .input-bar textarea { flex: 1; }
.input-bar button, .input-bar .send-btn { flex: none; min-width: 104rpx; height: 72rpx; border-radius: 12rpx; background: var(--color-primary); color: #fff; font-size: 23rpx; font-weight: 600; }
.input-bar button:disabled { opacity: .42; }
.search-input { width: 100%; }
.gold-dot { display: inline-block; width: 7rpx; height: 7rpx; margin: 0 8rpx; border-radius: 50%; background: var(--color-accent); vertical-align: middle; }

.page-enter-active { transition: opacity .22s ease; }
.page-leave-active { transition: opacity .12s ease; }
.page-enter-from { opacity: 0; }
.page-leave-to { opacity: 0; }
.fade-enter-active, .fade-leave-active { transition: opacity .2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

/* #ifdef H5 */
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { scroll-behavior: auto!important; transition-duration: .01ms!important; animation-duration: .01ms!important; } }
@media(max-width:480px){.app-frame{max-width:none;box-shadow:none}}
/* #endif */
</style>
