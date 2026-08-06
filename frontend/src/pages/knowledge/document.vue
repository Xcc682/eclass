<template>
  <div class="document-page">
    <div v-if="loading" class="notice">正在加载原文…</div>
    <template v-else-if="doc.id">
      <header>
        <span class="category">{{ doc.category }}</span>
        <h1>{{ doc.title }}</h1>
        <div class="meta">
          <span>来源：{{ doc.source || "未注明" }}</span
          ><span>版本：v{{ doc.version }}</span
          ><span>{{ doc.view_count }} 次浏览</span>
        </div>
        <div class="actions">
          <button class="ask-current" @click="askCurrent">
            基于此资料提问
          </button>
          <button @click="toggleFavorite">
            {{ doc.is_favorite ? "★ 已收藏" : "☆ 收藏" }}
          </button>
          <button v-if="doc.file_name" @click="download">下载原文件</button>
          <button v-if="doc.source_url" @click="copySource">
            复制来源链接
          </button>
        </div>
      </header>
      <aside v-if="focusedExcerpt" class="citation-focus">
        <b>问答引用位置 · 第 {{ chunkIndex + 1 }} 段</b
        ><span>{{ focusedExcerpt }}</span>
      </aside>
      <article>
        <pre>{{ doc.content || doc.summary }}</pre>
      </article>
    </template>
    <div v-else class="notice">{{ error || "文档不存在" }}</div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { onLoad } from "@dcloudio/uni-app";
import { knowledgeApi, type KnowledgeDocument } from "@/api/knowledge";

const doc = ref<Partial<KnowledgeDocument>>({});
const loading = ref(true);
const error = ref("");
const focusedExcerpt = ref("");
const chunkIndex = ref(-1);
onLoad(async (query: any) => {
  try {
    doc.value = await knowledgeApi.getDocument(query.id);
    if (query.chunk !== undefined && query.chunk !== "") {
      chunkIndex.value = Number(query.chunk);
      focusedExcerpt.value = (
        await knowledgeApi.getDocumentChunk(query.id, chunkIndex.value)
      ).content;
    }
  } catch (event: any) {
    error.value = event.message || "加载失败";
  } finally {
    loading.value = false;
  }
});
async function toggleFavorite() {
  if (!doc.value.id) return;
  try {
    doc.value.is_favorite
      ? await knowledgeApi.unfavorite(doc.value.id)
      : await knowledgeApi.favorite(doc.value.id);
    doc.value.is_favorite = !doc.value.is_favorite;
  } catch (event: any) {
    uni.showToast({ title: event.message, icon: "none" });
  }
}
function copySource() {
  (uni as any).setClipboardData({
    data: doc.value.source_url,
    success: () => uni.showToast({ title: "来源链接已复制", icon: "success" }),
  });
}
function askCurrent() {
  if (!doc.value.id) return;
  uni.navigateTo({
    url: `/pages/knowledge/ask?documentId=${doc.value.id}&documentTitle=${encodeURIComponent(doc.value.title || "")}`,
  });
}
async function download() {
  const base = import.meta.env.VITE_API_BASE_URL || "/api/v1";
  const url = `${base}/knowledge/documents/${doc.value.id}/download`;
  const token = uni.getStorageSync("token");
  uni.downloadFile({
    url,
    header: { Authorization: `Bearer ${token}` },
    success: (result: any) =>
      uni.openDocument({
        filePath: result.tempFilePath,
        fileName: doc.value.file_name || "资料文件",
        fail: () => uni.showToast({ title: "无法打开文件", icon: "none" }),
      }),
    fail: () => uni.showToast({ title: "下载失败", icon: "none" }),
  });
}
</script>

<style scoped>
.document-page {
  min-height: 100vh;
  background: #f5f0e7;
  padding: 30rpx;
  color: #28231f;
}
.document-page header,
.document-page article {
  max-width: 760px;
  margin: 0 auto;
  background: #fffdf8;
  border: 1rpx solid #eadfce;
}
.document-page header {
  padding: 38rpx;
  border-radius: 24rpx 24rpx 0 0;
  border-bottom: 0;
}
.category {
  display: inline-block;
  background: #8d211b;
  color: #fff;
  padding: 8rpx 18rpx;
  border-radius: 999rpx;
  font-size: 20rpx;
}
.document-page h1 {
  font-family: "STSong", "SimSun", serif;
  font-size: var(--page-title-size);
  line-height: 1.45;
  margin: 22rpx 0;
}
.meta {
  display: flex;
  flex-wrap: wrap;
  gap: 22rpx;
  color: #8b7d6e;
  font-size: 21rpx;
}
.actions {
  display: flex;
  gap: 12rpx;
  margin-top: 24rpx;
}
.actions button {
  border: 1rpx solid #d9c9b2;
  background: #fff9ed;
  color: #7d251f;
  border-radius: 12rpx;
  padding: 14rpx 20rpx;
}
.document-page article {
  padding: 42rpx;
  border-radius: 0 0 24rpx 24rpx;
}
.document-page pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: "STSong", "SimSun", serif;
  font-size: 28rpx;
  line-height: 2;
  color: #3d3832;
}
.notice {
  text-align: center;
  padding: 120rpx 0;
  color: #8b7d6e;
}
.citation-focus {
  display: block;
  max-width: 760px;
  box-sizing: border-box;
  margin: 18rpx auto;
  padding: 24rpx;
  background: #fff4cf;
  border-left: 6rpx solid #d4a017;
}
.citation-focus b,
.citation-focus span {
  display: block;
}
.citation-focus span {
  margin-top: 10rpx;
  line-height: 1.8;
  color: #51483f;
}
.actions .ask-current {
  border-color: #7d251f;
  background: #7d251f;
  color: #fff;
}
</style>
