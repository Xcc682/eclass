<template>
  <div class="post">
    <div v-if="post" class="post__card">
      <span class="post__title">{{ post.title }}</span>
      <span class="post__meta">{{ post.author }} · {{ post.category }}</span>
      <span class="post__content">{{ post.content }}</span>
      <button @click="like">❤️ {{ post.likes }}</button>
    </div>
    <div class="post__card">
      <span class="post__title">回复</span>
      <div v-for="reply in post?.reply_list || []" :key="reply.id" class="post__reply">
        <b>{{ reply.author }}{{ reply.is_teacher ? '（教师）' : '' }} <em v-if="reply.accepted">已采纳</em></b>
        <span>{{ reply.content }}</span>
        <button v-if="canResolve && !post?.resolved" class="post__accept" @click="resolveReply(reply.id)">采纳为最佳回答</button>
      </div>
      <textarea v-model="replyText" placeholder="写下你的回复" />
      <button class="post__submit" @click="submitReply">提交回复</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { communityApi, type CommunityPost } from '@/api/community'
import { userApi, type UserInfo } from '@/api/user'

const id = ref('')
const post = ref<CommunityPost | null>(null)
const replyText = ref('')
const profile = ref<UserInfo | null>(null)
const canResolve = computed(() => Boolean(post.value && profile.value && (post.value.author_id === profile.value.id || ['teacher','admin'].includes(profile.value.role))))
async function load() { post.value = await communityApi.getPost(id.value) }
onLoad(async (query: any) => { id.value = query.id || ''; try { const values = await Promise.all([userApi.getProfile(), load()]); profile.value = values[0] } catch (error: any) { uni.showToast({ title: error.message, icon: 'none' }) } })
async function submitReply() { if (!replyText.value.trim()) return; await communityApi.reply(id.value, replyText.value.trim()); replyText.value = ''; await load() }
async function like() { const result = await communityApi.like(id.value); if (post.value) post.value.likes = result.likes }
async function resolveReply(replyId:string){await communityApi.resolve(id.value,replyId);await load();uni.showToast({title:'已采纳回答',icon:'success'})}
</script>

<style scoped>
.post { min-height:100vh; padding:24rpx; background:var(--color-bg); }
.post__card { background:#fff; border-radius:18rpx; padding:28rpx; margin-bottom:20rpx; }
.post__title { display:block; font-family: 'STKaiti', 'Noto Serif SC', serif;
  font-size:32rpx; font-weight:700; }
.post__meta { display:block; color:var(--color-text-muted); font-size:22rpx; margin:8rpx 0 20rpx; }
.post__content { display:block; white-space:pre-wrap; margin-bottom:20rpx; }
.post__reply { border-top:1px solid #eee; padding:16rpx 0; display:flex; flex-direction:column; }
.post__reply em{font-style:normal;color:#2e7d32;font-size:20rpx}.post__accept{align-self:flex-start;margin-top:10rpx;padding:8rpx 14rpx;border:1rpx solid #2e7d32;color:#2e7d32;border-radius:8rpx}

.post__submit { width:100%; margin-top:16rpx; background:#C41E1A; color:#fff; padding:18rpx; }
</style>
