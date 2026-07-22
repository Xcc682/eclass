<template>
  <div class="writer-page">
    <header><span>WRITING STUDIO</span><h1>思政写作台</h1><p>AI 生成的是可编辑初稿，请结合本人真实经历核对修改。</p></header>
    <div class="workspace">
      <aside><button v-for="tpl in templates" :key="tpl.id" :class="{active:selected?.id===tpl.id}" @click="selected=tpl"><b>{{ tpl.name }}</b><small>{{ tpl.desc }}</small></button><button class="history-button" @click="showHistory=!showHistory">历史记录</button></aside>
      <main>
        <template v-if="!showHistory">
          <label>个人情况<textarea v-model="background" placeholder="如：专业年级、成长经历、近期学习实践。请勿填写身份证号等敏感信息。"/></label>
          <label>具体要求<textarea v-model="requirements" placeholder="篇幅、主题、希望重点表达的内容…"/></label>
          <button class="generate" :disabled="!selected||generating" @click="generate">{{ generating?'正在生成…':'生成可编辑初稿' }}</button>
          <label v-if="content">生成结果<textarea v-model="content" class="result"/></label>
          <div v-if="content" class="result-actions"><div><button @click="copy">复制全文</button><button @click="saveEdit">保存修改</button></div><span>{{ saved ? '修改已保存' : '内容有修改' }}</span></div>
        </template>
        <template v-else><article v-for="item in history" :key="item.id"><b>{{ item.title }}</b><small>{{ new Date(item.created_at).toLocaleString() }}</small><p>{{ item.content }}</p><footer><button @click="openHistory(item)">继续编辑</button><button @click="removeHistory(item.id)">删除</button></footer></article><div v-if="!history.length" class="empty">暂无生成记录</div></template>
      </main>
    </div>
  </div>
</template>
<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { knowledgeApi, type KnowledgeTemplate } from '@/api/knowledge'
const templates=ref<KnowledgeTemplate[]>([]);const selected=ref<KnowledgeTemplate>();const background=ref('');const requirements=ref('');const content=ref('');const generating=ref(false);const showHistory=ref(false);const history=ref<any[]>([]);const reportId=ref('');const saved=ref(true);const savedContent=ref('')
async function generate(){if(!selected.value)return;generating.value=true;try{const result=await knowledgeApi.generate(selected.value.id,requirements.value,background.value);reportId.value=result.id;savedContent.value=result.content;content.value=result.content;saved.value=true;history.value=await knowledgeApi.templateHistory()}catch(event:any){uni.showToast({title:event.message,icon:'none'})}finally{generating.value=false}}
function copy(){(uni as any).setClipboardData({data:content.value,success:()=>uni.showToast({title:'已复制',icon:'success'})})}
async function saveEdit(){if(!reportId.value)return;try{await knowledgeApi.updateTemplateHistory(reportId.value,content.value);savedContent.value=content.value;saved.value=true;history.value=await knowledgeApi.templateHistory();uni.showToast({title:'修改已保存',icon:'success'})}catch(event:any){uni.showToast({title:event.message||'保存失败',icon:'none'})}}
function openHistory(item:any){reportId.value=item.id;savedContent.value=item.content;content.value=item.content;showHistory.value=false;saved.value=true}
async function removeHistory(id:string){const confirmed=await new Promise<boolean>(resolve=>uni.showModal({title:'删除记录',content:'确定删除这份生成记录吗？',success:r=>resolve(Boolean(r.confirm)),fail:()=>resolve(false)}));if(!confirmed)return;await knowledgeApi.deleteTemplateHistory(id);history.value=history.value.filter(item=>item.id!==id)}
watch(content,value=>{if(reportId.value)saved.value=value===savedContent.value})
watch(showHistory,async value=>{if(value)history.value=await knowledgeApi.templateHistory()})
onMounted(async()=>{templates.value=await knowledgeApi.getTemplates();selected.value=templates.value[0];history.value=await knowledgeApi.templateHistory()})
</script>
<style scoped>
.writer-page{min-height:100vh;background:#f0eadf;padding:32rpx;color:#302b25}.writer-page>header{max-width:960rpx;margin:0 auto 24rpx}.writer-page>header span{font-size:18rpx;letter-spacing:5rpx;color:#8d211b}.writer-page h1{font-family:"STKaiti","KaiTi",serif;font-size:48rpx;margin:8rpx 0}.writer-page header p{font-size:22rpx;color:#786d62}.workspace{max-width:960rpx;margin:auto;display:grid;grid-template-columns:260rpx 1fr;background:#fffdf8;border:1rpx solid #ded1be;min-height:650rpx}.workspace aside{padding:18rpx;background:#36312c}.workspace aside button{display:block;width:100%;text-align:left;border:0;background:transparent;color:#ded3c4;padding:20rpx;border-radius:10rpx}.workspace aside b,.workspace aside small{display:block}.workspace aside small{margin-top:6rpx;color:#a99d8e}.workspace aside .active{background:#8d211b;color:#fff}.workspace aside .active small{color:#f1cfc5}.history-button{margin-top:22rpx;border-top:1rpx solid #635b53!important}.workspace main{padding:30rpx}.workspace label{display:block;font-size:22rpx;color:#6f6357;margin-bottom:22rpx}.workspace textarea{display:block;width:100%;box-sizing:border-box;min-height:130rpx;margin-top:9rpx;padding:20rpx;background:#f3ece1;border-radius:10rpx;font-size:24rpx}.workspace textarea.result{min-height:360rpx;font-family:"STSong","SimSun",serif;line-height:1.8}.generate{width:100%;border:0;border-radius:10rpx;background:#8d211b;color:#fff;padding:20rpx;margin-bottom:24rpx}.generate:disabled{opacity:.45}.result-actions{display:flex;justify-content:space-between;align-items:center;color:#887b6f;font-size:20rpx}.result-actions button{border:1rpx solid #8d211b;background:#fff;color:#8d211b;padding:12rpx 24rpx;border-radius:8rpx}.workspace article{border-bottom:1rpx solid #e6dac9;padding:18rpx 0}.workspace article b,.workspace article small{display:block}.workspace article small{color:#9b8f82;margin:6rpx 0}.workspace article p{white-space:pre-wrap;max-height:180rpx;overflow:auto;font-size:22rpx;line-height:1.6}.empty{text-align:center;padding:100rpx;color:#8b7e70}@media(max-width:600px){.workspace{grid-template-columns:1fr}.workspace aside{display:flex;overflow:auto}.workspace aside button{min-width:190rpx}.history-button{margin:0!important;border-top:0!important}}
.workspace article footer,.result-actions>div{display:flex;gap:12rpx}.workspace article footer button{padding:10rpx 16rpx;border:1rpx solid #d7c8b5;border-radius:8rpx;color:#7d211b}
</style>
