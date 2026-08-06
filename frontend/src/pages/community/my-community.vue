<template>
  <main class="my-space">
    <header>
      <small>MY LEARNING COMMONS</small>
      <h1>我的社区</h1>
      <p>管理发布、收藏、参与过的讨论和关注分类。</p>
    </header>

    <nav>
      <button
        v-for="item in tabs"
        :key="item.key"
        :class="{ active: tab === item.key }"
        @click="tab = item.key"
      >
        {{ item.label }} <span>{{ count(item.key) }}</span>
      </button>
    </nav>

    <section v-if="loading" class="state">正在整理你的社区记录…</section>
    <section v-else-if="error" class="state error">
      {{ error }} <button @click="load">重试</button>
    </section>
    <section v-else-if="tab === 'topics'" class="topic-list">
      <button v-for="topic in topics" :key="topic.name" @click="toggle(topic)">
        <div>
          <strong>{{ topic.name }}</strong
          ><span>{{ topic.posts }} 篇内容</span>
        </div>
        <i :class="{ active: topic.followed }">{{
          topic.followed ? "已关注" : "关注"
        }}</i>
      </button>
    </section>
    <section v-else class="post-list">
      <div v-if="!visible.length" class="state">这里暂时没有记录</div>
      <article v-for="post in visible" :key="post.id" @click="open(post.id)">
        <div>
          <small
            >{{ post.category }} ·
            {{ post.is_question ? "互助问答" : "学习分享" }}</small
          >
          <h2>{{ post.title }}</h2>
          <p>{{ post.excerpt }}</p>
        </div>
        <aside>
          <strong>{{ post.replies }}</strong
          ><span>回应</span>
        </aside>
      </article>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { onShow } from "@dcloudio/uni-app";
import {
  communityApi,
  type CommunityPost,
  type TopicState,
} from "@/api/community";

const tabs = [
  { key: "posts", label: "我的发布" },
  { key: "favorites", label: "我的收藏" },
  { key: "replied", label: "参与讨论" },
  { key: "topics", label: "关注分类" },
];
const tab = ref("posts");
const data = ref<{
  posts: CommunityPost[];
  favorites: CommunityPost[];
  replied: CommunityPost[];
  followed_topics: string[];
}>({
  posts: [],
  favorites: [],
  replied: [],
  followed_topics: [],
});
const topics = ref<TopicState[]>([]);
const loading = ref(false);
const error = ref("");
const visible = computed(() => (data.value as any)[tab.value] || []);

function count(key: string) {
  return key === "topics"
    ? topics.value.filter((item) => item.followed).length
    : (data.value as any)[key]?.length || 0;
}

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const result = await Promise.all([
      communityApi.myCommunity(),
      communityApi.topics(),
    ]);
    data.value = result[0];
    topics.value = result[1];
  } catch (cause: any) {
    error.value = cause.message || "记录加载失败";
  } finally {
    loading.value = false;
  }
}

async function toggle(topic: TopicState) {
  if (topic.followed) await communityApi.unfollowTopic(topic.name);
  else await communityApi.followTopic(topic.name);
  topic.followed = !topic.followed;
}

function open(id: string) {
  uni.navigateTo({ url: `/pages/community/post-detail?id=${id}` });
}

onShow(load);
</script>

<style scoped>
.my-space {
  min-height: 100vh;
  background: #ece5da;
}
.my-space > header {
  padding: 35px clamp(22px, 6vw, 64px);
  background: #3a2420;
  color: #fff8e9;
}
.my-space > header small {
  color: #d8b96f;
  font:
    9px Georgia,
    serif;
  letter-spacing: 2px;
}
.my-space h1 {
  margin: 6px 0;
  font-size: 34px;
}
.my-space > header p {
  margin: 0;
  color: rgba(255, 248, 233, 0.58);
  font-size: 12px;
}
.my-space > nav {
  display: flex;
  max-width: 880px;
  margin: 22px auto 0;
  border-bottom: 1px solid #cdbfab;
}
.my-space > nav button {
  flex: 1;
  padding: 12px;
  color: #7e7062;
}
.my-space > nav button.active {
  border-bottom: 3px solid #7f211d;
  color: #7f211d;
  font-weight: 700;
}
.my-space > nav span {
  color: #ac7b35;
  font:
    10px Georgia,
    serif;
}
.my-space > section {
  max-width: 880px;
  margin: auto;
  padding: 19px;
  box-sizing: border-box;
}
.post-list article {
  display: grid;
  grid-template-columns: 1fr 60px;
  margin-bottom: 11px;
  padding: 19px;
  border: 1px solid #d7caba;
  background: #fffaf1;
  cursor: pointer;
}
.post-list small {
  color: #a17431;
  font-size: 9px;
}
.post-list h2 {
  margin: 5px 0;
  font-size: 19px;
}
.post-list p {
  margin: 0;
  color: #7d7063;
  font-size: 11px;
}
.post-list aside {
  display: grid;
  place-items: center;
  align-content: center;
  border-left: 1px solid #e3d8c9;
}
.post-list aside strong {
  color: #7e2924;
  font:
    700 23px Georgia,
    serif;
}
.post-list aside span {
  font-size: 9px;
  color: #958779;
}
.topic-list {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}
.topic-list > button {
  display: flex;
  justify-content: space-between;
  padding: 18px;
  border: 1px solid #d5c8b7;
  background: #fffaf1;
  text-align: left;
}
.topic-list > button div {
  display: grid;
}
.topic-list strong {
  font-size: 14px;
}
.topic-list span {
  color: #958779;
  font-size: 9px;
}
.topic-list i {
  align-self: center;
  padding: 5px 9px;
  border: 1px solid #cbbda9;
  color: #847568;
  font-size: 9px;
  font-style: normal;
}
.topic-list i.active {
  border-color: #356148;
  color: #356148;
}
.state {
  padding: 65px !important;
  text-align: center;
  color: #8a7b6e;
}
.state button {
  color: #7e2924;
}
/* #ifndef H5 */
@media (max-width: 600px) {
  .my-space > header {
    padding: 26px 19px;
  }
  .my-space > nav {
    overflow: auto;
  }
  .my-space > nav button {
    min-width: 92px;
    font-size: 11px;
  }
  .topic-list {
    grid-template-columns: 1fr;
  }
  .my-space > section {
    padding: 12px;
  }
}
/* #endif */
/* #ifdef H5 */
@container (max-width: 600px) {
  .my-space > header {
    padding: 26px 19px;
  }
  .my-space > nav {
    overflow: auto;
  }
  .my-space > nav button {
    min-width: 92px;
    font-size: 11px;
  }
  .topic-list {
    grid-template-columns: 1fr;
  }
  .my-space > section {
    padding: 12px;
  }
}
/* #endif */
</style>
