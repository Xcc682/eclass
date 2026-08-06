<template>
  <div class="growth-page">
    <header class="archive-hero">
      <div class="archive-hero__eyebrow">
        <span>PERSONAL GROWTH ARCHIVE</span>
        <span>全局排名 {{ growth.rank || '—' }}</span>
      </div>
      <div class="archive-hero__body">
        <div class="archive-hero__copy">
          <p class="archive-hero__edition">成长档案 · 动态评估版</p>
          <h1 class="archive-hero__title">看见每个模块的积累，<br />也看见完整的自己。</h1>
          <p>积分记录参与和完成，成长指数反映四个模块的训练表现。两者彼此关联，但不互相替代。</p>
        </div>
        <div class="index-seal" :style="{ '--score': `${growthIndex.score * 3.6}deg` }">
          <div class="index-seal__inner">
            <strong>{{ growthIndex.score }}</strong>
            <span>综合成长指数</span>
            <small>覆盖 {{ growthIndex.coverage }}%</small>
          </div>
        </div>
      </div>
      <div class="archive-hero__stats">
        <div><strong>{{ growth.total_points }}</strong><span>全局积分</span><small>奖励余额</small></div>
        <div><strong>{{ totalCompleted }}</strong><span>有效完成</span><small>四模块合计</small></div>
        <div><strong>{{ growth.streak_days }}</strong><span>连续学习</span><small>天</small></div>
        <div><strong>{{ badges.filter(item => item.earned).length }}</strong><span>成就印章</span><small>已解锁</small></div>
      </div>
    </header>

    <main class="growth-content">
      <section class="section-block module-section">
        <div class="section-heading">
          <div><span>MODULE GROWTH / 01</span><h2>四条成长路径</h2></div>
          <p>各模块独立记录，按 {{ growthIndex.method }}</p>
        </div>
        <div class="module-grid">
          <article v-for="(item, index) in modules" :key="item.key" class="module-card" :class="`module-card--${item.key}`">
            <div class="module-card__top">
              <span class="module-card__mark">{{ moduleMarks[item.key] }}</span>
              <span class="module-card__number">0{{ index + 1 }}</span>
            </div>
            <div class="module-card__title"><div><h3>{{ item.label }}</h3><p>{{ item.description }}</p></div><strong>{{ item.mastery_score }}</strong></div>
            <div class="module-card__track"><span :style="{ width: `${item.mastery_score}%` }"></span></div>
            <div class="module-card__meta">
              <span>{{ item.level }}</span>
              <span>完成 {{ item.completed_count }}<template v-if="item.total_available !== null">/{{ item.total_available }}</template> 次</span>
              <span>{{ item.points }} 积分</span>
            </div>
          </article>
        </div>
      </section>

      <div class="evidence-layout">
        <section class="section-block ability-section">
          <div class="section-heading section-heading--compact">
            <div><span>ABILITY EVIDENCE / 02</span><h2>综合能力证据</h2></div>
            <p>{{ growth.ability_profile?.coverage || 0 }}% 覆盖</p>
          </div>
          <RadarChart :dimensions="abilityDimensions" :size="430" />
          <div class="evidence-list">
            <div v-for="item in abilityDimensions" :key="item.name">
              <strong>{{ item.name }}</strong>
              <span>{{ item.evidence?.length ? item.evidence.join(' · ') : '完成相关训练后形成证据' }}</span>
            </div>
          </div>
          <p class="method-note">{{ growth.ability_profile?.disclaimer || '综合能力来自有效训练证据，不等同于积分，也不作为正式组织评价。' }}</p>
        </section>

        <section class="section-block ledger-section">
          <div class="section-heading section-heading--compact">
            <div><span>POINT LEDGER / 03</span><h2>积分构成</h2></div>
            <p>{{ pointSummary.is_reconciled ? '账目已对平' : '账目待校验' }}</p>
          </div>
          <div class="ledger-total">
            <div><span>可追溯模块积分</span><strong>{{ pointSummary.traceable_points }}</strong></div>
            <div><span>迁移前历史余额</span><strong>{{ signed(pointSummary.legacy_balance) }}</strong></div>
          </div>
          <div class="point-bars">
            <div v-for="item in pointBreakdown" :key="item.key" class="point-row">
              <div><span>{{ item.label }}</span><strong>{{ item.value }}</strong></div>
              <div class="point-row__track"><span :style="{ width: `${item.percent}%` }"></span></div>
            </div>
          </div>
          <div class="ledger-note">
            <strong>积分不是能力分</strong>
            <p>积分用于全局排名与成就；同一党史情景和同一研学点位只在首次完成时发放，重复训练仍可保留学习记录。</p>
          </div>
          <div class="transaction-list">
            <h3>最近积分明细</h3>
            <article v-for="item in recentPoints.slice(0, 6)" :key="item.id">
              <div><strong>{{ item.description }}</strong><span>{{ item.module_label }} · {{ formatTime(item.created_at) }}</span></div>
              <b :class="{ negative: item.points < 0 }">{{ signed(item.points) }}</b>
            </article>
            <EmptyState v-if="!recentPoints.length" title="暂无积分流水" description="完成一次有效训练后，积分来源会记录在这里" />
          </div>
        </section>
      </div>

      <section class="section-block achievement-section">
        <div class="section-heading">
          <div><span>ACHIEVEMENTS / 04</span><h2>成就印章</h2></div>
          <p>{{ badges.filter(item => item.earned).length }}/{{ badges.length }} 已解锁</p>
        </div>
        <div class="badge-grid">
          <div v-for="(badge, index) in badges" :key="badge.name" class="badge" :class="{ locked: !badge.earned }">
            <div class="badge__seal"><span>{{ badge.earned ? '成' : String(index + 1).padStart(2, '0') }}</span><small>{{ badge.earned ? '已获得' : '未解锁' }}</small></div>
            <strong>{{ badge.name }}</strong>
          </div>
        </div>
      </section>

      <section class="section-block timeline-section">
        <div class="section-heading">
          <div><span>ACTIVITY LOG / 05</span><h2>成长足迹</h2></div>
          <p>{{ timeline.length }} 条有效记录</p>
        </div>
        <div class="timeline">
          <article v-for="(item, index) in timeline" :key="item.id">
            <div class="timeline__index">{{ String(index + 1).padStart(2, '0') }}</div>
            <div><strong>{{ item.title }}</strong><span>{{ formatTime(item.time) }}</span></div>
            <b v-if="item.score !== null && item.score !== undefined">{{ item.score }}</b>
          </article>
          <EmptyState v-if="!timeline.length" title="暂无成长记录" description="完成一次有效训练后，记录会自动归档在这里" />
        </div>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import RadarChart from '@/components/radar/RadarChart.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import { userApi, type ModuleGrowth, type PointTransaction, type UserInfo } from '@/api/user'

const emptyGrowth: UserInfo['growth'] = {
  total_interviews: 0, total_history_scenarios: 0, total_debates: 0, total_tours: 0,
  total_reports: 0, total_points: 0, streak_days: 0, rank: 0,
  ability_dimensions: [], activities: [],
}
const growth = ref<UserInfo['growth']>(emptyGrowth)
const badges = ref<Array<{ name: string; icon: string; earned: boolean }>>([])
const moduleMarks: Record<ModuleGrowth['key'], string> = { interview: '谈', debate: '辩', history: '史', tour: '行' }
const moduleLabels: Record<string, string> = { interview: '入党谈话', debate: '思政辩论', history: '党史情景', tour: '红色研学', system: '历史余额' }

const growthIndex = computed(() => growth.value.growth_index || { score: 0, coverage: 0, method: '谈话30% + 辩论30% + 党史20% + 研学20%' })
const modules = computed<ModuleGrowth[]>(() => growth.value.module_growth || [])
const abilityDimensions = computed(() => growth.value.ability_profile?.dimensions || growth.value.ability_dimensions || [])
const timeline = computed(() => growth.value.activities || [])
const totalCompleted = computed(() => growth.value.total_interviews + growth.value.total_debates + growth.value.total_history_scenarios + growth.value.total_tours)
const pointSummary = computed(() => growth.value.point_summary || {
  total: growth.value.total_points, ledger_total: growth.value.total_points, traceable_points: 0,
  legacy_balance: growth.value.total_points, by_module: {}, is_reconciled: true, recent_transactions: [],
})
const recentPoints = computed<PointTransaction[]>(() => pointSummary.value.recent_transactions || [])
const pointBreakdown = computed(() => {
  const values = Object.entries(pointSummary.value.by_module || {})
    .filter(([key, value]) => key !== 'system' && Number(value) !== 0)
    .map(([key, value]) => ({ key, label: moduleLabels[key] || key, value: Number(value) }))
  const maximum = Math.max(...values.map(item => Math.abs(item.value)), 1)
  return values.map(item => ({ ...item, percent: Math.max(Math.abs(item.value) / maximum * 100, 4) }))
})

onMounted(async () => {
  try {
    const [growthData, achievementData] = await Promise.all([userApi.getGrowth(), userApi.getAchievements()])
    growth.value = growthData
    badges.value = achievementData as any
  } catch (error: any) {
    uni.showToast({ title: error.message || '成长数据加载失败', icon: 'none' })
  }
})

function signed(value: number) { return value > 0 ? `+${value}` : String(value) }
function formatTime(value: string) { return new Date(value).toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) }
</script>

<style scoped>
.growth-page{min-height:100vh;padding-bottom:80rpx;background:#f3eee5;color:#392d27}.archive-hero{position:relative;overflow:hidden;padding:46rpx var(--page-gutter) 0;background:#451b19;color:#fff8e9}.archive-hero::after{content:"成长";position:absolute;right:-24rpx;top:44rpx;color:rgba(236,207,145,.045);font:700 220rpx/.8 var(--font-display);pointer-events:none}.archive-hero__eyebrow{position:relative;z-index:1;display:flex;justify-content:space-between;padding-bottom:22rpx;border-bottom:1px solid rgba(232,202,132,.26);font-size:15rpx;letter-spacing:3rpx;color:#dfc27f}.archive-hero__body{position:relative;z-index:1;display:flex;align-items:center;justify-content:space-between;gap:28rpx;padding:46rpx 0 40rpx}.archive-hero__edition{margin:0 0 12rpx;color:#d7b66d;font-size:17rpx;letter-spacing:2rpx}.archive-hero__title{margin:0;font:700 var(--page-title-size)/1.3 var(--font-display);letter-spacing:2rpx}.archive-hero__copy>p:last-child{max-width:620rpx;margin:22rpx 0 0;font-size:19rpx;line-height:1.75;color:rgba(255,248,233,.66)}.index-seal{display:grid;place-items:center;width:190rpx;height:190rpx;flex:none;border-radius:50%;background:conic-gradient(#d8b76d var(--score),rgba(255,255,255,.12) 0);transform:rotate(-3deg)}.index-seal__inner{display:grid;place-items:center;align-content:center;width:168rpx;height:168rpx;border:1px solid rgba(216,183,109,.7);border-radius:50%;background:#451b19;text-align:center}.index-seal strong{font:700 58rpx/1 Georgia,serif;color:#ebce8b}.index-seal span{margin-top:8rpx;font:700 18rpx var(--font-display)}.index-seal small{margin-top:5rpx;font-size:14rpx;color:rgba(255,248,233,.5)}.archive-hero__stats{position:relative;z-index:1;display:grid;grid-template-columns:repeat(4,1fr);border-top:1px solid rgba(232,202,132,.24)}.archive-hero__stats>div{padding:22rpx 10rpx 25rpx;border-right:1px solid rgba(232,202,132,.17)}.archive-hero__stats>div:last-child{border:0}.archive-hero__stats strong,.archive-hero__stats span,.archive-hero__stats small{display:block}.archive-hero__stats strong{font:700 34rpx Georgia,serif;color:#e6c77f}.archive-hero__stats span{margin-top:6rpx;font-size:17rpx}.archive-hero__stats small{margin-top:3rpx;font-size:14rpx;color:rgba(255,248,233,.42)}
.growth-content{max-width:1160px;margin:auto;padding:28rpx var(--page-gutter) 0}.section-block{margin-bottom:24rpx;padding:30rpx;border:1px solid rgba(74,38,29,.12);background:#fffaf1;box-shadow:0 12rpx 35rpx rgba(61,42,29,.055)}.section-heading{display:flex;align-items:end;justify-content:space-between;gap:20rpx;margin-bottom:25rpx;padding-bottom:17rpx;border-bottom:1px solid rgba(74,38,29,.11)}.section-heading span{font-size:14rpx;letter-spacing:3rpx;color:#a9782c}.section-heading h2{margin:5rpx 0 0;font:700 30rpx var(--font-display)}.section-heading>p{margin:0;font-size:16rpx;color:#8b7c6e;text-align:right}.section-heading--compact h2{font-size:28rpx}.module-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18rpx}.module-card{position:relative;overflow:hidden;padding:23rpx;border:1px solid #ded2c1;background:#f8f1e6}.module-card::after{content:"";position:absolute;left:0;bottom:0;width:100%;height:5rpx;background:#7c2823}.module-card--debate::after{background:#9c6d25}.module-card--history::after{background:#4e654f}.module-card--tour::after{background:#365b64}.module-card__top{display:flex;justify-content:space-between;align-items:center}.module-card__mark{display:grid;place-items:center;width:52rpx;height:52rpx;border:2rpx solid currentColor;border-radius:50%;font:700 22rpx var(--font-display);color:#76241f}.module-card__number{font:italic 24rpx Georgia,serif;color:#b7a794}.module-card__title{display:flex;align-items:end;justify-content:space-between;gap:12rpx;margin-top:24rpx}.module-card h3{margin:0;font:700 27rpx var(--font-display)}.module-card p{margin:6rpx 0 0;font-size:15rpx;line-height:1.45;color:#8a7b6c}.module-card__title>strong{font:700 46rpx/.9 Georgia,serif;color:#5d3c2e}.module-card__track{height:7rpx;margin-top:19rpx;overflow:hidden;background:#e1d7c9}.module-card__track span{display:block;height:100%;background:#7c2823;transition:width .5s ease}.module-card__meta{display:flex;justify-content:space-between;margin-top:12rpx;font-size:14rpx;color:#75685d}
.evidence-layout{display:grid;grid-template-columns:minmax(0,.9fr) minmax(0,1.1fr);gap:24rpx}.evidence-list{display:grid;grid-template-columns:repeat(2,1fr);gap:10rpx;margin-top:18rpx}.evidence-list>div{padding:13rpx 15rpx;border-left:4rpx solid #7b2b25;background:#f5ede2}.evidence-list strong,.evidence-list span{display:block}.evidence-list strong{font-size:17rpx}.evidence-list span{margin-top:3rpx;font-size:13rpx;line-height:1.45;color:#8a7b6c}.method-note,.ledger-note{margin:18rpx 0 0;padding:16rpx 18rpx;border:1px solid #d9cdbb;background:#f6efe4;font-size:15rpx;line-height:1.65;color:#77695d}.ledger-total{display:grid;grid-template-columns:1fr 1fr;border:1px solid #d7cab7}.ledger-total>div{padding:20rpx}.ledger-total>div+div{border-left:1px solid #d7cab7}.ledger-total span,.ledger-total strong{display:block}.ledger-total span{font-size:15rpx;color:#837466}.ledger-total strong{margin-top:6rpx;font:700 34rpx Georgia,serif;color:#6f251f}.point-bars{padding:20rpx 0}.point-row+.point-row{margin-top:15rpx}.point-row>div:first-child{display:flex;justify-content:space-between;font-size:15rpx}.point-row__track{height:7rpx;margin-top:7rpx;overflow:hidden;background:#e7ddd0}.point-row__track span{display:block;height:100%;background:#416052}.ledger-note strong{display:block;color:#5d2823}.ledger-note p{margin:5rpx 0 0}.transaction-list{margin-top:22rpx}.transaction-list h3{margin:0 0 7rpx;font:700 21rpx var(--font-display)}.transaction-list article{display:flex;align-items:center;justify-content:space-between;gap:14rpx;padding:14rpx 0;border-bottom:1px solid #e8ded1}.transaction-list article strong,.transaction-list article span{display:block}.transaction-list article strong{font-size:16rpx}.transaction-list article span{margin-top:3rpx;font-size:13rpx;color:#8c7e70}.transaction-list article b{font:700 21rpx Georgia,serif;color:#35604a}.transaction-list article b.negative{color:#9a3b34}
.badge-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:22rpx 12rpx}.badge{text-align:center}.badge__seal{display:grid;place-items:center;align-content:center;width:86rpx;height:86rpx;margin:auto;border:4rpx double #7d2722;border-radius:50%;color:#7d2722;transform:rotate(-4deg)}.badge__seal span{font:700 24rpx var(--font-display)}.badge__seal small{font-size:11rpx}.badge>strong{display:block;margin-top:9rpx;font-size:17rpx}.badge.locked{filter:grayscale(1);opacity:.35}.timeline article{display:flex;align-items:center;gap:17rpx;padding:17rpx 0;border-bottom:1px solid #e8ded1}.timeline__index{display:grid;place-items:center;width:44rpx;height:44rpx;flex:none;border:1px solid #a97931;font:700 15rpx Georgia,serif;color:#782923}.timeline article>div:nth-child(2){flex:1}.timeline article strong,.timeline article span{display:block}.timeline article strong{font:700 18rpx var(--font-display)}.timeline article span{margin-top:4rpx;font-size:14rpx;color:#8b7c6e}.timeline article>b{font:700 22rpx Georgia,serif;color:#3b624f}
/* #ifndef H5 */
@media (max-width: 620px){.archive-hero__body{align-items:flex-end}.archive-hero__copy>p:last-child{display:none}.index-seal{width:150rpx;height:150rpx}.index-seal__inner{width:130rpx;height:130rpx}.index-seal strong{font-size:45rpx}.index-seal span{font-size:14rpx}.archive-hero__title{font-size:30px}.archive-hero__stats{grid-template-columns:repeat(2,1fr)}.archive-hero__stats>div:nth-child(2){border-right:0}.archive-hero__stats>div:nth-child(-n+2){border-bottom:1px solid rgba(232,202,132,.17)}.module-grid,.evidence-layout{grid-template-columns:1fr}.badge-grid{grid-template-columns:repeat(3,1fr)}.section-heading{align-items:start}.section-heading>p{max-width:48%;font-size:14rpx}.evidence-list{grid-template-columns:1fr}}
/* #endif */
/* #ifdef H5 */
@container (max-width: 620px){.archive-hero__body{align-items:flex-end}.archive-hero__copy>p:last-child{display:none}.index-seal{width:150rpx;height:150rpx}.index-seal__inner{width:130rpx;height:130rpx}.index-seal strong{font-size:45rpx}.index-seal span{font-size:14rpx}.archive-hero__title{font-size:30px}.archive-hero__stats{grid-template-columns:repeat(2,1fr)}.archive-hero__stats>div:nth-child(2){border-right:0}.archive-hero__stats>div:nth-child(-n+2){border-bottom:1px solid rgba(232,202,132,.17)}.module-grid,.evidence-layout{grid-template-columns:1fr}.badge-grid{grid-template-columns:repeat(3,1fr)}.section-heading{align-items:start}.section-heading>p{max-width:48%;font-size:14rpx}.evidence-list{grid-template-columns:1fr}}
/* #endif */
/* #ifndef H5 */
@media (max-width: 360px){.index-seal{width:132rpx;height:132rpx}.index-seal__inner{width:114rpx;height:114rpx}.archive-hero__title{font-size:31rpx}.section-block{padding:24rpx}}
/* #endif */
/* #ifdef H5 */
@container (max-width: 360px){.index-seal{width:132rpx;height:132rpx}.index-seal__inner{width:114rpx;height:114rpx}.archive-hero__title{font-size:31rpx}.section-block{padding:24rpx}}
/* #endif */
</style>
