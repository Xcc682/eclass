<template>
  <main class="detail-page">
    <div v-if="loading" class="page-state">正在打开讨论…</div>
    <div v-else-if="error" class="page-state error">
      <p>{{ error }}</p>
      <button @click="load">重新加载</button>
    </div>
    <template v-else-if="post">
      <article class="post-sheet">
        <header>
          <div class="author">
            <img :src="post.avatar_url || defaultAvatar" />
            <div>
              <strong>{{ post.author }}</strong
              ><span
                >{{ roleLabel(post.author_role) }} ·
                {{ format(post.updated_at) }}</span
              >
            </div>
          </div>
          <div class="post-menu">
            <button v-if="post.can_edit" @click="editPost">编辑</button
            ><button v-if="post.can_edit" @click="removePost">删除</button
            ><button @click="report('post', post.id)">举报</button>
          </div>
        </header>
        <div class="post-tags">
          <span>{{ post.category }}</span
          ><span v-if="post.is_question" :class="{ resolved: post.resolved }">{{
            post.resolved ? "问题已解决" : "等待解答"
          }}</span>
        </div>
        <h1>{{ post.title }}</h1>
        <p class="post-content">{{ post.content }}</p>
        <div v-if="post.attachments?.length" class="post-images">
          <img
            v-for="file in post.attachments"
            :key="file.id"
            :src="assetUrl(file.url)"
            loading="lazy"
            @click="preview(file.url)"
          />
        </div>
        <footer>
          <div>
            <span>阅读 {{ post.views }}</span
            ><span>回应 {{ post.replies }}</span>
          </div>
          <button :class="{ active: post.liked }" @click="toggleLike">
            {{ post.liked ? "已赞同" : "赞同" }} {{ post.likes }}</button
          ><button :class="{ active: post.favorited }" @click="toggleFavorite">
            {{ post.favorited ? "已收藏" : "收藏" }} {{ post.favorites }}
          </button>
        </footer>
      </article>

      <section class="reply-section">
        <header class="section-title">
          <div>
            <small>DISCUSSION · {{ post.reply_list?.length || 0 }}</small>
            <h2>{{ post.is_question ? "回答与讨论" : "共同讨论" }}</h2>
          </div>
          <span v-if="post.is_question && !post.resolved"
            >发布者可采纳一条最有帮助的回答</span
          >
        </header>
        <div v-if="!post.reply_list?.length" class="empty-replies">
          还没有回应。写下第一条有内容的回复吧。
        </div>
        <article
          v-for="reply in post.reply_list"
          :id="`reply-${reply.id}`"
          :key="reply.id"
          class="reply-card"
          :class="{ accepted: reply.accepted, child: reply.parent_reply_id }"
        >
          <div v-if="reply.accepted" class="accepted-ribbon">
            已采纳回答 · +2 成果积分
          </div>
          <header>
            <img :src="reply.avatar_url || defaultAvatar" />
            <div>
              <strong
                >{{ reply.author }}
                <em v-if="reply.is_teacher">指导教师</em></strong
              ><span>{{ format(reply.created_at) }}</span>
            </div>
          </header>
          <p>{{ reply.content }}</p>
          <footer>
            <button
              :class="{ active: reply.liked }"
              @click="toggleReplyLike(reply)"
            >
              {{ reply.liked ? "已赞同" : "赞同" }} {{ reply.likes }}</button
            ><button @click="replyTo(reply)">回复</button
            ><button @click="report('reply', reply.id)">举报</button
            ><button v-if="reply.can_edit" @click="removeReply(reply.id)">
              删除</button
            ><button
              v-if="
                post.is_question &&
                !post.resolved &&
                post.can_edit &&
                reply.author_id !== post.author_id
              "
              class="accept"
              @click="accept(reply.id)"
            >
              采纳回答
            </button>
          </footer>
        </article>
      </section>

      <section class="composer">
        <header>
          <div>
            <small>{{ replyingTo ? "REPLY TO" : "JOIN THE DISCUSSION" }}</small
            ><strong>{{
              replyingTo ? `回复 ${replyingTo.author}` : "写下你的回应"
            }}</strong>
          </div>
          <button v-if="replyingTo" @click="replyingTo = null">取消回复</button>
        </header>
        <textarea
          v-model="replyText"
          maxlength="5000"
          :placeholder="
            post.is_question
              ? '请说明依据和推理过程，避免只给结论。'
              : '回应观点、补充资料，或提出新的问题。'
          "
        />
        <footer>
          <small>{{ replyText.length }}/5000</small
          ><span v-if="replyError">{{ replyError }}</span
          ><button
            :disabled="replying || !replyText.trim()"
            @click="submitReply"
          >
            {{ replying ? "发送中…" : replyError ? "重新发送" : "提交回复" }}
          </button>
        </footer>
      </section>
    </template>
  </main>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { onLoad } from "@dcloudio/uni-app";
import {
  communityApi,
  type CommunityPost,
  type CommunityReply,
} from "@/api/community";
import defaultAvatar from "@/static/images/icons/default-avatar.png";
const id = ref(""),
  post = ref<CommunityPost | null>(null),
  loading = ref(true),
  error = ref(""),
  replyText = ref(""),
  replying = ref(false),
  replyError = ref(""),
  replyingTo = ref<CommunityReply | null>(null),
  submissionId = ref("");
async function load() {
  loading.value = true;
  error.value = "";
  try {
    post.value = await communityApi.getPost(id.value);
  } catch (e: any) {
    error.value = e.message || "讨论加载失败";
  } finally {
    loading.value = false;
  }
}
function assetUrl(url: string) {
  const base = import.meta.env.VITE_API_BASE_URL || "/api/v1";
  return url.startsWith("/api/v1")
    ? `${base.replace(/\/api\/v1$/, "")}${url}`
    : url;
}
function format(value: string) {
  return new Date(value).toLocaleString();
}
function roleLabel(role: string) {
  return role === "admin"
    ? "社区管理员"
    : role === "teacher"
      ? "指导教师"
      : "学习伙伴";
}
async function toggleLike() {
  if (!post.value) return;
  const data = post.value.liked
    ? await communityApi.unlike(post.value.id)
    : await communityApi.like(post.value.id);
  post.value.liked = data.liked;
  post.value.likes = data.likes;
}
async function toggleFavorite() {
  if (!post.value) return;
  const data = post.value.favorited
    ? await communityApi.unfavorite(post.value.id)
    : await communityApi.favorite(post.value.id);
  post.value.favorited = data.favorited;
  post.value.favorites = data.favorites;
}
async function toggleReplyLike(reply: CommunityReply) {
  const data = reply.liked
    ? await communityApi.unlikeReply(reply.id)
    : await communityApi.likeReply(reply.id);
  reply.liked = data.liked;
  reply.likes = data.likes;
}
function replyTo(reply: CommunityReply) {
  replyingTo.value = reply;
}
async function submitReply() {
  if (!replyText.value.trim() || replying.value) return;
  if (!submissionId.value)
    submissionId.value = `reply-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  replying.value = true;
  replyError.value = "";
  try {
    await communityApi.reply(id.value, {
      content: replyText.value.trim(),
      parent_reply_id: replyingTo.value?.id,
      submission_id: submissionId.value,
    });
    replyText.value = "";
    replyingTo.value = null;
    submissionId.value = "";
    await load();
  } catch (e: any) {
    replyError.value = e.message || "发送失败，请重试";
  } finally {
    replying.value = false;
  }
}
async function accept(replyId: string) {
  const result = await new Promise<any>((resolve) =>
    uni.showModal({
      title: "采纳这条回答？",
      content: "采纳后问题将标记为已解决，回答者可获得成果积分。",
      success: resolve,
    }),
  );
  if (!result.confirm) return;
  try {
    await communityApi.resolve(id.value, replyId);
    await load();
    uni.showToast({ title: "已采纳回答", icon: "success" });
  } catch (e: any) {
    uni.showToast({ title: e.message || "采纳失败", icon: "none" });
  }
}
async function removeReply(replyId: string) {
  const result = await new Promise<any>((resolve) =>
    uni.showModal({
      title: "删除回复",
      content: "删除后无法恢复，确定继续吗？",
      success: resolve,
    }),
  );
  if (result.confirm) {
    await communityApi.deleteReply(replyId);
    await load();
  }
}
function editPost() {
  uni.navigateTo({ url: `/pages/community/create-post?id=${id.value}` });
}
async function removePost() {
  const result = await new Promise<any>((resolve) =>
    uni.showModal({
      title: "删除内容",
      content: "删除后不会再出现在社区中，确定继续吗？",
      success: resolve,
    }),
  );
  if (result.confirm) {
    await communityApi.deletePost(id.value);
    uni.navigateBack();
  }
}
function report(target_type: "post" | "reply", target_id: string) {
  uni.showActionSheet({
    itemList: [
      "内容不实或误导",
      "不友善或攻击性内容",
      "广告或无关内容",
      "泄露个人信息",
    ],
    success: async (result) => {
      const reasons = [
        "内容不实或误导",
        "不友善或攻击性内容",
        "广告或无关内容",
        "泄露个人信息",
      ];
      try {
        await communityApi.report({
          target_type,
          target_id,
          reason: reasons[result.tapIndex],
        });
        uni.showToast({ title: "已提交审核", icon: "success" });
      } catch (e: any) {
        uni.showToast({ title: e.message || "举报失败", icon: "none" });
      }
    },
  });
}
function preview(url: string) {
  uni.previewImage({
    urls: post.value?.attachments.map((x) => assetUrl(x.url)) || [],
    current: assetUrl(url),
  });
}
onLoad((query: any) => {
  id.value = query.id || "";
  load();
});
</script>

<style scoped>
.detail-page {
  min-height: 100vh;
  padding: 28px max(18px, 5vw) 70px;
  background: #eee7dc;
}
.post-sheet,
.reply-section,
.composer {
  max-width: 860px;
  margin: 0 auto 18px;
  box-sizing: border-box;
  border: 1px solid #d7cbbb;
  background: #fffaf1;
}
.post-sheet {
  padding: 28px 31px;
}
.post-sheet > header,
.author,
.post-sheet > footer,
.reply-card header,
.reply-card footer,
.composer header,
.composer footer {
  display: flex;
  align-items: center;
}
.post-sheet > header {
  justify-content: space-between;
}
.author {
  gap: 11px;
}
.author img,
.reply-card header img {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  object-fit: cover;
}
.author div,
.reply-card header div {
  display: grid;
}
.author strong,
.reply-card strong {
  font-size: 13px;
}
.author span,
.reply-card header span {
  font-size: 10px;
  color: #9a8c7e;
}
.post-menu {
  display: flex;
  gap: 12px;
}
.post-menu button {
  color: #8a7c6e;
  font-size: 10px;
}
.post-tags {
  display: flex;
  gap: 6px;
  margin-top: 23px;
}
.post-tags span {
  padding: 4px 9px;
  background: #f1e6d6;
  color: #99692b;
  font-size: 10px;
}
.post-tags span.resolved {
  background: #e7f0e7;
  color: #386449;
}
.post-sheet h1 {
  margin: 10px 0 14px;
  font-size: 30px;
  line-height: 1.35;
}
.post-content {
  white-space: pre-wrap;
  font-size: 15px;
  line-height: 1.95;
  color: #4d433b;
}
.post-images {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 7px;
  margin-top: 19px;
}
.post-images img {
  width: 100%;
  height: 190px;
  object-fit: cover;
  cursor: zoom-in;
}
.post-sheet > footer {
  justify-content: flex-end;
  gap: 17px;
  margin-top: 24px;
  padding-top: 15px;
  border-top: 1px solid #e9dfd2;
  color: #887a6c;
  font-size: 11px;
}
.post-sheet > footer div {
  display: flex;
  gap: 15px;
  margin-right: auto;
}
.post-sheet footer button.active,
.reply-card footer button.active {
  color: #7f211d;
  font-weight: 700;
}
.reply-section {
  padding: 25px 28px;
}
.section-title {
  justify-content: space-between;
}
.section-title small {
  color: #a47531;
  font:
    9px Georgia,
    serif;
  letter-spacing: 2px;
}
.section-title h2 {
  margin: 3px 0 0;
  font-size: 22px;
}
.section-title > span {
  color: #9a8c7d;
  font-size: 10px;
}
.reply-card {
  position: relative;
  margin-top: 13px;
  padding: 18px;
  border: 1px solid #e2d7c8;
  background: #fdf8ef;
}
.reply-card.child {
  margin-left: 45px;
  border-left: 3px solid #c1a36b;
}
.reply-card.accepted {
  padding-top: 37px;
  border-color: #a98542;
  background: #fff9e9;
}
.accepted-ribbon {
  position: absolute;
  left: -1px;
  top: -1px;
  padding: 6px 11px;
  background: #9a7333;
  color: #fff;
  font-size: 9px;
  letter-spacing: 1px;
}
.reply-card header {
  gap: 9px;
}
.reply-card header img {
  width: 34px;
  height: 34px;
}
.reply-card em {
  margin-left: 5px;
  color: #7b2923;
  font-size: 9px;
  font-style: normal;
}
.reply-card > p {
  white-space: pre-wrap;
  margin: 13px 0;
  color: #4e443c;
  font-size: 13px;
  line-height: 1.8;
}
.reply-card footer {
  gap: 14px;
  border-top: 1px solid #eee4d7;
  padding-top: 10px;
}
.reply-card footer button {
  color: #8d7e70;
  font-size: 10px;
}
.reply-card footer .accept {
  margin-left: auto;
  color: #356047;
}
.empty-replies {
  padding: 45px;
  text-align: center;
  color: #938578;
}
.composer {
  padding: 22px 27px;
}
.composer header {
  justify-content: space-between;
  margin-bottom: 12px;
}
.composer header div {
  display: grid;
}
.composer header small {
  color: #a47732;
  font:
    9px Georgia,
    serif;
  letter-spacing: 2px;
}
.composer header button {
  color: #8b2c27;
  font-size: 10px;
}
.composer textarea {
  min-height: 130px;
}
.composer footer {
  justify-content: flex-end;
  gap: 13px;
  margin-top: 10px;
}
.composer footer small {
  margin-right: auto;
  color: #9e9184;
}
.composer footer span {
  color: #a23b34;
  font-size: 10px;
}
.composer footer button {
  padding: 9px 16px;
  background: #7f211d;
  color: #fff;
  font-size: 11px;
}
.composer footer button:disabled {
  opacity: 0.45;
}
.page-state {
  max-width: 860px;
  margin: 50px auto;
  padding: 70px;
  border: 1px dashed #c9b9a4;
  text-align: center;
  color: #817367;
}
.page-state button {
  color: #7e2924;
}
.page-state.error {
  color: #9e3831;
}
/* #ifndef H5 */
@media (max-width: 650px) {
  .detail-page {
    padding: 13px 10px 55px;
  }
  .post-sheet {
    padding: 20px 16px;
  }
  .post-sheet h1 {
    font-size: 25px;
  }
  .post-menu {
    gap: 8px;
  }
  .post-images {
    grid-template-columns: 1fr;
  }
  .post-images img {
    height: 230px;
  }
  .reply-section {
    padding: 19px 13px;
  }
  .section-title > span {
    display: none;
  }
  .reply-card.child {
    margin-left: 22px;
  }
  .composer {
    padding: 18px 14px;
  }
}
/* #endif */
/* #ifdef H5 */
@container (max-width: 650px) {
  .detail-page {
    padding: 13px 10px 55px;
  }
  .post-sheet {
    padding: 20px 16px;
  }
  .post-sheet h1 {
    font-size: 25px;
  }
  .post-menu {
    gap: 8px;
  }
  .post-images {
    grid-template-columns: 1fr;
  }
  .post-images img {
    height: 230px;
  }
  .reply-section {
    padding: 19px 13px;
  }
  .section-title > span {
    display: none;
  }
  .reply-card.child {
    margin-left: 22px;
  }
  .composer {
    padding: 18px 14px;
  }
}
/* #endif */
</style>
