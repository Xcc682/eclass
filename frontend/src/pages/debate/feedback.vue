<template>
  <div class="feedback">
    <div class="feedback__score">{{ overallScore }}<span>分</span></div>
    <div class="feedback__grade">{{ grade }}</div>

    <div class="feedback__card" v-if="dimAnalysis.length">
      <span class="feedback__card-title">每维度建议</span>
      <div class="feedback__dim-item" v-for="da in dimAnalysis" :key="da.name">
        <div class="feedback__dim-header"><span>{{ da.name }}</span><span>{{ da.score }}分</span></div>
        <div class="feedback__dim-bar"><div class="feedback__dim-fill" :style="{width:da.score+'%',background:da.score>=80?'#2E7D32':da.score>=60?'#F57C00':'#D32F2F'}"></div></div>
        <span class="feedback__dim-suggestion">{{ da.suggestion }}</span>
      </div>
    </div>

    <div class="feedback__card">
      <span class="feedback__card-title">维度评分 <small>DIMENSIONS</small></span>
      <div class="feedback__dim" v-for="(score, name) in dimensions" :key="name">
        <div class="feedback__dim-header"><span>{{ name }}</span><span>{{ score }}分</span></div>
        <div class="feedback__dim-bar"><div class="feedback__dim-fill" :style="{width:score+'%',background:score>=80?'#C41E1A':score>=60?'#F57C00':'#D32F2F'}"></div></div>
      </div>
    </div>

    <div class="feedback__card">
      <span class="feedback__card-title">论证优势 <small>STRENGTHS</small></span>
      <span class="feedback__tag" v-for="s in strengths" :key="s" style="background:#E8F5E9;color:#2E7D32;">{{ s }}</span>
    </div>

    <div class="feedback__card">
      <span class="feedback__card-title">待改进 <small>FOCUS</small></span>
      <span class="feedback__tag" v-for="w in weaknesses" :key="w" style="background:#FFF3E0;color:#F57C00;">{{ w }}</span>
    </div>

    <div class="feedback__card">
      <span class="feedback__card-title">下一步建议 <small>ACTION</small></span>
      <span class="feedback__text">{{ suggestion }}</span>
    </div>

    <div class="feedback__actions">
      <div class="feedback__btn feedback__btn--primary" @click="retrySameTopic">再辩同题</div>
      <div class="feedback__btn feedback__btn--secondary" @click="switchStance">换立场再辩</div>
      <div class="feedback__btn feedback__btn--ghost" @click="backToList">返回列表</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { debateApi, type DebateFeedback } from '@/api/debate'

const overallScore = ref(0)
const grade = ref('')
const dimensions = ref<Record<string,number>>({})
const dimAnalysis = ref<Array<{name:string;score:number;suggestion:string}>>([])
const strengths = ref<string[]>([])
const weaknesses = ref<string[]>([])
const suggestion = ref('')
const topicId = ref('')
const topicTitle = ref('')
const stance = ref('pro')

onLoad(async (query: any) => {
  const sid = query.sessionId || 'd_1'; topicId.value = query.topicId || ''; topicTitle.value = decodeURIComponent(query.topic || '辩论'); stance.value = query.stance || 'pro'
  try {
    const fb = await debateApi.getFeedback(sid)
    overallScore.value = fb.overall_score
    grade.value = fb.overall_score >= 85 ? '优秀' : fb.overall_score >= 70 ? '良好' : '需努力'
    dimensions.value = fb.dimension_scores; dimAnalysis.value = fb.dimension_analysis || []
    strengths.value = fb.strengths
    weaknesses.value = fb.weaknesses
    suggestion.value = fb.suggestion
  } catch(e) { console.error(e) }
})
function retrySameTopic() { uni.redirectTo({ url: `/pages/debate/arena?topicId=${topicId.value}&stance=${stance.value}&title=${encodeURIComponent(topicTitle.value)}` }) }
function switchStance() { const s = stance.value === "pro" ? "con" : "pro"; uni.redirectTo({ url: `/pages/debate/arena?topicId=${topicId.value}&stance=${s}&title=${encodeURIComponent(topicTitle.value)}` }) }
function backToList() { uni.redirectTo({ url: "/pages/debate/debate" }) }
</script>

<style scoped>
.feedback { min-height: 100vh; background: linear-gradient(#431a18 0 300rpx,var(--color-bg) 300rpx); padding: 46rpx 32rpx 60rpx; }
.feedback__score { display:grid;place-items:center;align-content:center;width:190rpx;height:190rpx;margin:0 auto;text-align: center; font:700 60rpx var(--font-display); color:#e7c981;border:7rpx double rgba(231,201,129,.7);border-radius:50%; }
.feedback__score span { font-size: 24rpx; color: var(--color-text-muted); }
.feedback__grade { text-align: center; font:700 28rpx var(--font-display); color:#fff8e9; margin:14rpx 0 32rpx; }
.feedback__card { background: var(--color-card);
  border:1px solid rgba(72,25,22,.12); border-radius: 2px; padding: 28rpx; margin-bottom: 20rpx; box-shadow:0 7rpx 22rpx rgba(48,32,22,.055); }
.feedback__card-title { font-family: 'STKaiti', 'Noto Serif SC', serif;
  font-size: 28rpx; font-weight: 600; color: var(--color-text); display: block; margin-bottom: 16rpx; }
.feedback__card-title small{float:right;font:400 14rpx var(--font-body);letter-spacing:2rpx;color:var(--color-gold)}
.feedback__dim { margin-bottom: 16rpx; }
.feedback__dim-header { display: flex; justify-content: space-between; font-size: 24rpx; margin-bottom: 6rpx; }
.feedback__dim-bar { height: 10rpx; background: var(--color-border); border-radius: 5rpx; overflow: hidden; }
.feedback__dim-item { margin-bottom: 16rpx; }
.feedback__dim-suggestion { font-size: 22rpx; color: var(--color-text-muted); line-height: 1.5; display: block; margin-top: 4rpx; }
.feedback__dim-fill { height: 100%; border-radius: 5rpx; transition: width 0.6s; }
.feedback__tag { display: inline-block; padding: 6rpx 16rpx; border-radius: 4px; font-size: 22rpx; margin: 4rpx 8rpx 4rpx 0; }
.feedback__text { font-size: 24rpx; color: var(--color-text-secondary); line-height: 1.6; }
.feedback__actions { display: flex; gap: 16rpx; padding: 0 32rpx; margin-top: 24rpx; }
.feedback__btn { flex: 1; height: 88rpx; border-radius: 2rpx; display: flex; align-items: center; justify-content: center; font-size: 25rpx; font-weight: 600; cursor: pointer; }
.feedback__btn--primary { background:var(--color-primary); color: #FFF; }
.feedback__btn--secondary { background: var(--color-card);
  border-left: 3px solid var(--color-primary-light); color: var(--color-primary-light); border: 2rpx solid var(--color-primary-light); }
</style>
