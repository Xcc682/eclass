<template>
  <div class="interview">
    <header class="interview-hero">
      <div class="interview-hero__folio"><span>ORGANIZATION TALK · 01</span><span>入党谈话模拟室</span></div>
      <div class="interview-hero__mark">谈</div>
      <h1>把每一次回答，<br />变成一次真诚的自我审视</h1>
      <p>AI 将以不同谈话角色追问你的入党动机、理论理解与行动选择。</p>
      <div class="interview-hero__stats">
        <div><strong>{{ completedCount }}</strong><span>完成练习</span></div>
        <div><strong>{{ avgScore }}</strong><span>平均得分</span></div>
        <div><strong>{{ historyCount }}</strong><span>谈话档案</span></div>
      </div>
    </header>

    <main class="interview__main">
      <section class="talk-guide"><span>进入谈话前</span><p>没有标准套话。结合真实经历回答，AI 会根据表达继续追问，并在结束后生成能力画像与逐维建议。</p></section>

      <section v-if="history.length" class="training-history">
        <div class="training-history__head"><div><span>TALK ARCHIVE</span><h2>最近谈话档案</h2></div><small>旧版档案不参与当前成长统计</small></div>
        <article v-for="item in history.slice(0,4)" :key="item.id" @click="openHistory(item)">
          <div><strong>{{ item.scenario_title }}</strong><text>{{ item.is_legacy ? '旧版档案' : statusLabel(item.status) }} · 已完成 {{ historyAnswered(item) }}/{{ item.total_questions || 6 }}</text></div>
          <b>{{ historyHasReport(item) ? `${item.score ?? '—'} 分` : item.status==='in_progress' ? '继续 →' : '查看 →' }}</b>
        </article>
      </section>

      <div class="interview__filters">
        <button v-for="filter in filters" :key="filter.key" :class="{ active: activeFilter === filter.key }" @click="activeFilter = filter.key">{{ filter.label }}</button>
      </div>

      <section class="interview__heading"><div><span>ROOM LIST</span><h2>选择谈话场景</h2></div><p>{{ filteredScenarios.length }} 间谈话室</p></section>
      <div v-if="loading" class="interview__state">正在准备谈话室…</div>
      <div v-else class="interview__list">
        <article v-for="(scenario, index) in filteredScenarios" :key="scenario.id" class="talk-room" @click="startPractice(scenario)">
          <div class="talk-room__number">{{ String(index + 1).padStart(2, '0') }}</div>
          <div class="talk-room__content">
            <div class="talk-room__meta"><span>{{ difficultyLabel(scenario.difficulty) }}难度</span><span>{{ scenario.estimated_duration || 15 }} MIN</span></div>
            <h3>{{ scenario.title }}</h3><p>{{ scenario.description }}</p>
            <div class="talk-room__role"><i>{{ scenario.ai_role_name.slice(0, 1) }}</i><div><span>本场谈话人</span><strong>{{ scenario.ai_role_name }} · {{ scenario.ai_role_title }}</strong></div></div>
          </div>
          <div class="talk-room__footer"><span>{{ scenario.best_score ? `最佳 ${scenario.best_score} 分` : '尚未练习' }}</span><b>进入谈话 →</b></div>
        </article>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { interviewApi, type InterviewHistoryItem, type InterviewScenario } from '@/api/interview'
import { userApi } from '@/api/user'

const completedCount = ref(0), historyCount = ref(0), avgScore = ref<number | string>('—')
const activeFilter = ref('all'), loading = ref(true)
const filters = [{ key: 'all', label: '全部场景' },{ key: 'beginner', label: '初级' },{ key: 'intermediate', label: '中级' },{ key: 'advanced', label: '高级' }]
const scenarios = ref<InterviewScenario[]>([])
const history = ref<InterviewHistoryItem[]>([])
const filteredScenarios = computed(() => activeFilter.value === 'all' ? scenarios.value : scenarios.value.filter(item => item.difficulty === activeFilter.value))
function difficultyLabel(value: string) { return ({ beginner: '基础', intermediate: '进阶', advanced: '深度', random: '随机' } as Record<string,string>)[value] || value }
function statusLabel(value:string){return ({in_progress:'进行中',awaiting_report:'待生成报告',completed:'已完成',abandoned:'已归档'} as Record<string,string>)[value]||value}
function historyAnswered(item:InterviewHistoryItem){return item.answered_count ?? item.rounds ?? 0}
function historyHasReport(item:InterviewHistoryItem){return item.has_report ?? (item.status==='completed'&&item.score!=null)}
function openHistory(item:InterviewHistoryItem){
  if(historyHasReport(item))return uni.navigateTo({url:`/pages/interview/report?practiceId=${item.id}`})
  if(item.is_legacy)return uni.showToast({title:'这条旧版记录没有可用报告',icon:'none'})
  if(item.status==='in_progress'||item.status==='awaiting_report')return uni.navigateTo({url:`/pages/interview/practice?practiceId=${item.id}`})
}
function openPractice(scenario: InterviewScenario, restart = false) {
  uni.navigateTo({ url: `/pages/interview/practice?scenarioId=${scenario.id}&restart=${restart ? 1 : 0}&title=${encodeURIComponent(scenario.title)}&roleName=${encodeURIComponent(scenario.ai_role_name)}&roleTitle=${encodeURIComponent(scenario.ai_role_title)}` })
}
function startPractice(scenario: InterviewScenario) {
  if (!scenario.has_active_practice) return openPractice(scenario)
  uni.showModal({
    title: '发现未完成谈话',
    content: '可以从上次停下的位置继续，也可以重新开始本场训练。',
    confirmText: '继续上次',
    cancelText: '重新开始',
    success: result => openPractice(scenario, !result.confirm),
  })
}
onMounted(async () => { try { const [rows,growth,archive] = await Promise.all([interviewApi.getScenarios(),userApi.getGrowth(),interviewApi.getHistory()]); scenarios.value=rows||[];history.value=archive||[]; completedCount.value=growth.total_interviews; historyCount.value=history.value.filter(historyHasReport).length; avgScore.value=growth.average_interview_score ?? '—' } catch(error:any) { uni.showToast({title:error.message||'场景加载失败',icon:'none'}) } finally { loading.value=false } })
</script>

<style scoped>
.interview { min-height:100vh; padding-bottom:65rpx; background:var(--color-bg); }.interview-hero { position:relative; overflow:hidden; padding:55rpx var(--page-gutter) 42rpx; color:#fff8e9; background:#4a1917; }.interview-hero::before { content:''; position:absolute; width:360rpx; height:360rpx; right:-120rpx; top:30rpx; border:1px solid rgba(231,201,129,.14); border-radius:50%; box-shadow:0 0 0 35rpx rgba(231,201,129,.035),0 0 0 70rpx rgba(231,201,129,.025); }.interview-hero__folio { display:flex; justify-content:space-between; position:relative; font-size:17rpx; letter-spacing:3rpx; color:#e7c981; }.interview-hero__mark { display:grid; place-items:center; position:absolute; right:50rpx; top:105rpx; width:104rpx; height:104rpx; border:4rpx double rgba(231,201,129,.58); border-radius:50%; color:#e7c981; font:700 35rpx var(--font-display); transform:rotate(7deg); }.interview-hero h1 { position:relative; width:76%; margin:65rpx 0 18rpx; font:700 48rpx/1.28 var(--font-display); letter-spacing:2rpx; }.interview-hero > p { width:76%; margin:0; font-size:21rpx; line-height:1.7; color:rgba(255,248,233,.65); }.interview-hero__stats { display:flex; margin-top:38rpx; border-top:1px solid rgba(231,201,129,.25); border-bottom:1px solid rgba(231,201,129,.18); }.interview-hero__stats div { flex:1; padding:17rpx 0; border-right:1px solid rgba(231,201,129,.18); }.interview-hero__stats div:last-child { border:0; }.interview-hero__stats strong,.interview-hero__stats span { display:block; }.interview-hero__stats strong { font:700 29rpx var(--font-display); color:#e7c981; }.interview-hero__stats span { margin-top:3rpx; font-size:16rpx; color:rgba(255,248,233,.5); }
.interview__main { padding:0 var(--page-gutter); }.talk-guide { margin:-1rpx 0 34rpx; padding:25rpx 27rpx; background:#fffaf0; border:1px solid rgba(72,25,22,.12); border-top:0; }.talk-guide span { font:700 23rpx var(--font-display); color:var(--color-primary); }.talk-guide p { margin:7rpx 0 0; font-size:19rpx; line-height:1.6; color:var(--color-text-muted); }.interview__filters { display:flex; gap:11rpx; overflow-x:auto; }.interview__filters button { flex:none; margin:0; padding:13rpx 22rpx; border:1px solid rgba(72,25,22,.14); border-radius:2rpx; color:var(--color-text-secondary); background:rgba(255,253,247,.75); font-size:20rpx; line-height:1.2; }.interview__filters button.active { color:white; background:var(--color-primary); border-color:var(--color-primary); }.interview__heading { display:flex; justify-content:space-between; align-items:end; margin:34rpx 0 23rpx; padding-bottom:17rpx; border-bottom:1px solid rgba(72,25,22,.16); }.interview__heading span { font-size:16rpx; letter-spacing:4rpx; color:var(--color-gold); }.interview__heading h2 { margin:5rpx 0 0; font:700 33rpx var(--font-display); color:var(--color-text); }.interview__heading p { margin:0; font-size:18rpx; color:var(--color-text-muted); }.interview__state { padding:70rpx; text-align:center; color:var(--color-text-muted); }.talk-room { position:relative; display:grid; grid-template-columns:58rpx 1fr; margin-bottom:20rpx; background:var(--color-card); border:1px solid rgba(72,25,22,.11); box-shadow:0 7rpx 23rpx rgba(47,32,23,.06); }.talk-room__number { padding-top:27rpx; text-align:center; font:700 19rpx var(--font-display); color:var(--color-primary); border-right:1px solid rgba(72,25,22,.1); }.talk-room__content { padding:24rpx 24rpx 20rpx; }.talk-room__meta { display:flex; justify-content:space-between; font-size:16rpx; letter-spacing:2rpx; color:var(--color-gold); }.talk-room h3 { margin:9rpx 0 7rpx; font:700 29rpx var(--font-display); color:var(--color-text); }.talk-room__content > p { margin:0; font-size:20rpx; line-height:1.55; color:var(--color-text-muted); }.talk-room__role { display:flex; align-items:center; gap:12rpx; margin-top:17rpx; padding-top:15rpx; border-top:1px dashed rgba(72,25,22,.13); }.talk-room__role i { display:grid; place-items:center; width:44rpx; height:44rpx; border-radius:50%; color:white; background:var(--color-green); font:700 19rpx var(--font-display); font-style:normal; }.talk-room__role span,.talk-room__role strong { display:block; }.talk-room__role span { font-size:15rpx; color:var(--color-text-muted); }.talk-room__role strong { margin-top:2rpx; font-size:18rpx; color:var(--color-text-secondary); }.talk-room__footer { grid-column:1/-1; display:flex; justify-content:space-between; padding:15rpx 23rpx; background:rgba(127,33,29,.035); font-size:17rpx; color:var(--color-text-muted); }.talk-room__footer b { color:var(--color-primary); font-weight:500; }
.training-history{margin:0 0 30rpx;padding:23rpx;background:#f8f1e4;border:1px solid rgba(72,25,22,.12)}.training-history__head{display:flex;align-items:end;justify-content:space-between;margin-bottom:12rpx}.training-history__head span{font-size:14rpx;letter-spacing:3rpx;color:var(--color-gold)}.training-history__head h2{margin:3rpx 0 0;font:700 27rpx var(--font-display)}.training-history__head small{font-size:14rpx;color:var(--color-text-muted)}.training-history article{display:flex;align-items:center;justify-content:space-between;padding:15rpx 0;border-top:1px solid rgba(72,25,22,.1)}.training-history strong,.training-history text{display:block}.training-history strong{font-size:21rpx}.training-history text{margin-top:3rpx;font-size:16rpx;color:var(--color-text-muted)}.training-history b{font-size:17rpx;color:var(--color-primary)}
/* #ifndef H5 */
@media (min-width: 769px){.interview__main{padding:0 28px 52px}.interview__list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}.talk-room{margin-bottom:0}.training-history{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));column-gap:28px}.training-history__head{grid-column:1/-1}.interview-hero{padding-left:28px;padding-right:28px}.interview-hero h1{max-width:720px}}
/* #endif */
/* #ifdef H5 */
@container (min-width: 769px){.interview__main{padding:0 28px 52px}.interview__list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}.talk-room{margin-bottom:0}.training-history{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));column-gap:28px}.training-history__head{grid-column:1/-1}.interview-hero{padding-left:28px;padding-right:28px}.interview-hero h1{max-width:720px}}
/* #endif */
</style>
