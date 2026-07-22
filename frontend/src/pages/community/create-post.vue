<template>
  <div class="create">
    <header><span>成长社区</span><h1>{{ isQuestion ? '提出问题' : '发布学习分享' }}</h1><p>{{ isQuestion ? '把问题描述清楚，方便老师和同学准确回答。' : '记录真实学习收获，让讨论更有内容。' }}</p></header>
    <section class="create__card">
      <label>发布类型</label>
      <div class="type-switch"><button :class="{active:!isQuestion}" @click="isQuestion=false">学习分享</button><button :class="{active:isQuestion}" @click="isQuestion=true">互助问答</button></div>
      <label>标题 <small>{{ title.length }}/300</small></label>
      <input v-model="title" :placeholder="isQuestion ? '用一句话说明你的问题' : '为这次分享写一个清晰标题'" maxlength="300" />
      <label>正文 <small>{{ content.length }}/10000</small></label>
      <textarea v-model="content" :placeholder="isQuestion ? '补充背景、你的思考和具体困惑…' : '写下学习过程、核心收获和自己的思考…'" maxlength="10000" />
      <label>分类</label>
      <div class="categories"><button v-for="item in categories" :key="item" :class="{active:category===item}" @click="category=item">{{ item }}</button></div>
      <button class="create__submit" :disabled="submitting" @click="submit">{{ submitting ? '正在发布…' : (isQuestion ? '发布问题' : '发布分享') }}</button>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { communityApi } from '@/api/community'

const title=ref(''); const content=ref(''); const category=ref('学习心得'); const isQuestion=ref(false); const submitting=ref(false)
const categories=['学习心得','理论学习','党史学习','实践活动','校园生活']
onLoad((query:any)=>{ if(query.type==='question'){isQuestion.value=true;category.value='理论学习'} })
async function submit(){
  if(title.value.trim().length<2||content.value.trim().length<2)return uni.showToast({title:'请完整填写标题和正文',icon:'none'})
  submitting.value=true
  try{const post=await communityApi.createPost({title:title.value.trim(),content:content.value.trim(),category:category.value,is_question:isQuestion.value});uni.showToast({title:'发布成功',icon:'success'});uni.redirectTo({url:`/pages/community/post-detail?id=${post.id}`})}
  catch(error:any){uni.showToast({title:error.message||'发布失败',icon:'none'})}finally{submitting.value=false}
}
</script>

<style scoped>
.create{min-height:100vh;padding:30rpx;background:#f5f0e8;box-sizing:border-box}.create header{padding:24rpx 8rpx}.create header>span{font-size:20rpx;letter-spacing:4rpx;color:#8b1a1a}.create h1{margin:8rpx 0;font:700 42rpx STKaiti,serif;color:#2d2925}.create header p{margin:0;color:#7e7267;font-size:23rpx}.create__card{background:#fffdf8;border:1rpx solid #e8ddce;border-radius:20rpx;padding:30rpx;box-shadow:0 12rpx 32rpx rgba(78,50,28,.06)}label{display:flex;justify-content:space-between;margin:26rpx 0 12rpx;font-weight:600;font-size:24rpx}label:first-child{margin-top:0}label small{color:#9b8e82;font-weight:400}.type-switch{display:grid;grid-template-columns:1fr 1fr;background:#f1e9de;padding:6rpx;border-radius:14rpx}.type-switch button,.categories button{padding:16rpx;border-radius:10rpx;color:#70645a}.type-switch .active,.categories .active{background:#8b1a1a;color:#fff}.create textarea{min-height:300rpx}.categories{display:flex;flex-wrap:wrap;gap:10rpx}.categories button{background:#f4ede3;padding:12rpx 18rpx}.create__submit{width:100%;margin-top:34rpx;background:linear-gradient(135deg,#9f241d,#761512);color:#fff;padding:24rpx;border-radius:16rpx;font-weight:700}.create__submit:disabled{opacity:.55}
</style>
