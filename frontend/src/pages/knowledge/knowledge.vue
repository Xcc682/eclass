<template>
  <div class="knowledge-page">
    <section class="hero">
      <div>
        <span class="eyebrow">权威资料 · 有据可查</span>
        <h1>思政知识库</h1>
        <p>从可信资料中检索答案，每条回答都能回到原文。</p>
      </div>
      <button class="hero__ask" @click="go('/pages/knowledge/ask')">
        智能问答 →
      </button>
    </section>

    <div class="quick-actions">
      <button @click="scrollToLibrary">资料库</button>
      <button @click="go('/pages/knowledge/template')">写作模板</button>
      <button @click="go('/pages/knowledge/favorites')">收藏与最近</button>
      <button
        v-if="canManage"
        class="manager"
        @click="go('/pages/knowledge/manage')"
      >
        资料管理
      </button>
    </div>

    <section class="library-card">
      <div class="search-row">
        <input
          v-model="searchText"
          placeholder="搜索标题、内容或来源"
          @confirm="loadDocuments(true)"
        />
        <button @click="loadDocuments(true)">搜索</button>
      </div>
      <div class="filters">
        <span
          v-for="item in categories"
          :key="item"
          :class="{ active: category === item }"
          @click="selectCategory(item)"
          >{{ item || "全部" }}</span
        >
      </div>

      <div v-if="loading && !documents.length" class="state">正在整理资料…</div>
      <div v-else-if="error && !documents.length" class="state state--error">
        {{ error }} <button @click="loadDocuments(true)">重试</button>
      </div>
      <div v-else-if="!loading && !error && !documents.length" class="state">
        暂无符合条件的资料
      </div>

      <div v-if="documents.length" class="document-list">
        <article
          v-for="doc in documents"
          :key="doc.id"
          @click="openDocument(doc.id)"
        >
          <div class="document-list__top">
            <span class="badge">{{ doc.category || "未分类" }}</span
            ><span>v{{ doc.version }}</span>
          </div>
          <h2>{{ doc.title }}</h2>
          <p>{{ doc.summary || "暂无摘要" }}</p>
          <footer>
            <span>{{ doc.source || "来源待补充" }}</span
            ><span>{{ doc.view_count || 0 }} 次浏览</span>
          </footer>
        </article>
      </div>
      <div v-if="loadingMore" class="state" style="padding: 20rpx">
        加载更多数据…
      </div>
      <button
        v-if="documents.length < totalCount && !loadingMore"
        class="load-more"
        @click="loadMore"
      >
        加载更多
      </button>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { knowledgeApi, type KnowledgeDocument } from "@/api/knowledge";
import { userApi } from "@/api/user";

const documents = ref<KnowledgeDocument[]>([]);
const searchText = ref("");
const category = ref("");
const categories = ["", "党史", "时政", "党章党规", "思政课程", "重要讲话"];
const loading = ref(false);
const loadingMore = ref(false);
const error = ref("");
const page = ref(1);
const pageSize = 12;
const totalCount = ref(0);
const canManage = ref(false);

async function loadDocuments(reset = false) {
  if (reset) page.value = 1;
  loading.value = true;
  error.value = "";
  try {
    const body = await knowledgeApi.getDocumentPage({
      page: page.value,
      page_size: pageSize,
      category: category.value || undefined,
      q: searchText.value.trim() || undefined,
    });
    documents.value = reset ? body.data : [...documents.value, ...body.data];
    totalCount.value = body.pagination.total;
  } catch (event: any) {
    error.value = event.message || "资料加载失败";
  } finally {
    loading.value = false;
  }
}

function selectCategory(value: string) {
  category.value = value;
  loadDocuments(true);
}
function loadMore() {
  page.value += 1;
  loadingMore.value = true;
  loadDocuments(false).finally(() => {
    loadingMore.value = false;
  });
}
function openDocument(id: string) {
  uni.navigateTo({ url: `/pages/knowledge/document?id=${id}` });
}
function go(url: string) {
  uni.navigateTo({ url });
}
function scrollToLibrary() {
  uni.pageScrollTo({ selector: ".library-card", duration: 280 });
}

onMounted(async () => {
  await loadDocuments(true);
  try {
    const profile = await userApi.getProfile();
    canManage.value = ["teacher", "admin"].includes(profile.role);
  } catch {}
});
</script>

<style scoped>
.knowledge-page {
  min-height: 100vh;
  box-sizing: border-box;
  background: #f7f2e8;
  padding: 24rpx 28rpx 80rpx;
  color: #27231e;
}
.hero {
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24rpx;
  padding: 40rpx 34rpx;
  background: linear-gradient(135deg, #821a16, #c84432);
  border-radius: 28rpx;
  color: #fff;
  box-shadow: 0 18rpx 40rpx rgba(124, 25, 20, 0.22);
}
.hero:after {
  content: "知";
  position: absolute;
  right: 20rpx;
  top: -58rpx;
  font-size: 220rpx;
  font-family: serif;
  color: rgba(255, 255, 255, 0.08);
}
.eyebrow {
  font-size: 20rpx;
  letter-spacing: 4rpx;
  color: #f8d99b;
}
.hero h1 {
  font-family: "STKaiti", "KaiTi", serif;
  font-size: var(--page-title-size);
  margin: 12rpx 0;
}
.hero p {
  font-size: 23rpx;
  opacity: 0.86;
  margin: 0;
  line-height: 1.6;
}
.hero__ask {
  position: relative;
  z-index: 1;
  flex: none;
  border: 0;
  border-radius: 999rpx;
  padding: 18rpx 24rpx;
  background: #f6d891;
  color: #6d1714;
  font-weight: 700;
}
.quick-actions {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12rpx;
  margin: 22rpx 0;
}
.quick-actions button {
  border: 1rpx solid #eadfcd;
  background: #fffaf1;
  color: #584d41;
  border-radius: 4px;
  padding: 20rpx 8rpx;
  font-size: 22rpx;
}
.quick-actions .manager {
  background: #2d4938;
  color: #fff;
}
.library-card {
  background: #fffdf8;
  border: 1rpx solid #eadfcd;
  border-radius: 4px;
  padding: 24rpx;
}
.search-row {
  display: flex;
  gap: 12rpx;
}
.search-row input {
  flex: 1;
  background: #f5efe4;
  border-radius: 14rpx;
  padding: 18rpx 22rpx;
  font-size: 24rpx;
}
.search-row button,
.state button {
  border: 0;
  background: #8f201b;
  color: #fff;
  border-radius: 14rpx;
  padding: 0 26rpx;
}
.filters {
  display: flex;
  gap: 12rpx;
  overflow: auto;
  padding: 22rpx 0;
}
.filters span {
  flex: none;
  padding: 10rpx 20rpx;
  border-radius: 999rpx;
  background: #f4ede1;
  color: #746557;
  font-size: 21rpx;
}
.filters .active {
  background: #8f201b;
  color: #fff;
}
.document-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18rpx;
}
.document-list article {
  padding: 24rpx;
  border: 1rpx solid #eee3d2;
  border-radius: 18rpx;
  background: linear-gradient(180deg, #fff, #fffaf2);
}
.document-list__top,
.document-list footer {
  display: flex;
  justify-content: space-between;
  color: #9b8c7b;
  font-size: 19rpx;
}
.badge {
  color: #8f201b;
}
.document-list h2 {
  font-family: "STSong", "SimSun", serif;
  font-size: 28rpx;
  line-height: 1.45;
  margin: 18rpx 0 10rpx;
}
.document-list p {
  font-size: 22rpx;
  color: #746b62;
  line-height: 1.65;
  min-height: 70rpx;
}
.document-list footer {
  border-top: 1rpx solid #eee3d2;
  padding-top: 15rpx;
}
.state {
  text-align: center;
  padding: 80rpx 20rpx;
  color: #8d8174;
}
.state--error {
  color: #9b312b;
}
.load-more {
  display: block;
  margin: 24rpx auto 0;
  border: 0;
  background: transparent;
  color: #8f201b;
}
/* #ifndef H5 */
@media (max-width: 520px) {
  .quick-actions {
    grid-template-columns: repeat(2, 1fr);
  }
  .document-list {
    grid-template-columns: 1fr;
  }
  .hero {
    align-items: flex-start;
    flex-direction: column;
  }
}
/* #endif */
/* #ifdef H5 */
@container (max-width: 520px) {
  .quick-actions {
    grid-template-columns: repeat(2, 1fr);
  }
  .document-list {
    grid-template-columns: 1fr;
  }
  .hero {
    align-items: flex-start;
    flex-direction: column;
  }
}
/* #endif */
/* Archive design system overrides */
.knowledge-page {
  background: var(--color-bg);
  padding: 0 28rpx 80rpx;
}
.hero {
  margin: 0 -28rpx;
  padding: 52rpx 34rpx 42rpx;
  border-radius: 0;
  background: #431a18;
  box-shadow: none;
}
.hero:after {
  color: rgba(231, 201, 129, 0.08);
}
.hero__ask {
  border-radius: 2rpx;
  background: #e7c981;
}
.quick-actions {
  margin: 22rpx 0;
}
.quick-actions button {
  border-radius: 2rpx;
  background: #fffaf0;
}
.library-card {
  border-radius: 2rpx;
  background: #fffaf0;
  box-shadow: 0 7rpx 23rpx rgba(47, 32, 23, 0.05);
}
.search-row input,
.search-row button,
.state button {
  border-radius: 2rpx;
}
.filters span {
  border-radius: 2rpx;
}
.document-list article {
  border-radius: 2rpx;
  background: var(--color-card);
  box-shadow: 0 5rpx 18rpx rgba(48, 32, 22, 0.04);
}
.document-list h2 {
  font-family: var(--font-display);
}
</style>
