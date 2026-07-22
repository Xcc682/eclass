<template>
  <div class="growth">
    <header class="growth-hero">
      <div class="growth-hero__top"><span>PERSONAL ARCHIVE · {{ String(growth.rank || '—').padStart(2,'0') }}</span><span>成长档案</span></div>
      <h1>每一次练习，<br />都应该留下可回看的证据</h1>
      <div class="growth-hero__stats"><div><strong>{{ growth.total_interviews + growth.total_debates }}</strong><span>实训次数</span></div><div><strong>{{ growth.total_points }}</strong><span>学习积分</span></div><div><strong>{{ badges.filter(item=>item.earned).length }}</strong><span>获得成就</span></div></div>
    </header>

    <main class="growth__main">
      <section class="growth-card ability-card"><div class="growth-heading"><div><span>ABILITY PROFILE / 01</span><h2>综合能力画像</h2></div><p>基于已完成练习</p></div><RadarChart :dimensions="abilityDimensions" :size="460" /><p class="ability-note">能力分数来自你的实训评估记录；练习越充分，画像越具有参考价值。</p></section>
      <section class="growth-card"><div class="growth-heading"><div><span>ACHIEVEMENTS / 02</span><h2>成就印章</h2></div><p>{{ badges.filter(item=>item.earned).length }}/{{ badges.length }}</p></div><div class="growth__badges"><div v-for="(badge,index) in badges" :key="badge.name" class="growth__badge" :class="{locked:!badge.earned}"><div class="growth__badge-seal"><span>{{ badge.earned ? '成' : String(index+1).padStart(2,'0') }}</span><small>{{ badge.earned?'已获得':'未解锁' }}</small></div><strong>{{ badge.name }}</strong></div></div></section>
      <section class="growth-card"><div class="growth-heading"><div><span>ACTIVITY LOG / 03</span><h2>成长足迹</h2></div><p>{{ timeline.length }} 条记录</p></div><div class="growth__timeline"><article v-for="(item,index) in timeline" :key="item.id"><div class="growth__timeline-index">{{ String(index+1).padStart(2,'0') }}</div><div><strong>{{ item.title }}</strong><span>{{ formatTime(item.time) }}</span></div></article><EmptyState v-if="!timeline.length" title="暂无成长记录" description="完成一次实训后，记录会自动归档在这里" /></div></section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { onMounted,ref } from 'vue'
import RadarChart from '@/components/radar/RadarChart.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import { userApi,type UserInfo } from '@/api/user'
const growth=ref<UserInfo['growth']>({total_interviews:0,total_history_scenarios:0,total_debates:0,total_tours:0,total_reports:0,total_points:0,streak_days:0,rank:0,ability_dimensions:[],activities:[]})
const abilityDimensions=ref<Array<{name:string;score:number}>>([]),timeline=ref<Array<any>>([])
const badges=ref<Array<{name:string;icon:string;earned:boolean}>>([])
onMounted(async()=>{try{growth.value=await userApi.getGrowth();abilityDimensions.value=growth.value.ability_dimensions||[];timeline.value=growth.value.activities||[];badges.value=await userApi.getAchievements() as any}catch(error:any){uni.showToast({title:error.message||'成长数据加载失败',icon:'none'})}})
function formatTime(value:string){return new Date(value).toLocaleString('zh-CN',{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'})}
</script>

<style scoped>
.growth{min-height:100vh;padding-bottom:65rpx;background:var(--color-bg)}.growth-hero{padding:48rpx var(--page-gutter) 40rpx;color:#fff9ed;background:#431a18}.growth-hero__top{display:flex;justify-content:space-between;font-size:16rpx;letter-spacing:3rpx;color:#e5c77f}.growth-hero h1{margin:48rpx 0 28rpx;font:700 44rpx/1.28 var(--font-display);letter-spacing:2rpx}.growth-hero__stats{display:flex;border-top:1px solid rgba(231,201,129,.25);border-bottom:1px solid rgba(231,201,129,.18)}.growth-hero__stats div{flex:1;padding:17rpx 0;border-right:1px solid rgba(231,201,129,.18)}.growth-hero__stats div:last-child{border:0}.growth-hero__stats strong,.growth-hero__stats span{display:block}.growth-hero__stats strong{font:700 30rpx var(--font-display);color:#e7c981}.growth-hero__stats span{font-size:16rpx;color:rgba(255,249,237,.48)}.growth__main{padding:25rpx var(--page-gutter) 0}.growth-card{margin-bottom:22rpx;padding:28rpx;background:var(--color-card);border:1px solid rgba(72,25,22,.11);box-shadow:0 7rpx 23rpx rgba(47,32,23,.05)}.growth-heading{display:flex;justify-content:space-between;align-items:end;margin-bottom:22rpx;padding-bottom:16rpx;border-bottom:1px solid rgba(72,25,22,.1)}.growth-heading span{font-size:15rpx;letter-spacing:3rpx;color:var(--color-gold)}.growth-heading h2{margin:5rpx 0 0;font:700 29rpx var(--font-display);color:var(--color-text)}.growth-heading>p{margin:0;font-size:17rpx;color:var(--color-text-muted)}.ability-note{margin:3rpx 0 0;padding:15rpx 18rpx;background:rgba(49,91,73,.06);font-size:17rpx;line-height:1.55;color:var(--color-text-muted)}.growth__badges{display:grid;grid-template-columns:repeat(3,1fr);gap:24rpx 12rpx}.growth__badge{text-align:center}.growth__badge-seal{display:grid;place-items:center;align-content:center;width:82rpx;height:82rpx;margin:auto;border:4rpx double var(--color-primary);border-radius:50%;color:var(--color-primary);transform:rotate(-4deg)}.growth__badge-seal span{font:700 23rpx var(--font-display)}.growth__badge-seal small{font-size:12rpx}.growth__badge>strong{display:block;margin-top:9rpx;font-size:18rpx;color:var(--color-text-secondary)}.growth__badge.locked{opacity:.38}.growth__badge.locked .growth__badge-seal{border-color:var(--color-text-muted);color:var(--color-text-muted)}.growth__timeline article{display:flex;gap:16rpx;padding:18rpx 0;border-bottom:1px solid rgba(72,25,22,.09)}.growth__timeline-index{display:grid;place-items:center;width:42rpx;height:42rpx;flex:none;border:1px solid var(--color-gold);color:var(--color-primary);font:700 16rpx var(--font-display)}.growth__timeline strong,.growth__timeline span{display:block}.growth__timeline strong{font:700 21rpx var(--font-display);color:var(--color-text)}.growth__timeline span{margin-top:4rpx;font-size:16rpx;color:var(--color-text-muted)}
</style>
