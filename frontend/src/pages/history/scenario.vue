<template>
  <div class="immersive-page">
    <ImmersiveBookReader v-if="book" :book="book" @completed="book.progress.completed = true" />
    <div v-else class="book-loader">
      <div class="book-loader__seal">史</div>
      <span>{{ loadError ? 'ARCHIVE UNAVAILABLE' : 'OPENING ARCHIVE' }}</span>
      <h1>{{ loadError ? '书卷暂时无法打开' : '正在展开历史现场' }}</h1>
      <p>{{ loadError || '正在装订画面、线索与史料来源…' }}</p>
      <button v-if="loadError" @click="loadBook">重新打开</button>
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
const bookId = ref('history-1')
const loadError = ref('')

onLoad((query: any) => {
  bookId.value = query.bookId || `history-${query.id || '1'}`
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
.immersive-page { position:fixed; inset:0; z-index:100; color:#f5ead2; background:#111310; }
.book-loader { position:absolute; inset:0; display:flex; flex-direction:column; align-items:center; justify-content:center; padding:40rpx; text-align:center; background:radial-gradient(circle at 50% 45%,#4a3026,transparent 30%),linear-gradient(135deg,#0c100e,#231a16,#0d0f0d); }
.book-loader::before { content:''; position:absolute; inset:0; opacity:.15; background-image:repeating-linear-gradient(90deg,transparent 0 90rpx,rgba(235,209,151,.12) 91rpx 92rpx); }.book-loader__seal { display:grid; place-items:center; width:105rpx;height:105rpx;border:5rpx double #b18a4d;border-radius:50%;color:#d8b56e;font:700 44rpx var(--font-display);animation:breathe 1.8s infinite alternate; }.book-loader>span { margin-top:29rpx;color:#bd9652;font-size:16rpx;letter-spacing:6rpx; }.book-loader h1 { margin:10rpx 0 5rpx;font:700 39rpx var(--font-display);letter-spacing:3rpx; }.book-loader p { margin:0 0 25rpx;color:rgba(255,241,212,.54);font-size:20rpx; }.book-loader button { position:relative;padding:16rpx 27rpx;border:1px solid rgba(229,196,126,.35);color:#f2dfbb;background:rgba(0,0,0,.2); }.book-loader__back { opacity:.6; } @keyframes breathe{to{transform:scale(1.05);box-shadow:0 0 40rpx rgba(196,143,61,.23)}}
</style>
