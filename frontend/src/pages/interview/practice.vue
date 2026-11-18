<template>
  <view class="practice">
    <view class="practice__header">
      <view class="practice__identity">
        <view class="practice__avatar">谈</view>
        <view><text class="practice__name">{{ roleName }}</text><text class="practice__title">{{ roleTitle }}</text></view>
      </view>
      <button class="practice__hint" :disabled="isThinking" @click="showHint">回答提示</button>
    </view>

    <view class="phase-rail">
      <view v-for="(item,index) in phases" :key="item" class="phase-rail__item" :class="{ active:index===activePhaseIndex, done:index<activePhaseIndex }">
        <i>{{ index < activePhaseIndex ? '✓' : index + 1 }}</i><text>{{ item }}</text>
      </view>
      <view class="phase-rail__track"><view :style="{ width: phaseProgress + '%' }"></view></view>
    </view>

    <view class="ability" :class="{ 'ability--open': abilityOpen }">
      <view class="ability__head" @click="abilityOpen=!abilityOpen">
        <view><text class="ability__eyebrow">LIVE OBSERVATION</text><strong>能力观察</strong></view>
        <view class="ability__meta"><text>已完成 {{ answeredCount }}/{{ totalQuestions }}<template v-if="currentQuestionNumber"> · 当前第 {{ currentQuestionNumber }} 题</template><template v-else> · 谈话已结束</template></text><i>{{ abilityOpen ? '收起' : '展开' }}</i></view>
      </view>
      <view v-if="abilityOpen" class="ability__body">
        <view v-for="(item,name) in liveDimensions" :key="name" class="ability__row">
          <view class="ability__line"><text>{{ name }}</text><strong v-if="item.score!==null">{{ item.score }}<small>分</small></strong><em v-else>待观察 · {{ item.evidence_count }}/2</em></view>
          <view class="ability__track"><view :class="`is-${item.trend}`" :style="{width:(item.score ?? 0)+'%'}"></view></view>
          <text v-if="item.latest_evidence" class="ability__evidence">依据：{{ item.latest_evidence }}</text>
        </view>
        <text class="ability__notice">{{ liveEvaluation.disclaimer || 'AI 训练预估，不代表党组织正式评价' }}</text>
      </view>
    </view>

    <scroll-view ref="messageScroller" class="practice__messages" scroll-y :scroll-into-view="scrollTarget" :show-scrollbar="false">
      <view class="practice__messages-inner">
        <view v-for="msg in messages" :id="`msg-${msg.id}`" :key="msg.id" class="turn">
          <ChatBubble :role="msg.role" :content="msg.content" :name="msg.role==='ai'?roleName:'我'" :images="msg.images" />
          <view v-if="msg.role==='ai' && analysisOf(msg).comment" class="turn-note">
            <view class="turn-note__head"><text>本轮观察</text><i>{{ followUpLabel(analysisOf(msg).follow_up_type) }}</i></view>
            <text>{{ analysisOf(msg).comment }}</text>
          </view>
          <view v-if="msg.role==='ai' && analysisOf(msg).scenario" class="scenario-card">
            <text class="scenario-card__label">情景任务</text><text>{{ analysisOf(msg).scenario }}</text><small>请结合真实判断说明你的选择和理由</small>
          </view>
          <view v-if="msg.role==='user' && msg.local_status==='pending'" class="delivery">正在发送并等待回应…</view>
          <view v-if="msg.role==='user' && msg.local_status==='failed'" class="delivery delivery--failed"><text>发送失败，轮次和评分未更新</text><button @click="retryMessage(msg)">重新发送</button></view>
        </view>
        <view v-if="isThinking" class="practice__thinking"><ChatBubble role="ai" content="" :name="roleName" :is-analyzing="true" /></view>
        <view v-if="status==='awaiting_report' || status==='completed'" class="complete-card">
          <text class="complete-card__seal">完成</text><view><strong>六轮谈话已经完成</strong><text>所有回答已保存，现在可以生成完整训练报告。</text></view>
        </view>
        <view id="message-bottom" class="message-bottom"></view>
      </view>
    </scroll-view>

    <view class="practice__footer">
      <view class="practice__current"><text>{{ currentPhase }}</text><span>{{ currentStepLabel }}</span></view>
      <ChatInput v-if="status==='in_progress'" :disabled="isThinking" :placeholder="isThinking ? '正在分析本轮回答…' : '输入你的真实回答…'" @send="handleSend" />
      <button v-else class="report-button" :disabled="ending" @click="endPractice">{{ ending ? '正在生成训练报告…' : status==='completed' ? '查看评估报告' : '生成完整评估报告' }}</button>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import { onLoad, onUnload } from '@dcloudio/uni-app'
import ChatBubble from '@/components/chat/ChatBubble.vue'
import ChatInput from '@/components/chat/ChatInput.vue'
import { interviewApi, type InterviewMessage, type InterviewPractice, type InterviewStatus, type LiveEvaluation } from '@/api/interview'

const phases=['开场寒暄','自我认知','入党动机','理论考察','情景假设']
const phaseMap:Record<string,number>={开场寒暄:0,自我认知:1,入党动机:2,理论考察:3,情景假设:4}
const practiceId=ref(''),roleName=ref('张老师'),roleTitle=ref('院党委组织委员')
const messages=ref<InterviewMessage[]>([]),status=ref<InterviewStatus>('in_progress'),currentPhase=ref('开场寒暄')
const questionIndex=ref(1),answeredCount=ref(0),currentQuestionNumber=ref<number|null>(1),totalQuestions=ref(6),phaseStep=ref(0),isThinking=ref(false),ending=ref(false),abilityOpen=ref(false)
const scrollTarget=ref(''),messageScroller=ref<any>(null),alive=ref(true)
const liveEvaluation=ref<LiveEvaluation>({dimensions:{},disclaimer:'AI 训练预估，不代表党组织正式评价'})
const activePhaseIndex=computed(()=>phaseMap[currentPhase.value] ?? Math.min(4,phaseStep.value))
const phaseProgress=computed(()=>activePhaseIndex.value>=4?100:Math.max(8,(activePhaseIndex.value/4)*100))
const liveDimensions=computed(()=>liveEvaluation.value.dimensions || {})
const currentStepLabel=computed(()=>phaseStep.value===3?'理论理解':phaseStep.value===4?'理论追问':phaseStep.value===5?'情景判断':'阶段训练')

function analysisOf(msg:InterviewMessage){return msg.analysis || msg.ai_analysis || {}}
function followUpLabel(value:string){return ({probe:'深入追问',challenge:'校准方向',encourage:'继续深化'} as Record<string,string>)[value]||'即时点评'}
function scrollBottom(){nextTick(()=>{scrollTarget.value='';setTimeout(()=>{if(!alive.value)return;scrollTarget.value='message-bottom';const scroller=messageScroller.value;if(scroller&&typeof scroller.scrollTo==='function')scroller.scrollTo({top:scroller.scrollHeight,behavior:'smooth'})},20)})}
function applyPractice(data:InterviewPractice){
  practiceId.value=data.id;status.value=data.status;currentPhase.value=data.phase||'开场寒暄';phaseStep.value=data.phase_index||0
  questionIndex.value=data.question_index||1;answeredCount.value=data.answered_count||0;currentQuestionNumber.value=data.current_question_number??null;totalQuestions.value=data.total_questions||6;liveEvaluation.value=data.live_evaluation||liveEvaluation.value
  roleName.value=data.scenario?.ai_role_name||roleName.value;roleTitle.value=data.scenario?.ai_role_title||roleTitle.value
  messages.value=(data.messages||[]).map(item=>({...item,local_status:item.delivery_status||'sent'}));scrollBottom()
}
onLoad(async(query:any)=>{
  roleName.value=query.roleName?decodeURIComponent(query.roleName):roleName.value;roleTitle.value=query.roleTitle?decodeURIComponent(query.roleTitle):roleTitle.value
  isThinking.value=true
  try{
    const data=query.practiceId?await interviewApi.getPractice(query.practiceId):await interviewApi.startPractice(query.scenarioId||'1',query.restart==='1')
    if(!alive.value)return;applyPractice(data);if(data.resumed)uni.showToast({title:data.status==='awaiting_report'?'已恢复：报告待生成':'已继续上次谈话',icon:'none'})
  }catch(error:any){if(alive.value)uni.showModal({title:'谈话暂未开始',content:error.message||'AI 服务暂不可用，请稍后重试。',showCancel:false})}
  finally{if(alive.value)isThinking.value=false}
})
onUnload(()=>{alive.value=false})

async function submitMessage(content:string,message:InterviewMessage,images?:string[]){
  if(isThinking.value||status.value!=='in_progress'||!practiceId.value)return
  message.local_status='pending';isThinking.value=true;scrollBottom()
  try{
    const result=await interviewApi.submitResponse(practiceId.value,content,message.submission_id!,images)
    if(!alive.value)return
    const index=messages.value.findIndex(item=>item.id===message.id)
    if(index>=0)messages.value[index]={...result.user_message,local_status:'sent'}
    messages.value.push({...result.ai_message,local_status:'sent'})
    status.value=result.status;currentPhase.value=result.phase;phaseStep.value=result.phase_index
    questionIndex.value=result.question_index;answeredCount.value=result.answered_count;currentQuestionNumber.value=result.current_question_number;totalQuestions.value=result.total_questions;liveEvaluation.value=result.live_evaluation
    if(result.is_completed){abilityOpen.value=true;uni.showToast({title:'谈话流程已完成',icon:'success'})}
  }catch(error:any){if(alive.value){message.local_status='failed';uni.showToast({title:error.message||'发送失败，请重试',icon:'none'})}}
  finally{if(alive.value){isThinking.value=false;scrollBottom()}}
}
function handleSend(content:string,images?:string[]){
  if(isThinking.value||status.value!=='in_progress'||!practiceId.value)return
  const submissionId=`sub-${Date.now()}-${Math.random().toString(36).slice(2,10)}`
  const message:InterviewMessage={id:`local-${submissionId}`,role:'user',content,round_number:answeredCount.value+1,submission_id:submissionId,local_status:'pending',images:images?.length?images.slice():undefined}
  messages.value.push(message);submitMessage(content,message,images)
}
function retryMessage(message:InterviewMessage){if(!message.submission_id)message.submission_id=`sub-${Date.now()}-${Math.random().toString(36).slice(2,10)}`;submitMessage(message.content,message,message.images)}
async function showHint(){
  if(!practiceId.value)return;uni.showLoading({title:'整理思路中…'})
  try{const data=await interviewApi.getHint(practiceId.value);uni.hideLoading();uni.showModal({title:'思考提示',content:data.hint,showCancel:false})}
  catch{uni.hideLoading();uni.showModal({title:'思考提示',content:'结合个人经历、理论学习和真实行动，用一个具体事例说明你的判断。',showCancel:false})}
}
async function endPractice(){
  if(!practiceId.value||ending.value)return
  if(status.value==='completed'){return uni.redirectTo({url:`/pages/interview/report?practiceId=${practiceId.value}`})}
  ending.value=true
  try{await interviewApi.endPractice(practiceId.value);if(!alive.value)return;status.value='completed';uni.redirectTo({url:`/pages/interview/report?practiceId=${practiceId.value}`})}
  catch(error:any){if(alive.value)uni.showToast({title:error.message||'报告生成失败，可稍后重试',icon:'none'})}
  finally{if(alive.value)ending.value=false}
}
</script>

<style scoped>
.practice{height:calc(100vh - 88rpx);display:flex;flex-direction:column;overflow:hidden;background:#f2ecdf;color:var(--color-text)}
.practice__header{display:flex;align-items:center;justify-content:space-between;padding:18rpx 28rpx;background:#431816;border-bottom:1px solid rgba(231,201,129,.22);color:#fff8e9}.practice__identity{display:flex;align-items:center;gap:15rpx}.practice__avatar{display:grid;place-items:center;width:58rpx;height:58rpx;border:3rpx double #e7c981;border-radius:50%;color:#e7c981;font:700 23rpx var(--font-display)}.practice__name,.practice__title{display:block}.practice__name{font:700 26rpx var(--font-display)}.practice__title{margin-top:2rpx;font-size:16rpx;color:rgba(255,248,233,.52)}.practice__hint{margin:0;padding:9rpx 14rpx;border:1px solid rgba(231,201,129,.35);border-radius:2rpx;background:transparent;color:#e7c981;font-size:18rpx;line-height:1.2}
.phase-rail{position:relative;display:grid;grid-template-columns:repeat(5,1fr);padding:16rpx 18rpx 20rpx;background:#fffaf0;border-bottom:1px solid rgba(72,25,22,.12)}.phase-rail__item{position:relative;z-index:2;text-align:center;color:#9c9082}.phase-rail__item i{display:grid;place-items:center;width:30rpx;height:30rpx;margin:0 auto 5rpx;border:1px solid #c8bdaf;border-radius:50%;background:#fffaf0;font-size:15rpx;font-style:normal}.phase-rail__item text{font-size:15rpx}.phase-rail__item.active,.phase-rail__item.done{color:#7f211d}.phase-rail__item.active i{color:white;background:#7f211d;border-color:#7f211d;box-shadow:0 0 0 5rpx rgba(127,33,29,.1)}.phase-rail__item.done i{color:#7f211d;border-color:#7f211d}.phase-rail__track{position:absolute;left:10%;right:10%;top:31rpx;height:2rpx;background:#d7cec2}.phase-rail__track view{height:100%;background:#7f211d;transition:width .35s}
.ability{background:#fbf6ea;border-bottom:1px solid rgba(72,25,22,.13);box-shadow:0 5rpx 15rpx rgba(48,32,22,.05)}.ability__head{display:flex;align-items:center;justify-content:space-between;padding:13rpx 28rpx}.ability__head strong,.ability__eyebrow{display:block}.ability__head strong{font:700 25rpx var(--font-display)}.ability__eyebrow{font-size:12rpx;letter-spacing:3rpx;color:#a27b35}.ability__meta{display:flex;align-items:center;gap:14rpx;font-size:16rpx;color:var(--color-text-muted)}.ability__meta i{padding:5rpx 10rpx;border:1px solid rgba(72,25,22,.14);font-style:normal;color:#7f211d}.ability__body{display:grid;grid-template-columns:repeat(2,1fr);gap:13rpx 22rpx;padding:7rpx 28rpx 17rpx}.ability__row{min-width:0}.ability__line{display:flex;justify-content:space-between;gap:7rpx;align-items:center}.ability__line text{font-size:20rpx}.ability__line strong{font-size:23rpx;color:#7f211d}.ability__line small{font-size:14rpx}.ability__line em{font-size:16rpx;font-style:normal;color:#a59a8d}.ability__track{height:6rpx;margin-top:7rpx;background:#ded6ca;overflow:hidden}.ability__track view{height:100%;background:#a27b35;transition:width .45s}.ability__track .is-up{background:#315b49}.ability__track .is-down{background:#9b3d32}.ability__evidence{display:none}.ability__notice{grid-column:1/-1;margin-top:3rpx;font-size:15rpx;color:#968b7f}
.practice__messages{flex:1;height:0}.practice__messages-inner{padding:22rpx 0 12rpx}.turn{margin-bottom:2rpx}.turn-note,.scenario-card{margin:-17rpx 32rpx 25rpx 108rpx;padding:16rpx 19rpx;background:#fffaf0;border-left:3px solid #a27b35;font-size:21rpx;line-height:1.6;color:#635a50}.turn-note>text{display:block}.turn-note__head{display:flex;justify-content:space-between;margin-bottom:5rpx}.turn-note__head text{font-weight:700;color:#7f211d}.turn-note__head i{font-size:16rpx;font-style:normal;color:#a27b35}.scenario-card{display:flex;flex-direction:column;gap:6rpx;border-left-color:#7f211d;background:#f8eee0}.scenario-card__label{font-weight:700;color:#7f211d}.scenario-card small{font-size:17rpx;color:#968b7f}.delivery{margin:-22rpx 32rpx 20rpx;text-align:right;font-size:17rpx;color:#968b7f}.delivery--failed{display:flex;justify-content:flex-end;align-items:center;gap:10rpx;color:#a13a32}.delivery button{margin:0;padding:5rpx 12rpx;border:1px solid #a13a32;background:transparent;color:#a13a32;font-size:17rpx;line-height:1.4}.complete-card{display:flex;align-items:center;gap:18rpx;margin:18rpx 32rpx 26rpx;padding:23rpx;background:#fffaf0;border:1px solid rgba(127,33,29,.22);box-shadow:0 8rpx 24rpx rgba(55,36,23,.06)}.complete-card__seal{display:grid;place-items:center;width:62rpx;height:62rpx;border:3rpx double #7f211d;border-radius:50%;color:#7f211d;font:700 19rpx var(--font-display);transform:rotate(-8deg)}.complete-card strong,.complete-card view text{display:block}.complete-card strong{font:700 24rpx var(--font-display)}.complete-card view text{margin-top:4rpx;font-size:18rpx;color:#81766a}.message-bottom{height:2rpx}
.practice__footer{padding:10rpx 0 calc(12rpx + env(safe-area-inset-bottom));background:#fffaf0;border-top:1px solid rgba(72,25,22,.15)}.practice__current{display:flex;justify-content:space-between;padding:0 30rpx 7rpx;font-size:16rpx;color:#93877a}.practice__current text{font-weight:700;color:#7f211d}.report-button{width:calc(100% - 56rpx);margin:6rpx 28rpx 0;padding:21rpx;border:0;border-radius:2rpx;background:#7f211d;color:white;font:700 24rpx var(--font-display)}
/* #ifndef H5 */
@media (min-width: 900px){.practice{max-width:980px;margin:0 auto;border-left:1px solid rgba(72,25,22,.12);border-right:1px solid rgba(72,25,22,.12)}.ability__body{grid-template-columns:repeat(5,1fr)}.ability__evidence{display:block;margin-top:5rpx;font-size:13rpx;line-height:1.4;color:#968b7f}}
/* #endif */
/* #ifdef H5 */
@container (min-width: 900px){.practice{max-width:980px;margin:0 auto;border-left:1px solid rgba(72,25,22,.12);border-right:1px solid rgba(72,25,22,.12)}.ability__body{grid-template-columns:repeat(5,1fr)}.ability__evidence{display:block;margin-top:5rpx;font-size:13rpx;line-height:1.4;color:#968b7f}}
/* #endif */
.turn-note{display:block;box-sizing:border-box}
.practice{height:calc(100dvh - 88rpx);min-height:0}
.practice__messages{display:block;flex:1;height:0;min-height:0;overflow-x:hidden;overflow-y:auto;overscroll-behavior:contain;touch-action:pan-y;-webkit-overflow-scrolling:touch;scroll-padding-bottom:24rpx;scrollbar-width:thin}
.practice__messages-inner{display:block;box-sizing:border-box;min-height:100%;padding-bottom:36rpx}
</style>
