<template>
  <div class="radar-chart">
    <div v-if="dimensions.length" class="radar-chart__canvas-wrap" :style="{ width: canvasSize + 'px' }">
      <canvas
        :id="canvasId"
        :canvas-id="canvasId"
        :width="canvasSize"
        :height="canvasSize"
        class="radar-chart__canvas"
      />
    </div>
    <div v-else class="radar-chart__empty">暂无能力维度数据</div>
    <div v-if="!hideLabels" class="radar-chart__labels">
      <div v-for="(dim, i) in dimensions" :key="i" class="radar-chart__label">
        <div class="radar-chart__label-heading">
          <div class="radar-chart__label-dot" :style="{ background: getScoreColor(dim.score, i) }" />
          <span class="radar-chart__label-text">{{ dim.name }}</span>
          <strong :style="{ color: getScoreColor(dim.score, i) }">{{ Math.round(dim.score) }}</strong>
        </div>
        <div class="radar-chart__label-track"><span :style="{ width: normalizedScore(dim.score) + '%', background: getScoreColor(dim.score, i) }"></span></div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, getCurrentInstance, nextTick, onMounted, watch } from 'vue'

const props = withDefaults(defineProps<{
  dimensions: Array<{ name: string; score: number }>
  size?: number
  maxScore?: number
  hideLabels?: boolean
  colors?: string[]
}>(), {
  size: 500,
  maxScore: 100,
  colors: () => ['#C41E1A'],
})

const instance = getCurrentInstance()
const canvasId = `radar-${Math.random().toString(36).slice(2, 9)}`
const canvasSize = computed(() => {
  // rpx is based on a 750-wide design canvas. Capping desktop width avoids
  // producing a canvas wider than the report card while keeping MP responsive.
  const width = Math.min(uni.getSystemInfoSync().windowWidth || 375, 750)
  return Math.min(Math.round(props.size * width / 750), width - 48)
})

function getColor(index: number) {
  return props.colors[index % props.colors.length]
}

function normalizedScore(score: number) {
  return Math.max(0, Math.min(Math.round(Number(score) / props.maxScore * 100), 100))
}

function getScoreColor(score: number, index = 0) {
  const value = normalizedScore(score)
  if (value >= 85) return '#2f6b4f'
  if (value >= 70) return getColor(index)
  if (value >= 60) return '#b26a24'
  return '#a83a32'
}

function drawRadar() {
  nextTick(() => {
    const values = props.dimensions
    if (!values.length) return
    const ctx = uni.createCanvasContext(canvasId, instance?.proxy as any)
    const width = canvasSize.value
    const center = width / 2
    const radius = width * 0.36
    const step = Math.PI * 2 / values.length
    const start = -Math.PI / 2
    ctx.clearRect(0, 0, width, width)

    for (let level = 1; level <= 5; level += 1) {
      const ring = radius * level / 5
      ctx.beginPath()
      values.forEach((_, index) => {
        const angle = start + index * step
        const x = center + ring * Math.cos(angle)
        const y = center + ring * Math.sin(angle)
        index ? ctx.lineTo(x, y) : ctx.moveTo(x, y)
      })
      ctx.closePath()
      ctx.setFillStyle(level % 2 ? 'rgba(143,32,27,.025)' : 'rgba(47,107,79,.025)')
      ctx.fill()
      ctx.setStrokeStyle(level === 5 ? '#CFC0AD' : '#E6DCCF')
      ctx.setLineWidth(level === 5 ? 1.5 : 1)
      ctx.stroke()
    }

    values.forEach((value, index) => {
      const angle = start + index * step
      const x = center + radius * Math.cos(angle)
      const y = center + radius * Math.sin(angle)
      ctx.beginPath(); ctx.moveTo(center, center); ctx.lineTo(x, y)
      ctx.setStrokeStyle('#DED2C2'); ctx.setLineWidth(1); ctx.stroke()
    })

    ctx.beginPath()
    values.forEach((value, index) => {
      const ratio = Math.max(0, Math.min(Number(value.score) / props.maxScore, 1))
      const angle = start + index * step
      const x = center + radius * ratio * Math.cos(angle)
      const y = center + radius * ratio * Math.sin(angle)
      index ? ctx.lineTo(x, y) : ctx.moveTo(x, y)
    })
    ctx.closePath(); ctx.setFillStyle('rgba(143,32,27,.18)'); ctx.setStrokeStyle('#8F201B'); ctx.setLineWidth(3); ctx.fill(); ctx.stroke()
    values.forEach((value, index) => {
      const ratio = normalizedScore(value.score) / 100
      const angle = start + index * step
      const x = center + radius * ratio * Math.cos(angle)
      const y = center + radius * ratio * Math.sin(angle)
      ctx.beginPath(); ctx.arc(x, y, Math.max(4, width * .012), 0, Math.PI * 2)
      ctx.setFillStyle(getScoreColor(value.score, index)); ctx.fill()
      ctx.setStrokeStyle('#FFFDF8'); ctx.setLineWidth(2); ctx.stroke()
    })
    ctx.draw()
  })
}

onMounted(drawRadar)
watch([() => props.dimensions, canvasSize], drawRadar, { deep: true })
</script>

<style scoped>
.radar-chart{display:flex;flex-direction:column;align-items:center}.radar-chart__canvas-wrap{max-width:100%;aspect-ratio:1;margin:-16rpx auto -8rpx}.radar-chart__canvas{display:block;width:100%;height:100%}.radar-chart__empty{width:100%;box-sizing:border-box;padding:72rpx 24rpx;border:1rpx dashed #d8cbbb;border-radius:16rpx;background:#faf6ef;color:#9a8d7e;text-align:center}.radar-chart__labels{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14rpx;width:100%;margin-top:8rpx}.radar-chart__label{padding:15rpx 17rpx;border:1rpx solid #ece2d5;border-radius:14rpx;background:#fbf7f0}.radar-chart__label-heading{display:flex;align-items:center;gap:9rpx}.radar-chart__label-dot{width:13rpx;height:13rpx;flex:none;border-radius:50%;box-shadow:0 0 0 5rpx rgba(143,32,27,.06)}.radar-chart__label-text{flex:1;min-width:0;font-size:21rpx;color:#5f554b;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.radar-chart__label-heading strong{font-family:Georgia,serif;font-size:24rpx}.radar-chart__label-track{height:6rpx;margin-top:10rpx;overflow:hidden;border-radius:999rpx;background:#e8dfd3}.radar-chart__label-track span{display:block;height:100%;border-radius:inherit;transition:width .5s ease}/* #ifndef H5 */@media (max-width: 360px){.radar-chart__labels{grid-template-columns:1fr}}/* #endif *//* #ifdef H5 */@container (max-width: 360px){.radar-chart__labels{grid-template-columns:1fr}}/* #endif */
</style>
