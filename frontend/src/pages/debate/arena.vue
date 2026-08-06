<template>
  <view class="arena">
    <view class="arena__masthead">
      <view class="arena__folio"><text>{{ stanceLabel }} · {{ mode==='full'?'完整赛训':'快速练习' }}</text><text>{{ displayStep }}/{{ totalSteps }} STEP</text></view>
      <text class="arena__topic">{{ topicTitle }}</text>
      <view class="stage-track">
        <view v-for="(item,index) in stages" :key="item.key" :class="{active:index===stageIndex,done:index<stageIndex}"><i>{{ index<stageIndex?'✓':index+1 }}</i><text>{{ item.label }}</text></view>
        <view class="stage-track__line"><view :style="{width:progress+'%'}"></view></view>
      </view>
    </view>

    <view class="arena__tabs">
      <button v-for="item in tabs" :key="item.key" :class="{active:activeTab===item.key}" @click="activeTab=item.key">{{ item.label }}<i v-if="item.key==='evidence'&&selectedEvidence.length">{{ selectedEvidence.length }}</i></button>
    </view>

    <view class="arena__workspace">
      <scroll-view ref="courtScroller" v-show="activeTab==='court'" class="court" scroll-y :scroll-into-view="scrollTarget" :show-scrollbar="false">
        <view class="court__inner">
          <view class="step-card">
            <view class="step-card__head"><text>当前任务</text><i>{{ displayStep }}/{{ totalSteps }}</i></view>
            <strong>{{ stepLabel }}</strong>
            <text class="step-card__goal">{{ currentHint }}</text>
            <small>{{ currentPlaceholder }}</small>
          </view>
          <view v-for="message in messages" :id="`debate-${message.id}`" :key="message.id" class="speech" :class="message.role==='user'?'is-user':'is-ai'">
            <view class="speech__meta"><text>{{ message.role==='user'?'我的陈词':'AI 对手' }}</text><i>{{ stageLabels[message.stage] }}</i></view>
            <text class="speech__content">{{ message.content }}</text>
            <view v-if="message.evidence?.length" class="speech__sources"><text v-for="source in message.evidence" :key="source.chunk_id">《{{ source.document_title }}》</text></view>
            <view v-if="message.role==='user'&&message.analysis?.coach_feedback" class="coach-inline">
              <text>提示</text><strong>{{ message.analysis.coach_feedback.strength || message.analysis.coach_feedback.stage_fit }}</strong><small>{{ message.analysis.coach_feedback.next_action }}</small>
            </view>
            <view v-if="message.transition" class="stage-transition"><i>→</i><text>{{ message.transition }}</text></view>
            <view v-if="message.local_status==='pending'" class="delivery">正在提交本轮陈词…</view>
            <view v-if="message.local_status==='failed'" class="delivery delivery--failed"><text>提交失败，赛程未推进</text><button @click="retryMessage(message)">重新发送</button></view>
          </view>
          <view v-if="thinking" class="speech is-ai"><view class="speech__meta"><text>AI 对手</text></view><text class="speech__content speech__thinking">正在分析论证并组织回应…</text></view>
          <view id="debate-bottom" class="bottom-anchor"></view>
        </view>
      </scroll-view>

      <scroll-view v-show="activeTab==='map'" class="side-panel" scroll-y>
        <view class="panel-title"><text>ARGUMENT MAP</text><strong>论证地图</strong><small>从你的陈词中自动提取，不替代你作答</small></view>
        <view v-if="!mapEntries.length" class="empty-panel">完成第一轮陈词后，这里会逐步形成你的论证结构。</view>
        <view v-for="(entry,index) in mapEntries" :key="index" class="map-card">
          <view class="map-card__head"><i>{{ index+1 }}</i><text>{{ entry.step_label }}</text></view>
          <view v-if="entry.map.claims?.length" class="map-unit"><strong>主张</strong><text v-for="item in entry.map.claims" :key="item">{{ item }}</text></view>
          <view v-if="entry.map.evidence?.length" class="map-unit"><strong>证据</strong><text v-for="item in entry.map.evidence" :key="item">{{ item }}</text></view>
          <view v-if="entry.map.reasoning?.length" class="map-unit"><strong>推理链</strong><text v-for="item in entry.map.reasoning" :key="item">{{ item }}</text></view>
          <view v-if="entry.map.gaps?.length" class="map-unit map-unit--gap"><strong>待补缺口</strong><text v-for="item in entry.map.gaps" :key="item">{{ item }}</text></view>
        </view>
      </scroll-view>

      <scroll-view v-show="activeTab==='evidence'" class="side-panel" scroll-y>
        <view class="panel-title"><text>EVIDENCE DESK</text><strong>资料证据席</strong><small>只检索知识库中已审核发布的资料</small></view>
        <view class="evidence-search"><input v-model="evidenceQuery" placeholder="搜索与你的论点相关的依据" @confirm="searchEvidence"/><button :disabled="searching||!evidenceQuery.trim()" @click="searchEvidence">{{ searching?'检索中':'检索' }}</button></view>
        <view v-if="selectedEvidence.length" class="selected-box"><text>本轮已选 {{ selectedEvidence.length }}/3</text><button @click="selectedEvidence=[]">清空</button></view>
        <view v-if="!evidenceResults.length&&!searching" class="empty-panel">输入关键词检索资料。选中的原文片段会随本轮陈词提交并保留来源。</view>
        <view v-for="item in evidenceResults" :key="item.chunk_id" class="evidence-card" :class="{selected:isSelected(item)}" @click="toggleEvidence(item)">
          <view><strong>《{{ item.document_title }}》</strong><i>{{ isSelected(item)?'已选择':'选择引用' }}</i></view><text>{{ item.excerpt }}</text><small>{{ item.source }}</small>
        </view>
      </scroll-view>
    </view>

    <view v-if="status==='in_progress'" class="composer">
      <view class="composer__meta"><text>{{ stepLabel }}</text><span>{{ text.length }}/3000</span></view>
      <view class="composer__row"><textarea v-model="text" :placeholder="currentPlaceholder" :disabled="thinking" :maxlength="3000" :rows="composerRows"/><button :disabled="!canSend" @click="send">{{ thinking?'等待回应':'提交陈词' }}</button></view>
      <view v-if="selectedEvidence.length" class="composer__evidence"><text v-for="item in selectedEvidence" :key="item.chunk_id">《{{ item.document_title }}》<i @click="toggleEvidence(item)">×</i></text></view>
    </view>

    <view v-if="!reviewMode&&(status!=='in_progress'||reportState!=='idle')" class="finish-layer">
      <view class="finish-card">
        <text class="finish-card__seal">赛毕</text><text class="finish-card__eyebrow">DEBATE COMPLETED</text><strong>四阶段攻防已经完成</strong>
        <text v-if="reportState==='generating'">正在整理关键交锋与论证表现，请稍候…</text>
        <text v-else-if="reportState==='failed'">赛程和陈词已保存，但报告暂时生成失败。你可以现在重试，也可以稍后从记录中继续。</text>
        <text v-else-if="status==='completed'">评估报告已经生成，可以随时查看关键交锋与改进建议。</text>
        <text v-else>输入已锁定，正在准备生成本场评估报告。</text>
        <view class="finish-card__progress"><i :class="{active:reportState==='generating'}"></i></view>
        <button v-if="reportState==='failed'" @click="finish">重新生成评估报告</button>
        <button v-else-if="status==='completed'" @click="gotoReport">查看评估报告</button>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed,nextTick,ref } from 'vue'
import { onLoad,onUnload } from '@dcloudio/uni-app'
import { debateApi,type ArgumentMap,type DebateEvidence,type DebateMessage,type DebateMode,type DebateSession,type DebateStage,type DebateStatus } from '@/api/debate'

type LocalMessage=DebateMessage&{transition?:string}
const tabs=[{key:'court',label:'赛场'},{key:'map',label:'论证图'},{key:'evidence',label:'资料席'}]
const stages=[{key:'opening',label:'立论'},{key:'cross_exam',label:'质询'},{key:'rebuttal',label:'驳论'},{key:'closing',label:'总结'}]
const stageLabels:Record<string,string>={opening:'立论',cross_exam:'质询',rebuttal:'驳论',closing:'总结',finished:'完成'}
const stepHints:Record<string,string>={user_opening:'建立清晰立场，用“主张—理由—依据”完成开篇。',user_question:'针对对手最关键的前提或证据提出一个可回答的问题。',user_counter_answer:'正面回答对手的反质询，再指出其问题中的隐含前提。',user_rebuttal:'围绕刚才暴露的核心分歧逐点反驳。',user_defense:'回应对手反击，补强你方证据和推理链。',user_closing:'收束已有论证，重申为什么你方更能回应辩题。'}
const stepPlaceholders:Record<string,string>={user_opening:'写下你的立论陈词…',user_question:'提出一个聚焦、尖锐且可回答的质询…',user_counter_answer:'回答反质询并说明其前提问题…',user_rebuttal:'逐点回应并完成核心驳论…',user_defense:'补充防守，修复论证缺口…',user_closing:'完成总结陈词，不再引入新论点…'}
const sid=ref(''),topicId=ref(''),topicTitle=ref('辩题'),stance=ref('pro'),stanceLabel=ref('正方'),mode=ref<DebateMode>('full')
const status=ref<DebateStatus>('in_progress'),currentStage=ref<DebateStage>('opening'),currentStep=ref('user_opening'),stepLabel=ref('立论陈词'),stepIndex=ref(0),totalSteps=ref(6)
const displayStep=computed(()=>status.value==='in_progress'?Math.min(stepIndex.value+1,totalSteps.value):totalSteps.value)
const messages=ref<LocalMessage[]>([]),text=ref(''),thinking=ref(false),activeTab=ref('court'),scrollTarget=ref(''),courtScroller=ref<any>(null),alive=ref(true)
const evidenceQuery=ref(''),evidenceResults=ref<DebateEvidence[]>([]),selectedEvidence=ref<DebateEvidence[]>([]),searching=ref(false)
const reportState=ref<'idle'|'generating'|'failed'|'completed'>('idle')
const reviewMode=ref(false)
const mapEntries=ref<Array<{step_label:string;map:ArgumentMap}>>([])
const stageIndex=computed(()=>currentStage.value==='finished'?4:Math.max(0,stages.findIndex(item=>item.key===currentStage.value)))
const progress=computed(()=>currentStage.value==='finished'?100:Math.max(8,(stageIndex.value/4)*100))
const currentHint=computed(()=>stepHints[currentStep.value]||'围绕辩题完成当前阶段训练。')
const currentPlaceholder=computed(()=>stepPlaceholders[currentStep.value]||'输入你的陈词…')
const canSend=computed(()=>!thinking.value&&status.value==='in_progress'&&!!sid.value&&!!text.value.trim())
const composerRows=computed(()=>{
  const visualLines=text.value.split('\n').reduce((count,line)=>count+Math.max(1,Math.ceil(line.length/24)),0)
  return Math.min(5,Math.max(1,visualLines))
})

function scrollBottom(){nextTick(()=>{scrollTarget.value='';setTimeout(()=>{if(!alive.value)return;scrollTarget.value='debate-bottom';const scroller=courtScroller.value;if(scroller&&typeof scroller.scrollTo==='function')scroller.scrollTo({top:scroller.scrollHeight,behavior:'smooth'})},20)})}
function rebuildMap(){mapEntries.value=messages.value.filter(item=>item.role==='user'&&item.analysis?.argument_map).map(item=>({step_label:item.analysis?.step_label||stageLabels[item.stage],map:item.analysis?.argument_map||{}}))}
function applySession(data:DebateSession){
  sid.value=data.id;status.value=data.status;currentStage.value=data.stage;currentStep.value=data.step;stepLabel.value=data.step_label
  stepIndex.value=data.step_index;totalSteps.value=data.total_steps;mode.value=data.mode;stance.value=data.stance
  topicTitle.value=data.topic?.title||topicTitle.value;topicId.value=data.topic?.id||topicId.value;stanceLabel.value=data.stance==='pro'?'正方':'反方'
  messages.value=(data.messages||[]).map(item=>({...item,local_status:item.delivery_status||'sent'}));reportState.value=data.status==='completed'?'completed':'idle';rebuildMap();scrollBottom()
}
onLoad(async(query:any)=>{
  reviewMode.value=!!query.messageId
  topicId.value=query.topicId||'';topicTitle.value=decodeURIComponent(query.title||'辩题');stance.value=query.stance||'pro';mode.value=query.mode==='quick'?'quick':'full';stanceLabel.value=stance.value==='pro'?'正方':'反方';thinking.value=true
  try{
    let data=query.sessionId?await debateApi.getPractice(query.sessionId):await debateApi.startDebate(topicId.value,stance.value,mode.value)
    if(!alive.value)return
    if(data.resumed&&!query.sessionId){
      const continuePrevious=await confirmResume(data)
      if(!continuePrevious){data=await debateApi.startDebate(topicId.value,stance.value,mode.value,true)}
    }
    if(!alive.value)return;applySession(data);if(query.messageId)setTimeout(()=>{if(alive.value)scrollTarget.value=`debate-${query.messageId}`},80);if(data.resumed&&!query.messageId)uni.showToast({title:data.status==='awaiting_feedback'?'已恢复：报告待生成':'已继续上次辩论',icon:'none'})
    if(data.status==='awaiting_feedback')setTimeout(finish,350)
  }catch(error:any){if(alive.value)uni.showModal({title:'赛场暂未开启',content:error.message||'AI 服务暂不可用',showCancel:false})}
  finally{if(alive.value)thinking.value=false}
})
onUnload(()=>{alive.value=false})

function confirmResume(data:DebateSession):Promise<boolean>{
  return new Promise(resolve=>uni.showModal({
    title:data.status==='awaiting_feedback'?'发现已结束赛程':'发现未完成辩论',
    content:data.status==='awaiting_feedback'?'上次赛程已结束但报告尚未生成。继续可直接生成报告，也可以重新开赛。':`上次是${data.mode==='full'?'完整赛训':'快速练习'}，已完成 ${data.step_index}/${data.total_steps} 步。`,
    confirmText:data.status==='awaiting_feedback'?'生成报告':'继续上次',cancelText:'重新开赛',
    success:result=>resolve(result.confirm),fail:()=>resolve(true),
  }))
}

async function submitMessage(content:string,message:LocalMessage){
  if(thinking.value||status.value!=='in_progress')return
  message.local_status='pending';thinking.value=true;scrollBottom()
  try{
    const result=await debateApi.submitArgument(sid.value,content,message.submission_id!,(message.evidence||[]).map(item=>({chunk_id:item.chunk_id})))
    if(!alive.value)return
    const index=messages.value.findIndex(item=>item.id===message.id)
    const analysis={step:result.step,step_label:result.step_label,coach_feedback:result.coach_feedback,argument_map:result.argument_map}
    if(index>=0)messages.value[index]={...message,id:result.user_message_id,analysis,evidence:message.evidence||[],local_status:'sent'}
    messages.value.push({id:result.ai_message_id,role:'ai',content:result.argument,stage:result.stage,transition:result.phase_transition,local_status:'sent'})
    status.value=result.status;currentStage.value=result.next_stage;currentStep.value=result.next_step;stepIndex.value=result.step_index;totalSteps.value=result.total_steps
    stepLabel.value=result.is_finished?'已完成':({user_question:'主动质询',user_counter_answer:'回答反质询',user_rebuttal:'核心驳论',user_defense:'补充防守',user_closing:'总结陈词'} as Record<string,string>)[result.next_step]||'下一步'
    selectedEvidence.value=[];rebuildMap();scrollBottom()
    if(result.is_finished){uni.showToast({title:'全部赛程已完成',icon:'success'});setTimeout(finish,600)}
  }catch(error:any){if(alive.value){message.local_status='failed';uni.showToast({title:error.message||'提交失败，请重试',icon:'none'})}}
  finally{if(alive.value){thinking.value=false;scrollBottom()}}
}
function send(){const content=text.value.trim();if(!content||!canSend.value)return;text.value='';activeTab.value='court';const submissionId=`sub-${Date.now()}-${Math.random().toString(36).slice(2,10)}`;const message:LocalMessage={id:`local-${submissionId}`,role:'user',content,stage:currentStage.value,submission_id:submissionId,local_status:'pending',evidence:[...selectedEvidence.value]};messages.value.push(message);submitMessage(content,message)}
function retryMessage(message:LocalMessage){if(!message.submission_id)message.submission_id=`sub-${Date.now()}-${Math.random().toString(36).slice(2,10)}`;submitMessage(message.content,message)}
async function finish(){
  if(!sid.value||reportState.value==='generating')return
  status.value='awaiting_feedback';currentStage.value='finished';reportState.value='generating'
  try{await debateApi.endDebate(sid.value);if(!alive.value)return;status.value='completed';reportState.value='completed';gotoReport()}
  catch(error:any){if(alive.value){reportState.value='failed';uni.showToast({title:error.message||'报告生成失败，可稍后重试',icon:'none'})}}
}
function gotoReport(){uni.redirectTo({url:`/pages/debate/feedback?sessionId=${sid.value}&topicId=${topicId.value}&topic=${encodeURIComponent(topicTitle.value)}&stance=${stance.value}&mode=${mode.value}`})}
async function searchEvidence(){
  const query=evidenceQuery.value.trim();if(!query||searching.value||!sid.value)return;searching.value=true
  try{evidenceResults.value=await debateApi.searchEvidence(sid.value,query)}catch(error:any){uni.showToast({title:error.message||'资料检索失败',icon:'none'})}finally{searching.value=false}
}
function isSelected(item:DebateEvidence){return selectedEvidence.value.some(row=>row.chunk_id===item.chunk_id)}
function toggleEvidence(item:DebateEvidence){const index=selectedEvidence.value.findIndex(row=>row.chunk_id===item.chunk_id);if(index>=0)return selectedEvidence.value.splice(index,1);if(selectedEvidence.value.length>=3)return uni.showToast({title:'每轮最多引用3条资料',icon:'none'});selectedEvidence.value.push(item)}
</script>

<style scoped>
.arena{height:100%;min-height:0;display:grid;grid-template-rows:auto auto minmax(0,1fr) auto;overflow:hidden;background:#eee7da;color:var(--color-text)}.arena__masthead{min-width:0;padding:18rpx 28rpx 0;background:#24221f;color:#fff9ed}.arena__folio{display:flex;justify-content:space-between;font-size:14rpx;letter-spacing:2rpx;color:#d7bd7a}.arena__topic{display:block;margin:11rpx 0 17rpx;font:700 28rpx/1.4 var(--font-display);overflow-wrap:anywhere}
.stage-track{position:relative;display:grid;grid-template-columns:repeat(4,1fr);padding-bottom:17rpx}.stage-track>view:not(.stage-track__line){position:relative;z-index:2;text-align:center;color:rgba(255,249,237,.38)}.stage-track i{display:grid;place-items:center;width:30rpx;height:30rpx;margin:0 auto 4rpx;border:1px solid currentColor;border-radius:50%;background:#24221f;font-size:14rpx;font-style:normal}.stage-track text{font-size:16rpx}.stage-track .active,.stage-track .done{color:#e7c981!important}.stage-track .active i{color:#24221f;background:#e7c981}.stage-track__line{position:absolute;left:12.5%;right:12.5%;top:15rpx;height:2rpx;background:rgba(255,255,255,.14)}.stage-track__line view{height:100%;background:#e7c981;transition:width .4s}
.arena__tabs{display:grid;grid-template-columns:repeat(3,1fr);background:#fffaf0;border-bottom:1px solid rgba(72,25,22,.14)}.arena__tabs button{position:relative;margin:0;padding:14rpx 0;border:0;border-bottom:3rpx solid transparent;border-radius:0;background:transparent;color:#84786c;font-size:19rpx;line-height:1.3}.arena__tabs button.active{border-bottom-color:#7f211d;color:#7f211d;font-weight:700}.arena__tabs i{display:inline-grid;place-items:center;width:27rpx;height:27rpx;margin-left:6rpx;border-radius:50%;background:#7f211d;color:white;font-size:13rpx;font-style:normal}
.arena__workspace{min-height:0;display:flex;overflow:hidden}.court,.side-panel{flex:1;height:100%}.court__inner,.side-panel{box-sizing:border-box;padding:20rpx 27rpx}.step-card{display:block;box-sizing:border-box;width:100%;margin-bottom:24rpx;padding:19rpx 21rpx 20rpx;background:#fffaf0;border:1px solid rgba(162,123,53,.22);border-left:4rpx solid #a27b35;box-shadow:0 7rpx 22rpx rgba(43,31,22,.07)}.step-card__head{display:flex;align-items:center;justify-content:space-between;margin-bottom:9rpx}.step-card__head text{font-size:14rpx;letter-spacing:2rpx;color:#a27b35}.step-card__head i{padding:2rpx 9rpx;border:1px solid rgba(162,123,53,.35);color:#8a682e;font-size:13rpx;font-style:normal;letter-spacing:1rpx}.step-card>strong{display:block;font:700 24rpx/1.45 var(--font-display);color:#3e332a}.step-card__goal{display:block;margin-top:7rpx;font-size:19rpx;line-height:1.65;color:#62574d}.step-card>small{display:block;margin-top:8rpx;padding-top:8rpx;border-top:1px solid rgba(72,25,22,.08);font-size:16rpx;color:#94887c}
.speech{display:block;box-sizing:border-box;width:100%;margin-bottom:24rpx}.speech__meta{display:flex;align-items:center;justify-content:space-between;margin-bottom:7rpx;font-size:17rpx;color:#766b60}.speech__meta>text{font-weight:700;letter-spacing:1rpx}.speech__meta i{padding:2rpx 9rpx;background:rgba(127,33,29,.07);color:#7f211d;font-size:14rpx;font-style:normal}.speech__content{display:block;box-sizing:border-box;width:100%;padding:20rpx 22rpx;background:#fffaf0;border:1px solid rgba(72,25,22,.08);border-left:3rpx solid #a27b35;font-size:22rpx;line-height:1.78;white-space:pre-wrap;overflow-wrap:anywhere;word-break:break-word}.speech.is-user .speech__meta{color:#7f211d}.speech.is-user .speech__content{background:#4a1917;border-color:#4a1917;border-left-color:#e7c981;color:#fff9ed}.speech__sources{display:flex;flex-wrap:wrap;gap:6rpx;margin-top:7rpx}.speech__sources text{padding:5rpx 9rpx;background:#e7ddc9;color:#6e5c3e;font-size:14rpx}.coach-inline{display:block;box-sizing:border-box;width:100%;margin-top:7rpx;padding:13rpx 16rpx;background:#fffaf0;border:1px solid rgba(49,91,73,.2)}.coach-inline text,.coach-inline strong,.coach-inline small{display:block}.coach-inline text{font-size:14rpx;letter-spacing:2rpx;color:#315b49}.coach-inline strong{margin-top:4rpx;font-size:18rpx}.coach-inline small{margin-top:4rpx;font-size:16rpx;line-height:1.5;color:#7d7267}.stage-transition{display:flex;box-sizing:border-box;width:100%;gap:8rpx;margin-top:9rpx;padding:13rpx 15rpx;background:#efe2ca;border-left:3rpx solid #7f211d;font-size:17rpx;line-height:1.5;color:#66584a}.stage-transition i{color:#7f211d;font-style:normal}.speech__thinking{color:#8e8276}.delivery{display:block;margin-top:5rpx;text-align:right;font-size:15rpx;color:#93877a}.delivery--failed{display:flex;justify-content:flex-end;align-items:center;gap:8rpx;color:#a13a32}.delivery button{margin:0;padding:4rpx 10rpx;border:1px solid #a13a32;background:transparent;color:#a13a32;font-size:15rpx;line-height:1.3}.bottom-anchor{display:block;height:2rpx}
.panel-title{display:block;box-sizing:border-box;width:100%;margin-bottom:18rpx;padding-bottom:15rpx;border-bottom:1px solid rgba(72,25,22,.16)}.panel-title text,.panel-title strong,.panel-title small{display:block}.panel-title text{font-size:13rpx;letter-spacing:3rpx;color:#a27b35}.panel-title strong{margin-top:4rpx;font:700 28rpx var(--font-display)}.panel-title small{margin-top:5rpx;font-size:16rpx;color:#8d8175}.empty-panel{display:block;box-sizing:border-box;width:100%;padding:45rpx 25rpx;text-align:center;background:#f7f0e4;border:1px dashed #cfc2af;font-size:18rpx;line-height:1.6;color:#918579}.map-card,.evidence-card{margin-bottom:13rpx;padding:18rpx;background:#fffaf0;border:1px solid rgba(72,25,22,.12)}.map-card__head{display:flex;align-items:center;gap:9rpx;margin-bottom:11rpx}.map-card__head i{display:grid;place-items:center;width:30rpx;height:30rpx;border-radius:50%;background:#7f211d;color:white;font-size:14rpx;font-style:normal}.map-card__head text{font-weight:700}.map-unit{margin-top:9rpx}.map-unit strong,.map-unit text{display:block}.map-unit strong{font-size:15rpx;color:#a27b35}.map-unit text{position:relative;margin-top:4rpx;padding-left:15rpx;font-size:18rpx;line-height:1.5}.map-unit text::before{content:'·';position:absolute;left:2rpx;color:#7f211d}.map-unit--gap{padding:9rpx 11rpx;background:rgba(155,61,50,.06)}.map-unit--gap strong{color:#9b3d32}
.evidence-search{display:flex;gap:8rpx;margin-bottom:12rpx}.evidence-search input{flex:1;height:67rpx;padding:0 16rpx;background:#fffaf0;border:1px solid rgba(72,25,22,.15);font-size:19rpx}.evidence-search button{margin:0;padding:0 20rpx;border:0;border-radius:0;background:#7f211d;color:white;font-size:18rpx}.selected-box{display:flex;justify-content:space-between;align-items:center;margin-bottom:12rpx;padding:10rpx 13rpx;background:#e8efe9;color:#315b49;font-size:16rpx}.selected-box button{margin:0;padding:3rpx 8rpx;border:0;background:transparent;color:#315b49;font-size:15rpx}.evidence-card.selected{border-color:#315b49;background:#f4f8f3}.evidence-card>view{display:flex;justify-content:space-between;gap:10rpx}.evidence-card strong{font-size:19rpx}.evidence-card i{flex:none;color:#315b49;font-size:15rpx;font-style:normal}.evidence-card>text{display:block;margin-top:8rpx;font-size:17rpx;line-height:1.55;color:#6f655b}.evidence-card small{display:block;margin-top:7rpx;color:#9a8e82;font-size:14rpx}
.composer{min-width:0;box-sizing:border-box;padding:10rpx 27rpx calc(13rpx + env(safe-area-inset-bottom));background:#fffaf0;border-top:1px solid rgba(72,25,22,.15);box-shadow:0 -8rpx 24rpx rgba(43,31,22,.045)}.composer__meta{display:flex;justify-content:space-between;margin-bottom:6rpx;font-size:15rpx;color:#8c8074}.composer__meta text{color:#7f211d;font-weight:700}.composer__row{display:flex;align-items:flex-end;gap:9rpx}.composer textarea{flex:1;min-height:66rpx;max-height:170rpx;box-sizing:border-box;padding:14rpx 16rpx;background:#f0e9dd;border:1px solid transparent;font-size:21rpx;line-height:1.45;resize:none;overflow-y:auto}.composer__row button{flex:none;height:68rpx;margin:0;padding:0 19rpx;border:0;border-radius:0;background:#7f211d;color:white;font-size:19rpx;white-space:nowrap}.composer__row button:disabled{opacity:.45}.composer__evidence{display:flex;gap:6rpx;overflow-x:auto;margin-top:7rpx}.composer__evidence text{flex:none;padding:4rpx 8rpx;background:#e8efe9;color:#315b49;font-size:14rpx}.composer__evidence i{margin-left:6rpx;font-style:normal}
.finish-layer{position:fixed;z-index:30;inset:0;display:grid;place-items:center;padding:32rpx;background:rgba(22,19,16,.78);backdrop-filter:blur(5px)}.finish-card{width:min(610rpx,88vw);box-sizing:border-box;padding:40rpx 34rpx;text-align:center;background:#fffaf0;border:5rpx double #a27b35;box-shadow:0 30rpx 80rpx rgba(0,0,0,.35)}.finish-card__seal{display:grid;place-items:center;width:90rpx;height:90rpx;margin:0 auto 16rpx;border:4rpx double #7f211d;border-radius:50%;color:#7f211d;font:700 27rpx var(--font-display);transform:rotate(-7deg)}.finish-card__eyebrow{display:block;font-size:14rpx;letter-spacing:4rpx;color:#a27b35}.finish-card strong{display:block;margin:8rpx 0 12rpx;font:700 31rpx var(--font-display)}.finish-card>text:not(.finish-card__seal):not(.finish-card__eyebrow){display:block;font-size:19rpx;line-height:1.6;color:#75695e}.finish-card__progress{height:4rpx;margin:23rpx 0;background:#dfd4c3;overflow:hidden}.finish-card__progress i{display:block;width:45%;height:100%;background:#7f211d;transform:translateX(-100%)}.finish-card__progress i.active{animation:loading 1.2s infinite}.finish-card button{width:100%;margin-top:6rpx;padding:18rpx;border:0;border-radius:0;background:#7f211d;color:white;font-size:21rpx}@keyframes loading{to{transform:translateX(225%)}}
/* #ifndef H5 */
@media (min-width: 1100px){.arena__tabs{display:none}.arena__workspace{display:grid;grid-template-columns:minmax(0,1.4fr) minmax(280px,.72fr) minmax(280px,.72fr)}.court,.side-panel{display:block!important}.court{border-right:1px solid rgba(72,25,22,.15)}.side-panel:nth-of-type(2){border-right:1px solid rgba(72,25,22,.12)}.arena__masthead,.composer{padding-left:40rpx;padding-right:40rpx}.court__inner{padding:25rpx 40rpx}}
/* #endif */
/* #ifdef H5 */
@container (min-width: 1100px){.arena__tabs{display:none}.arena__workspace{display:grid;grid-template-columns:minmax(0,1.4fr) minmax(280px,.72fr) minmax(280px,.72fr)}.court,.side-panel{display:block!important}.court{border-right:1px solid rgba(72,25,22,.15)}.side-panel:nth-of-type(2){border-right:1px solid rgba(72,25,22,.12)}.arena__masthead,.composer{padding-left:40rpx;padding-right:40rpx}.court__inner{padding:25rpx 40rpx}}
/* #endif */
.map-card,.evidence-card{display:block;box-sizing:border-box}
.evidence-search input{font-size:22rpx}.evidence-search button{font-size:20rpx}
.evidence-card strong{font-size:22rpx;line-height:1.45}.evidence-card i{font-size:18rpx}
.evidence-card>text{display:-webkit-box;overflow:hidden;-webkit-box-orient:vertical;-webkit-line-clamp:5;font-size:21rpx;line-height:1.65}
.evidence-card small{margin-top:9rpx;font-size:17rpx}
.arena{height:100%;min-height:0}
.arena__workspace{min-height:0;overflow:hidden}
.court,.side-panel{display:block;min-height:0;overflow-x:hidden;overflow-y:auto;overscroll-behavior:contain;touch-action:pan-y;-webkit-overflow-scrolling:touch;scroll-padding-bottom:24rpx;scrollbar-width:thin}
.court__inner{display:block;box-sizing:border-box;min-height:100%;padding-bottom:40rpx}
</style>
