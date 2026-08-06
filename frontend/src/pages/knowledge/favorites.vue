<template>
  <div class="collection-page">
    <header>
      <h1>我的资料夹</h1>
      <div>
        <button
          :class="{ active: tab === 'favorites' }"
          @click="switchTab('favorites')"
        >
          收藏</button
        ><button
          :class="{ active: tab === 'recent' }"
          @click="switchTab('recent')"
        >
          最近浏览
        </button>
      </div>
    </header>
    <div v-if="loading" class="empty">加载中…</div>
    <div v-else-if="!documents.length" class="empty">这里还没有资料</div>
    <article v-for="doc in documents" :key="doc.id" @click="open(doc.id)">
      <span>{{ doc.category }}</span>
      <h2>{{ doc.title }}</h2>
      <p>{{ doc.summary }}</p>
      <small>{{
        tab === "recent" && doc.viewed_at
          ? `浏览于 ${format(doc.viewed_at)}`
          : doc.source
      }}</small>
    </article>
  </div>
</template>
<script setup lang="ts">
import { onMounted, ref } from "vue";
import { knowledgeApi, type KnowledgeDocument } from "@/api/knowledge";
const tab = ref<"favorites" | "recent">("favorites");
const documents = ref<KnowledgeDocument[]>([]);
const loading = ref(false);
async function load() {
  loading.value = true;
  try {
    documents.value =
      tab.value === "favorites"
        ? await knowledgeApi.favorites()
        : await knowledgeApi.recent();
  } finally {
    loading.value = false;
  }
}
function switchTab(value: "favorites" | "recent") {
  tab.value = value;
  load();
}
function open(id: string) {
  uni.navigateTo({ url: `/pages/knowledge/document?id=${id}` });
}
function format(value: string) {
  return new Date(value).toLocaleString();
}
onMounted(load);
</script>
<style scoped>
.collection-page {
  min-height: 100vh;
  background: #f5f0e7;
  padding: 30rpx;
}
.collection-page header {
  max-width: 840px;
  margin: auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.collection-page h1 {
  font-family: "STKaiti", "KaiTi", serif;
  font-size: var(--page-title-size);
}
.collection-page header button {
  border: 0;
  background: transparent;
  padding: 15rpx 22rpx;
  color: #786b5d;
}
.collection-page header .active {
  background: #8d211b;
  color: #fff;
  border-radius: 999rpx;
}
.collection-page article {
  max-width: 780px;
  margin: 18rpx auto;
  padding: 28rpx;
  background: #fffdf8;
  border: 1rpx solid #e6dac7;
  border-radius: 18rpx;
}
.collection-page article span {
  color: #8d211b;
  font-size: 20rpx;
}
.collection-page h2 {
  font-family: "STSong", "SimSun", serif;
  font-size: 30rpx;
}
.collection-page p {
  font-size: 22rpx;
  color: #6f655b;
  line-height: 1.6;
}
.collection-page small {
  color: #9d8f80;
}
.empty {
  text-align: center;
  padding: 120rpx;
  color: #8f8274;
}
</style>
