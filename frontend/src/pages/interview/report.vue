<template>
  <div class="report">
    <div class="report__scroll" style="overflow-y:auto;overflow-x:hidden;height:100%;-webkit-overflow-scrolling:touch">
      <!-- 得分概览 -->
      <div class="report__overview">
        <div class="report__score-ring">
          <div class="report__score-circle">
            <span class="report__score-value">{{ overallScore || '...' }}</span>
            <span class="report__score-label">综合得分</span>
          </div>
        </div>
        <div class="report__grade">
          <span class="report__grade-badge">{{ grade || '评估中' }}</span>
          <span class="report__grade-desc">继续保持，稳步提升！</span>
        </div>
      </div>

      <!-- 雷达图 -->
      <div class="report__card">
        <span class="report__card-title"><small>PROFILE / 01</small>能力画像</span>
        <RadarChart :dimensions="dimensions" :size="440" />
      </div>

      <!-- 各维度分析 -->
      <div class="report__card">
        <span class="report__card-title"><small>ANALYSIS / 02</small>维度分析</span>
        <div class="report__dimensions">
          <div class="report__dim-item" v-for="dim in dimensionAnalysis" :key="dim.name">
            <div class="report__dim-header">
              <span class="report__dim-name">{{ dim.name }}</span>
              <span class="report__dim-score" :style="{ color: getScoreColor(dim.score) }">{{ dim.score }}分</span>
            </div>
            <div class="report__dim-bar">
              <div class="report__dim-fill" :style="{ width: dim.score + '%', background: getScoreColor(dim.score) }"></div>
            </div>
            <span class="report__dim-suggestion">{{ dim.suggestion }}</span>
          </div>
        </div>
      </div>

      <!-- 历史对比 -->
      <div class="report__card" v-if="hasPrevious">
        <span class="report__card-title"><small>PROGRESS / 03</small>历史对比</span>
        <div class="report__dimensions">
          <div class="report__dim-item" v-for="dim in dimensionAnalysis" :key="'delta-'+dim.name">
            <div class="report__dim-header">
              <span class="report__dim-name">{{ dim.name }}</span>
              <span class="report__dim-score" :style="{ color: delta[dim.name] > 0 ? '#2E7D32' : delta[dim.name] < 0 ? '#D32F2F' : '#999' }">{{ dim.score }}分 <small v-if="delta[dim.name]">{{ delta[dim.name] > 0 ? '↑' : '↓' }}{{ Math.abs(delta[dim.name]) }}</small></span>
            </div>
          </div>
        </div>
        <div class="report__delta-summary" v-if="delta.overall_score">
          综合得分较上次{{ delta.overall_score > 0 ? '提升' : delta.overall_score < 0 ? '下降' : '持平' }}
          <strong :style="{color: delta.overall_score > 0 ? '#2E7D32' : '#D32F2F'}">{{ delta.overall_score > 0 ? '+' : '' }}{{ delta.overall_score }}分</strong>
        </div>
      </div>

      <!-- 总结建议 -->
      <div class="report__card">
        <span class="report__card-title"><small>ACTION / {{ hasPrevious ? '04' : '03' }}</small>改进建议</span>
        <div class="report__strengths">
          <span class="report__subtitle">✅ 优势</span>
          <div class="report__tag-list">
            <span class="report__tag report__tag--success" v-for="s in strengths" :key="s">{{ s }}</span>
          </div>
        </div>
        <div class="report__weaknesses">
          <span class="report__subtitle">⚠️ 待加强</span>
          <div class="report__tag-list">
            <span class="report__tag report__tag--warning" v-for="w in weaknesses" :key="w">{{ w }}</span>
          </div>
        </div>
        <div class="report__suggestion-box">
          <span class="report__suggestion-text">{{ suggestion }}</span>
        </div>
      </div>

      <!-- 操作按钮 -->
      <div class="report__actions">
        <div class="report__btn report__btn--primary" @click="practiceAgain">
          <span>再来一次</span>
        </div>
        <div class="report__btn report__btn--secondary" @click="shareReport">
          <span>复制结果</span>
        </div>
      </div>

      <div style="height: 60rpx"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import RadarChart from '@/components/radar/RadarChart.vue'
import { interviewApi } from '@/api/interview'

const overallScore = ref(0)
const grade = ref('')
const dimensions = ref<Array<{name:string;score:number}>>([])
const dimensionAnalysis = ref<Array<{name:string;score:number;suggestion:string}>>([])
const strengths = ref<string[]>([])
const weaknesses = ref<string[]>([])
const suggestion = ref('')
const delta = ref<Record<string,number>>({})
const hasPrevious = ref(false)

onLoad(async (query: any) => {
  const pid = query.practiceId || ''
  if (!pid) return
  let r: any = {}
  try { r = await interviewApi.getReport(pid) }
  catch (event: any) {
    uni.showToast({ title: event.message || '报告加载失败', icon: 'none' })
    return
  }
  overallScore.value = r.overall_score || 0
  grade.value = r.grade || (r.overall_score >= 85 ? '优秀' : r.overall_score >= 70 ? '良好' : '需努力')
  if (r.dimension_scores) {
    dimensions.value = Object.entries(r.dimension_scores).map(([k,v]) => ({name:k,score:Number(v)}))
  }
  dimensionAnalysis.value = r.dimension_analysis || []
  strengths.value = r.strengths || []
  weaknesses.value = r.weaknesses || []
  suggestion.value = r.suggestion || '请继续练习提升。'
  delta.value = r.delta || {}
  hasPrevious.value = r.has_previous || false
})

function getScoreColor(score: number): string {
  if (score >= 80) return '#2E7D32'
  if (score >= 60) return '#F57C00'
  return '#D32F2F'
}

function practiceAgain() {
  uni.redirectTo({ url: '/pages/interview/interview' })
}

function shareReport() {
  const text = `【思政情景工坊-谈话评估报告】\n综合得分：${overallScore.value}分 (${grade.value})\n${dimensionAnalysis.value.map(d=>d.name+':'+d.score+'分').join('，')}\n建议：${suggestion.value}`
  uni.setClipboardData({
    data: text,
    success: () => uni.showToast({ title: '已复制到剪贴板', icon: 'success' }),
    fail: () => uni.showToast({ title: '复制失败', icon: 'none' }),
  })
}
</script>

<style scoped>
.report { min-height: 100vh; background: var(--color-bg); }
.report__scroll { height: 100vh; }

/* Overview */
.report__overview { display: flex; flex-direction: column; align-items: center; padding: 48rpx 32rpx; background: #431a18; border-bottom:1px solid rgba(231,201,129,.3); }
.report__score-ring { margin-bottom: 16rpx; }
.report__score-circle { width: 200rpx; height: 200rpx; border-radius: 50%; border: 8rpx double rgba(231,201,129,.72); display: flex; flex-direction: column; align-items: center; justify-content: center; }
.report__score-value { font:700 64rpx var(--font-display); color: #e7c981; }
.report__score-label { font-size: 22rpx; color: rgba(255,255,255,0.8); }
.report__grade { text-align: center; }
.report__grade-badge { display: inline-block; background: rgba(255,255,255,0.2); color: #FFFFFF; font-size: 28rpx; padding: 8rpx 32rpx; border-radius: 4px; font-weight: 600; margin-bottom: 8rpx; }
.report__grade-desc { font-size: 24rpx; color: rgba(255,255,255,0.8); display: block; }

/* Cards */
.report__card { margin: 24rpx 32rpx; background: var(--color-card);
  border: 1px solid rgba(72,25,22,.12); border-radius: 2px; padding: 32rpx; box-shadow: 0 7rpx 22rpx rgba(48,32,22,.055);
  transition: box-shadow 0.2s ease; }
.report__card-title { font-family: 'STKaiti', 'Noto Serif SC', serif;
  font-size: 30rpx; font-weight: 600; color: var(--color-text); margin-bottom: 24rpx; display: block; }
.report__card-title small { display:block; margin-bottom:5rpx; font:400 15rpx var(--font-body); letter-spacing:4rpx; color:var(--color-gold); }

/* Dimensions */
.report__dim-item { margin-bottom: 24rpx; }
.report__dim-header { display: flex; justify-content: space-between; margin-bottom: 8rpx; }
.report__dim-name { font-size: 26rpx; color: var(--color-text); font-weight: 500; }
.report__dim-score { font-size: 24rpx; font-weight: 700; }
.report__dim-bar { height: 12rpx; background: var(--color-border); border-radius: 6rpx; margin-bottom: 8rpx; overflow: hidden; }
.report__dim-fill { height: 100%; border-radius: 6rpx; transition: width 0.6s ease; }
.report__dim-suggestion { font-size: 22rpx; color: var(--color-text-muted); line-height: 1.5; }

/* Strengths & Weaknesses */
.report__subtitle { font-size: 24rpx; font-weight: 600; color: var(--color-text-secondary); display: block; margin-bottom: 12rpx; }
.report__tag-list { display: flex; flex-wrap: wrap; gap: 12rpx; margin-bottom: 20rpx; }
.report__tag { padding: 6rpx 20rpx; border-radius: 4px; font-size: 22rpx; font-weight: 500; }
.report__tag--success { background: #E8F5E9; color: var(--color-primary-light); }
.report__tag--warning { background: #FFF3E0; color: #F57C00; }
.report__suggestion-box { background: var(--color-bg); border-radius: 4px; padding: 24rpx; border-left: 6rpx solid #C41E1A; }
.report__delta-summary { text-align: center; margin-top: 16rpx; padding: 12rpx; background: rgba(139,26,26,0.04); border-radius: 4px; font-size: 24rpx; color: var(--color-text-secondary); }
.report__suggestion-text { font-size: 24rpx; color: var(--color-text-secondary); line-height: 1.6; }

/* Actions */
.report__actions { display: flex; gap: 20rpx; padding: 0 32rpx; }
.report__btn { flex: 1; height: 88rpx; border-radius: 2rpx; display: flex; align-items: center; justify-content: center; font-size: 25rpx; font-weight: 600; }
.report__btn--primary { background: var(--color-primary); color: #FFFFFF; }
.report__btn--secondary { background: var(--color-card);
  border-left: 3px solid var(--color-primary-light); color: var(--color-primary-light); border: 2rpx solid #C41E1A; }
</style>
