<template>
  <div class="home">
    <section class="home__masthead">
      <div class="home__folio"><span>思想实践手册</span><b>NO. 2026</b></div>
      <div class="home__identity">
        <div>
          <span class="home__eyebrow">今日学习档案</span>
          <h1>你好，{{ profile?.nickname || '同学' }}</h1>
          <p>把每一次思考，沉淀为成长的刻度。</p>
        </div>
        <button class="home__avatar-wrap" @click="goToProfile" aria-label="进入个人中心">
          <img :src="profile?.avatar_url || defaultAvatar" class="home__avatar" />
          <span></span>
        </button>
      </div>
      <div class="home__ledger">
        <div><small>累计积分</small><strong>{{ growth.total_points }}</strong></div>
        <i></i>
        <div><small>连续学习</small><strong>{{ growth.streak_days }}<em>天</em></strong></div>
        <i></i>
        <div><small>成长排名</small><strong>{{ growth.rank || '—' }}</strong></div>
      </div>
    </section>

    <section class="home__section">
      <header class="home__section-head"><div><span>LEARNING PATH</span><h2>选择一项实践</h2></div><small>六个真实学习闭环</small></header>
      <div class="home__grid">
        <button v-for="item in quickActions" :key="item.key" class="home__grid-item" :class="`tone-${item.tone}`" @click="navigateTo(item.path)">
          <span class="home__grid-index">{{ item.index }}</span>
          <span class="home__grid-icon"><IconSet :name="item.icon" size="34rpx" color="currentColor" /></span>
          <span class="home__grid-copy"><b>{{ item.label }}</b><small>{{ item.desc }}</small></span>
          <span class="home__grid-arrow" aria-hidden="true"></span>
        </button>
      </div>
    </section>

    <section class="home__record">
      <header><span>本期学习记录</span><b>LEARNING LOG</b></header>
      <div class="home__stats-row">
        <div class="home__stat"><strong>{{ growth.total_interviews + growth.total_debates }}</strong><span>次情景训练</span></div>
        <div class="home__stat"><strong>{{ growth.total_history_scenarios }}</strong><span>篇党史学习</span></div>
        <div class="home__stat"><strong>{{ growth.total_tours }}</strong><span>处红色研学</span></div>
      </div>
    </section>

    <button class="home__recommend" @click="goToInterview">
      <div class="home__recommend-top"><span>本周推荐 · 01</span><b>约 15 分钟</b></div>
      <div class="home__recommend-body">
        <div><h2>入党积极分子谈话模拟</h2><p>由 AI 扮演谈话老师，围绕动机、理论与实践进行真实演练。</p></div>
        <span class="home__recommend-cta">开始<br/>练习</span>
      </div>
      <footer><span>难度：初级</span><span>即时反馈</span><span>生成报告</span></footer>
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { userApi, type UserInfo } from '@/api/user'
import IconSet from '@/components/common/IconSet.vue'
import defaultAvatar from '@/static/images/icons/default-avatar.png'

const emptyGrowth: UserInfo['growth'] = { total_interviews: 0, total_history_scenarios: 0, total_debates: 0, total_tours: 0, total_reports: 0, total_points: 0, streak_days: 0, rank: 0, ability_dimensions: [], activities: [] }
const profile = ref<UserInfo | null>(null)
const growth = computed(() => profile.value?.growth || emptyGrowth)
onMounted(async () => {
  try { profile.value = await userApi.getProfile() }
  catch (error: any) { uni.showToast({ title: error.message || '数据加载失败', icon: 'none' }) }
})

const quickActions = [
  { key: 'interview', index:'01', label: '入党谈话', desc:'对话演练', icon: 'interview', path: '/pages/interview/interview', tone:'red' },
  { key: 'history', index:'02', label: '党史情景', desc:'历史抉择', icon: 'history', path: '/pages/history/history', tone:'gold' },
  { key: 'tour', index:'03', label: '红色研学', desc:'云端走访', icon: 'tour', path: '/pages/tour/tour', tone:'green' },
  { key: 'debate', index:'04', label: '思政辩论', desc:'观点交锋', icon: 'debate', path: '/pages/debate/debate', tone:'ink' },
  { key: 'knowledge', index:'05', label: '知识问答', desc:'有据可查', icon: 'knowledge', path: '/pages/knowledge/ask', tone:'red' },
  { key: 'growth', index:'06', label: '成长档案', desc:'记录轨迹', icon: 'growth', path: '/pages/community/growth', tone:'gold' },
]

function navigateTo(path: string) {
  const tabs = ['/pages/index/index','/pages/interview/interview','/pages/community/community','/pages/knowledge/knowledge','/pages/community/profile']
  tabs.includes(path) ? uni.switchTab({ url: path }) : uni.navigateTo({ url: path })
}
function goToProfile() { uni.switchTab({ url: '/pages/community/profile' }) }
function goToGrowth() { uni.navigateTo({ url: '/pages/community/growth' }) }
function goToInterview() { uni.switchTab({ url: '/pages/interview/interview' }) }
</script>

<style scoped>
.home{min-height:100vh;padding-bottom:30rpx;background:var(--color-bg);color:var(--color-text)}
.home__masthead{position:relative;overflow:hidden;padding:30rpx 28rpx 28rpx;background:#4b1916;color:#fff8ed}.home__masthead:after{content:'实践';position:absolute;right:-20rpx;bottom:-58rpx;color:rgba(255,255,255,.035);font:150rpx/1 var(--font-display);writing-mode:vertical-rl}.home__folio{display:flex;justify-content:space-between;padding-bottom:17rpx;border-bottom:1rpx solid rgba(216,185,111,.32);font-size:17rpx;letter-spacing:3rpx;color:#d8b96f}.home__folio b{font-family:Georgia,serif;letter-spacing:1rpx}.home__identity{position:relative;z-index:1;display:flex;align-items:center;justify-content:space-between;gap:22rpx;padding:30rpx 0 24rpx}.home__eyebrow{font-size:18rpx;letter-spacing:4rpx;color:#d8b96f}.home__identity h1{margin:8rpx 0 5rpx;font:700 43rpx/1.25 var(--font-display)}.home__identity p{margin:0;color:rgba(255,248,237,.66);font-size:20rpx}.home__avatar-wrap{position:relative;flex:none;width:82rpx;height:82rpx;padding:0;border:1rpx solid rgba(216,185,111,.7);border-radius:50%;background:#fff}.home__avatar-wrap:after{content:'';position:absolute;inset:-8rpx;border:1rpx solid rgba(216,185,111,.22);border-radius:50%}.home__avatar{width:100%;height:100%;border-radius:50%;object-fit:cover}.home__avatar-wrap span{position:absolute;right:-2rpx;bottom:2rpx;width:18rpx;height:18rpx;border:3rpx solid #4b1916;border-radius:50%;background:#4f8b62}.home__ledger{position:relative;z-index:1;display:flex;align-items:center;padding:18rpx 0 0;border-top:1rpx solid rgba(255,255,255,.12)}.home__ledger div{flex:1}.home__ledger i{width:1rpx;height:40rpx;background:rgba(255,255,255,.14)}.home__ledger small{display:block;color:rgba(255,248,237,.55);font-size:17rpx}.home__ledger strong{display:block;margin-top:2rpx;color:#f6dd9e;font:26rpx Georgia,serif}.home__ledger em{margin-left:4rpx;font:17rpx var(--font-body)}
.home__section{padding:32rpx 28rpx 8rpx}.home__section-head{display:flex;align-items:flex-end;justify-content:space-between;margin-bottom:20rpx}.home__section-head span{color:var(--color-primary);font:15rpx Georgia,serif;letter-spacing:3rpx}.home__section-head h2{margin:3rpx 0 0;font-size:31rpx}.home__section-head small{color:var(--color-text-muted);font-size:18rpx}.home__grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12rpx}.home__grid-item{position:relative;display:grid;grid-template-columns:50rpx 1fr 22rpx;align-items:center;gap:12rpx;min-height:92rpx;padding:17rpx;border:1rpx solid var(--color-border);border-radius:14rpx;background:var(--color-paper);color:var(--color-primary);text-align:left;box-shadow:0 6rpx 18rpx rgba(65,45,28,.035);overflow:hidden}.home__grid-item:after{content:'';position:absolute;left:0;top:0;width:4rpx;height:100%;background:currentColor}.home__grid-index{position:absolute;right:9rpx;top:5rpx;color:rgba(50,40,30,.12);font:17rpx Georgia,serif}.home__grid-icon{display:grid;place-items:center;width:50rpx;height:50rpx;border-radius:50%;background:currentColor}.home__grid-icon :deep(svg){color:#fff}.home__grid-copy b,.home__grid-copy small{display:block}.home__grid-copy b{font:700 24rpx var(--font-display);color:var(--color-text)}.home__grid-copy small{margin-top:3rpx;color:var(--color-text-muted);font-size:17rpx}.home__grid-arrow{position:relative;align-self:end;justify-self:end;width:16rpx;height:16rpx;color:currentColor}.home__grid-arrow::before{content:'';position:absolute;right:0;top:0;width:9rpx;height:9rpx;border-top:2rpx solid currentColor;border-right:2rpx solid currentColor}.home__grid-arrow::after{content:'';position:absolute;right:0;top:1rpx;width:20rpx;height:2rpx;border-radius:2rpx;background:currentColor;transform:rotate(-45deg);transform-origin:right center}.tone-gold{color:#a57729}.tone-green{color:#315b49}.tone-ink{color:#45403a}
.home__record{margin:22rpx 28rpx 14rpx;border:1rpx solid #d8ccbc;background:#e9e1d5}.home__record header{display:flex;justify-content:space-between;padding:13rpx 18rpx;border-bottom:1rpx solid #d5c7b5;color:#6d5f51;font-size:17rpx;letter-spacing:2rpx}.home__record header b{font:14rpx Georgia,serif}.home__stats-row{display:flex;padding:18rpx 8rpx;background:rgba(255,253,247,.75)}.home__stat{flex:1;text-align:center;border-right:1rpx solid #ded3c4}.home__stat:last-child{border:0}.home__stat strong{display:block;color:var(--color-primary);font:30rpx Georgia,serif}.home__stat span{display:block;margin-top:2rpx;color:var(--color-text-muted);font-size:17rpx}
.home__recommend{display:block;width:calc(100% - 56rpx);margin:0 28rpx;padding:0;border:1rpx solid #a89579;border-radius:16rpx;background:#fffaf0;color:var(--color-text);text-align:left;overflow:hidden;box-shadow:var(--shadow-card)}.home__recommend-top{display:flex;justify-content:space-between;padding:12rpx 18rpx;background:#7f211d;color:#fff4e6;font-size:16rpx;letter-spacing:2rpx}.home__recommend-top b{font-weight:500;color:#e5c676}.home__recommend-body{display:flex;align-items:center;gap:18rpx;padding:22rpx}.home__recommend-body>div{flex:1}.home__recommend h2{margin:0 0 7rpx;font-size:28rpx}.home__recommend p{margin:0;color:var(--color-text-secondary);font-size:20rpx;line-height:1.65}.home__recommend-cta{display:grid;place-items:center;width:64rpx;height:64rpx;flex:none;border:1rpx solid #b58a3f;border-radius:50%;color:var(--color-primary);font:700 18rpx/1.25 var(--font-display);text-align:center}.home__recommend footer{display:flex;gap:22rpx;padding:12rpx 20rpx;border-top:1rpx solid #e3d7c6;color:#8e7f6f;font-size:16rpx}.home__recommend footer span:before{content:'◆';margin-right:7rpx;color:#b58a3f;font-size:8rpx;vertical-align:middle}
/* #ifndef H5 */
@media (max-width: 350px){.home__grid{grid-template-columns:1fr}.home__section-head small{display:none}}
/* #endif */
/* #ifdef H5 */
@container (max-width: 350px){.home__grid{grid-template-columns:1fr}.home__section-head small{display:none}}
/* #endif */
</style>
