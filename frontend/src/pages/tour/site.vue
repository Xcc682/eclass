<template>
  <div class="immersive-page">
    <ImmersiveBookReader v-if="book" :book="book" @completed="book.progress.completed = true" />
    <div v-else class="book-loader">
      <div class="book-loader__compass"><i></i><b>✦</b></div>
      <span>{{ loadError ? 'ROUTE UNAVAILABLE' : 'PREPARING FIELD NOTES' }}</span>
      <h1>{{ loadError ? '图志暂时无法展开' : '正在抵达研学现场' }}</h1>
      <p>{{ loadError || '正在校准当代地标、历史之窗与研学记录…' }}</p>
      <button v-if="loadError" @click="loadBook">重新展开</button>
      <button v-else class="book-loader__back" @click="goBack">取消</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { immersiveApi, type ImmersiveBook } from '@/api/immersive'
import ImmersiveBookReader from '@/components/immersive/ImmersiveBookReader.vue'

const book = ref<ImmersiveBook | null>(null)
const bookId = ref('tour-1')
const loadError = ref('')

onLoad((query: any) => {
  bookId.value = query.bookId || `tour-${query.id || '1'}`
  loadBook()
})

async function loadBook() {
  book.value = null; loadError.value = ''
  try { book.value = await immersiveApi.getBook(bookId.value) }
  catch (error: any) { loadError.value = error.message || '网络连接异常，请稍后重试' }
}
function goBack() { uni.navigateBack() }
</script>

<style scoped>
.immersive-page { position:fixed; inset:0; z-index:100; color:#f5ead2; background:#101510; }.book-loader { position:absolute; inset:0; display:flex; flex-direction:column; align-items:center;justify-content:center;padding:40rpx;text-align:center;background:radial-gradient(circle at 50% 43%,#385344,transparent 32%),linear-gradient(135deg,#0a1110,#1e3027,#0b100d); }.book-loader::before { content:'';position:absolute;inset:0;opacity:.12;background-image:linear-gradient(25deg,transparent 48%,#dfc98d 49% 50%,transparent 51%),linear-gradient(155deg,transparent 48%,#dfc98d 49% 50%,transparent 51%);background-size:130rpx 100rpx; }.book-loader__compass { position:relative;width:115rpx;height:115rpx;border:2rpx solid #b79558;border-radius:50%;animation:spinIn 1.4s ease both; }.book-loader__compass::before,.book-loader__compass::after { content:'';position:absolute;background:#b79558;opacity:.55; }.book-loader__compass::before { left:50%;top:7rpx;bottom:7rpx;width:1px; }.book-loader__compass::after { top:50%;left:7rpx;right:7rpx;height:1px; }.book-loader__compass b { position:absolute;inset:0;display:grid;place-items:center;color:#e1bf7a;font-size:48rpx; }.book-loader>span { margin-top:29rpx;color:#c3a366;font-size:16rpx;letter-spacing:6rpx; }.book-loader h1 { margin:10rpx 0 5rpx;font:700 39rpx var(--font-display);letter-spacing:3rpx; }.book-loader p { margin:0 0 25rpx;color:rgba(255,241,212,.54);font-size:20rpx; }.book-loader button { position:relative;padding:16rpx 27rpx;border:1px solid rgba(229,196,126,.35);color:#f2dfbb;background:rgba(0,0,0,.2); }.book-loader__back { opacity:.6; } @keyframes spinIn{from{opacity:0;transform:rotate(-90deg) scale(.7)}to{opacity:1;transform:none}}
</style>
