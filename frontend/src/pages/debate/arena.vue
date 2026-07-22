<template>
  <div class="arena">
    <nav class="arena__progress"><div v-for="(s,i) in stages" :key="s.key" :class="{done:i<stageIdx,active:i===stageIdx}"><span class="arena__num">{{ i+1 }}</span><span class="arena__nm">{{ s.label }}</span></div><div class="arena__bar"><div class="arena__fill" :style="{width:progress+'%'}"></div></div></nav>
    <header class="arena__head"><small>{{ stanceLabel }} · 第{{ stageIdx+1 }}/4 阶段</small><h1>{{ topicTitle }}</h1></header>
    <div class="arena__chat" ref="chat">
      <div v-if="transition" class="arena__tran"><i>→</i><span>{{ transition }}</span></div>
      <div v-for="(m,i) in msgs" :key="i" class="arena__msg" :class="m.role==='user'?'is-me':'is-ai'">
        <div class="arena__meta"><span>{{ m.role==='user'?'我的陈词':'AI 对手' }}</span><span class="arena__stag">{{ labels[m.stage] }}</span></div><p>{{ m.content }}</p>
      </div>
      <div v-if="thinking" class="arena__msg is-ai"><div class="arena__meta"><span>AI 对手</span></div><p class="arena__think">思考中…</p></div>
    </div>
    <footer class="arena__foot">
      <div class="arena__hint">{{ hint }}</div>
      <div class="arena__row"><input v-model="text" :placeholder="ph" :disabled="thinking||done" /><button :disabled="!canSend" @click="send">{{ thinking?'…':done?'完成':'发送' }}</button></div>
      <button v-if="done" class="arena__end" @click="finish">生成 AI 评估报告</button>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { computed,nextTick,ref } from 'vue';import { onLoad } from '@dcloudio/uni-app';import { debateApi } from '@/api/debate'
const topicId=ref(''),topicTitle=ref('辩题'),stance=ref('pro'),stanceLabel=ref('正方'),sid=ref(''),text=ref(''),thinking=ref(false),msgs=ref<Array<{role:string;content:string;stage:string}>>([]),cur=ref('opening'),done=ref(false),transition=ref(''),chat=ref<HTMLElement|null>(null)
const stages=[{key:'opening',label:'立论'},{key:'cross_exam',label:'质询'},{key:'rebuttal',label:'驳论'},{key:'closing',label:'总结'}]
const keys=stages.map(s=>s.key)
const stageIdx=computed(()=>Math.max(0,keys.indexOf(cur.value)))
const progress=computed(()=>Math.max(10,((stageIdx.value+(cur.value==='finished'?1:0))/4)*100))
const labels:Record<string,string>={opening:'立论',cross_exam:'质询',rebuttal:'驳论',closing:'总结',finished:'完成'}
const hints:Record<string,string>={opening:'陈述你的核心立场与2个论据，不必回应AI',cross_exam:'针对AI立论提出1个尖锐问题',rebuttal:'逐点指出对方论证的漏洞',closing:'总结你的全部论点，做有力升华'}
const phs:Record<string,string>={opening:'写下你的立论陈词…',cross_exam:'质询：针对AI立论提问…',rebuttal:'驳论：指出AI论证的漏洞…',closing:'请总结你的核心论点…'}
const hint=computed(()=>hints[cur.value]||'')
const ph=computed(()=>phs[cur.value]||'输入…')
const canSend=computed(()=>!thinking.value&&!done.value&&text.value.trim()&&!!sid.value)
function lbl(s:string){return labels[s]||s}
function scroll(){nextTick(()=>{const e=chat.value;if(e)e.scrollTop=e.scrollHeight})}
onLoad(async(q:any)=>{topicId.value=q.topicId||'1';topicTitle.value=decodeURIComponent(q.title||'辩题');stance.value=q.stance||'pro';stanceLabel.value=stance.value==='pro'?'正方':'反方';thinking.value=true;try{const r=await debateApi.startDebate(topicId.value,stance.value);sid.value=r.id;cur.value=r.stage||'opening';msgs.value=[{role:'ai',content:r.first_argument,stage:'opening'}];scroll()}catch(e:any){uni.showToast({title:e.message||'启动失败',icon:'none'})}thinking.value=false})
async function send(){if(!canSend.value)return;const t=text.value.trim();text.value='';msgs.value.push({role:'user',content:t,stage:cur.value});thinking.value=true;scroll();try{const r=await debateApi.submitArgument(sid.value,t);msgs.value.push({role:'ai',content:r.argument,stage:cur.value});if(r.stage_complete){cur.value=r.next_stage;transition.value=r.phase_transition||'';setTimeout(()=>{transition.value=''},4000);if(r.is_finished){done.value=true;uni.showToast({title:'辩论全部完成！',icon:'success'})}else{uni.showToast({title:'进入下一阶段',icon:'none'})}}}catch(e:any){uni.showToast({title:e.message||'AI暂不可用',icon:'none'})}thinking.value=false;scroll()}
async function finish(){if(!sid.value)return;thinking.value=true;try{await debateApi.endDebate(sid.value);uni.redirectTo({url:`/pages/debate/feedback?sessionId=${sid.value}&topicId=${topicId.value}&topic=${encodeURIComponent(topicTitle.value)}&stance=${stance.value}`})}catch(e:any){uni.showToast({title:e.message||'评估失败',icon:'none'});thinking.value=false}}
</script>

<style scoped>
.arena{min-height:100vh;display:flex;flex-direction:column;background:var(--color-bg);color:var(--color-text)}
.arena__progress{display:grid;grid-template-columns:repeat(4,1fr);padding:20rpx 28rpx 0;position:relative}
.arena__bar{position:absolute;bottom:0;left:28rpx;right:28rpx;height:3rpx;background:var(--color-border);border-radius:2rpx}
.arena__fill{height:100%;background:var(--color-primary-light);border-radius:2rpx;transition:width .4s}
.arena__progress div{text-align:center;padding-bottom:14rpx;opacity:.3;transition:opacity .3s;position:relative;z-index:1}
.arena__progress div.done,.arena__progress div.active{opacity:1}
.arena__num{display:inline-block;width:36rpx;height:36rpx;border-radius:50%;border:2rpx solid var(--color-text-muted);font-size:18rpx;line-height:36rpx;margin-bottom:4rpx}
.arena__progress div.active .arena__num{background:var(--color-primary-light);border-color:var(--color-primary-light);color:#fff}
.arena__progress div.done .arena__num{background:var(--color-primary);border-color:var(--color-primary);color:#fff}
.arena__nm{display:block;font-size:22rpx;font-weight:600}
.arena__head{padding:20rpx 28rpx 12rpx}
.arena__head small{font-size:18rpx;color:var(--color-primary-light);letter-spacing:2rpx}
.arena__head h1{font:700 30rpx/1.35 'STKaiti','Noto Serif SC',serif;margin:6rpx 0 0}
.arena__chat{flex:1;overflow-y:auto;padding:0 28rpx 12rpx}
.arena__tran{margin:16rpx 0;padding:16rpx 20rpx;background:rgba(139,26,26,.06);border-left:3px solid var(--color-primary-light);border-radius:4px;font-size:22rpx;color:var(--color-text-secondary);display:flex;gap:8rpx;align-items:flex-start;animation:a0 .3s}
.arena__tran i{color:var(--color-primary-light);font-weight:700}
@keyframes a0{from{opacity:0;transform:translateY(-4px)}to{opacity:1;transform:translateY(0)}}
.arena__msg{margin-bottom:20rpx}
.arena__meta{display:flex;justify-content:space-between;align-items:center;margin-bottom:4rpx}
.arena__meta span{font-size:20rpx;font-weight:600;color:var(--color-text-secondary)}
.arena__msg.is-me .arena__meta span{color:var(--color-primary-light)}
.arena__stag{font-size:16rpx!important;color:var(--color-text-muted)!important;background:rgba(139,26,26,.06);padding:2rpx 10rpx;border-radius:8rpx;font-weight:400!important}
.arena__msg p{margin:0;padding:20rpx 24rpx;border-radius:4px;font-size:24rpx;line-height:1.65;white-space:pre-wrap}
.arena__msg.is-ai p{background:var(--color-card);border-left:3px solid var(--color-primary-light)}
.arena__msg.is-me p{background:linear-gradient(135deg,#4B1612,#6B1A1A);color:#FFF}
.arena__think{opacity:.5}
.arena__foot{padding:16rpx 28rpx calc(16rpx + env(safe-area-inset-bottom));background:var(--color-card);border-top:1px solid var(--color-border)}
.arena__hint{font-size:18rpx;color:var(--color-text-muted);margin-bottom:8rpx;line-height:1.4}
.arena__row{display:flex;gap:10rpx}
.arena__row input{flex:1;height:72rpx;background:#F5EFE6;border-radius:4px;padding:0 20rpx;font-size:24rpx;border:none;outline:none}
.arena__row button{height:72rpx;padding:0 28rpx;background:var(--color-primary-light);border:none;border-radius:4px;color:#FFF;font-size:24rpx;font-weight:600;white-space:nowrap;cursor:pointer}
.arena__row button:disabled{opacity:.4;cursor:not-allowed}
.arena__end{width:100%;margin-top:12rpx;padding:20rpx;background:linear-gradient(135deg,#8B1A1A,#5C0E0E);border:none;border-radius:4px;color:#FFF;font-size:26rpx;font-weight:600;cursor:pointer;animation:a1 2s infinite}
@keyframes a1{0%,100%{box-shadow:0 0 0 0 rgba(139,26,26,.4)}50%{box-shadow:0 0 0 12rpx rgba(139,26,26,0)}}
</style>