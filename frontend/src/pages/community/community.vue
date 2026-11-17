<template>
  <main class="commons">
    <header class="commons-hero">
      <div class="hero-copy">
        <small>LEARNING COMMONS · 学习协作中心</small>
        <h1>让每一次分享，<br />都能得到回应</h1>
        <p>围绕真实学习展开讨论，在同伴互助与教师反馈中继续生长。</p>
      </div>
      <div class="hero-actions">
        <button @click="go('/pages/community/notifications')">
          消息 <b v-if="unread">{{ unread > 99 ? "99+" : unread }}</b></button
        ><button class="primary" @click="go('/pages/community/create-post')">
          发布内容
        </button>
      </div>
    </header>

    <nav class="commons-tabs" aria-label="社区栏目">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        :class="{ active: activeTab === tab.key }"
        @click="switchTab(tab.key)"
      >
        <span>{{ tab.index }}</span
        >{{ tab.label }}
      </button>
    </nav>

    <div class="commons-layout">
      <section class="commons-main">
        <div v-if="activeTab !== 'tasks'" class="feed-tools">
          <label class="search"
            ><span>检索</span
            ><input
              v-model="search"
              placeholder="搜索标题或正文"
              @input="debouncedLoad"
          /></label>
          <div class="sorts">
            <button
              v-for="item in sorts"
              :key="item.key"
              :class="{ active: sortBy === item.key }"
              @click="setSort(item.key)"
            >
              {{ item.label }}
            </button>
          </div>
        </div>
        <div v-if="activeTab !== 'tasks'" class="topic-strip">
          <button :class="{ active: !topic }" @click="setTopic('')">
            全部分类</button
          ><button
            v-for="item in topics"
            :key="item.name"
            :class="{ active: topic === item.name }"
            @click="setTopic(item.name)"
          >
            {{ item.name }}<i v-if="item.followed">已关注</i>
          </button>
        </div>

        <template v-if="activeTab === 'overview'">
          <section class="overview-strip">
            <button @click="switchTab('tasks')">
              <small>待办任务</small><strong>{{ pendingTasks }}</strong
              ><span>查看学习任务 →</span>
            </button>
            <button @click="go('/pages/community/notifications')">
              <small>未读消息</small><strong>{{ unread }}</strong
              ><span>查看新的回应 →</span>
            </button>
            <button @click="go('/pages/community/my-community')">
              <small>我的社区</small><strong>{{ followedCount }}</strong
              ><span>关注的学习分类 →</span>
            </button>
          </section>
          <div class="section-heading">
            <div>
              <small>CURATED DISCUSSION</small>
              <h2>值得参与的讨论</h2>
            </div>
            <button @click="setSort('latest')">查看最新</button>
          </div>
        </template>

        <template v-if="activeTab === 'tasks'">
          <div class="section-heading">
            <div>
              <small>TEACHER ASSIGNMENTS</small>
              <h2>教师任务</h2>
            </div>
            <button
              v-if="canManage"
              @click="go('/pages/community/task-manage')"
            >
              教师工作台
            </button>
          </div>
          <div v-if="taskLoading" class="state-card">正在整理任务清单…</div>
          <div v-else-if="taskError" class="state-card error">
            <p>{{ taskError }}</p>
            <button @click="loadTasks">重新加载</button>
          </div>
          <div v-else-if="!tasks.length" class="state-card">
            暂时没有已发布任务
          </div>
          <article
            v-for="task in tasks"
            v-else
            :key="task.id"
            class="task-file"
            @click="go(`/pages/community/task-detail?id=${task.id}`)"
          >
            <div class="task-file__date">
              <strong>{{ deadlineDay(task.deadline_at) }}</strong
              ><span>{{ deadlineMonth(task.deadline_at) }}</span>
            </div>
            <div>
              <header>
                <span>{{ taskStatus(task) }}</span
                ><small>{{ task.rubric.length }} 项评价维度</small>
              </header>
              <h3>{{ task.title }}</h3>
              <p>{{ task.description || "老师暂未填写补充要求" }}</p>
              <footer>
                <b>{{
                  task.submission?.status === "reviewed"
                    ? `${task.submission.score} 分`
                    : task.submission
                      ? "继续完善"
                      : "开始任务"
                }}</b
                ><span>{{
                  task.deadline_at
                    ? `截止 ${formatDate(task.deadline_at)}`
                    : "长期有效"
                }}</span>
              </footer>
            </div>
          </article>
        </template>

        <template v-else>
          <div v-if="feedLoading" class="state-card">正在调阅社区内容…</div>
          <div v-else-if="feedError" class="state-card error">
            <p>{{ feedError }}</p>
            <button @click="loadFeed(true)">重新加载</button>
          </div>
          <div v-else-if="!posts.length" class="state-card">
            <p>
              {{ activeTab === "qa" ? "还没有人提出问题" : "这里还没有内容" }}
            </p>
            <button
              @click="
                go(
                  activeTab === 'qa'
                    ? '/pages/community/create-post?type=question'
                    : '/pages/community/create-post',
                )
              "
            >
              成为第一个发布者
            </button>
          </div>
          <article
            v-for="post in posts"
            v-else
            :key="post.id"
            class="discussion-card"
            :class="{ question: post.is_question }"
            @click="openPost(post)"
          >
            <header>
              <img :src="post.avatar_url || defaultAvatar" />
              <div>
                <strong>{{ post.author }}</strong
                ><span
                  >{{ roleLabel(post.author_role) }} ·
                  {{ relative(post.updated_at) }}</span
                >
              </div>
              <em>{{ post.category }}</em>
            </header>
            <div class="discussion-card__kind">
              <span v-if="post.pinned">置顶</span
              ><span
                v-if="post.is_question"
                :class="{ resolved: post.resolved }"
                >{{ post.resolved ? "已解决" : "等待解答" }}</span
              >
            </div>
            <h3>{{ post.title }}</h3>
            <p>{{ post.excerpt }}</p>
            <div v-if="post.attachments?.length" class="image-preview">
              <img
                v-for="file in post.attachments.slice(0, 3)"
                :key="file.id"
                :src="assetUrl(file.url)"
                loading="lazy"
              />
            </div>
            <footer>
              <div>
                <span>回应 {{ post.replies }}</span
                ><span>赞同 {{ post.likes }}</span
                ><span>阅读 {{ post.views }}</span>
              </div>
              <button
                :class="{ active: post.favorited }"
                @click.stop="toggleFavorite(post)"
              >
                {{ post.favorited ? "已收藏" : "收藏" }}
              </button>
            </footer>
          </article>
          <button
            v-if="posts.length < total && !feedLoading"
            class="load-more"
            @click="loadMore"
          >
            继续加载
          </button>
        </template>
      </section>

      <aside class="commons-aside">
        <section class="aside-card identity">
          <small>MY COMMONS</small>
          <h3>你的学习协作台</h3>
          <p>关注分类后，新讨论会出现在“我的关注”中。</p>
          <button @click="go('/pages/community/my-community')">
            查看我的发布与收藏
          </button>
        </section>
        <section class="aside-card">
          <header>
            <h3>学习分类</h3>
            <span>{{ followedCount }} 已关注</span>
          </header>
          <button
            v-for="item in topics"
            :key="item.name"
            class="topic-row"
            @click="toggleTopic(item)"
          >
            <span
              ><b>{{ item.name }}</b
              ><small>{{ item.posts }} 篇内容</small></span
            ><i :class="{ active: item.followed }">{{
              item.followed ? "已关注" : "关注"
            }}</i>
          </button>
        </section>
        <section class="aside-card rule">
          <h3>社区约定</h3>
          <p>
            分享真实收获，引用可靠资料；对观点提出质疑时，也尊重表达观点的人。
          </p>
          <button @click="go('/pages/community/create-post?type=question')">
            提出一个好问题 →
          </button>
        </section>
      </aside>
    </div>
  </main>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { onShow } from "@dcloudio/uni-app";
import {
  communityApi,
  type CommunityPost,
  type TeacherTask,
  type TopicState,
} from "@/api/community";
import { userApi } from "@/api/user";
import defaultAvatar from "@/static/images/icons/default-avatar.png";

const tabs = [
  { key: "overview", label: "社区首页", index: "01" },
  { key: "posts", label: "学习分享", index: "02" },
  { key: "qa", label: "互助问答", index: "03" },
  { key: "tasks", label: "教师任务", index: "04" },
];
const sorts = [
  { key: "latest", label: "最新" },
  { key: "hot", label: "热门" },
  { key: "unanswered", label: "待解答" },
  { key: "followed", label: "我的关注" },
];
const activeTab = ref("overview"),
  sortBy = ref("hot"),
  topic = ref(""),
  search = ref(""),
  posts = ref<CommunityPost[]>([]),
  topics = ref<TopicState[]>([]),
  tasks = ref<TeacherTask[]>([]);
const feedLoading = ref(false),
  taskLoading = ref(false),
  feedError = ref(""),
  taskError = ref(""),
  page = ref(1),
  total = ref(0),
  unread = ref(0),
  canManage = ref(false);
let timer: any;
const followedCount = computed(
  () => topics.value.filter((x) => x.followed).length,
);
const pendingTasks = computed(
  () =>
    tasks.value.filter(
      (x) => !x.submission || x.submission.status !== "reviewed",
    ).length,
);
function go(url: string) {
  uni.navigateTo({ url });
}
function openPost(post: CommunityPost) {
  go(`/pages/community/post-detail?id=${post.id}`);
}
function section() {
  return activeTab.value === "posts"
    ? "post"
    : activeTab.value === "qa"
      ? "question"
      : "all";
}
async function loadFeed(reset = true) {
  if (reset) {
    page.value = 1;
    posts.value = [];
  }
  feedLoading.value = true;
  feedError.value = "";
  try {
    const data = await communityApi.feed({
      section: section(),
      sort_by: sortBy.value,
      topic: topic.value,
      q: search.value.trim(),
      page: page.value,
      page_size: 12,
    });
    posts.value = reset ? data.items : [...posts.value, ...data.items];
    total.value = data.pagination.total;
    unread.value = data.summary?.unread_notifications || unread.value;
  } catch (e: any) {
    feedError.value = e.message || "社区内容加载失败";
  } finally {
    feedLoading.value = false;
  }
}
async function loadTasks() {
  taskLoading.value = true;
  taskError.value = "";
  try {
    tasks.value = await communityApi.getTasks();
  } catch (e: any) {
    taskError.value = e.message || "教师任务加载失败";
  } finally {
    taskLoading.value = false;
  }
}
async function loadTopics() {
  try {
    topics.value = await communityApi.topics();
  } catch {
    topics.value = [];
  }
}
async function loadProfile() {
  try {
    const user = await userApi.getProfile();
    canManage.value = ["teacher", "admin"].includes(user.role);
  } catch {}
}
async function refresh() {
  await Promise.allSettled([
    loadFeed(true),
    loadTasks(),
    loadTopics(),
    loadProfile(),
  ]);
}
function switchTab(value: string) {
  activeTab.value = value;
  if (value !== "tasks") {
    sortBy.value = value === "overview" ? "hot" : "latest";
    loadFeed(true);
  } else loadTasks();
}
function setSort(value: string) {
  sortBy.value = value;
  loadFeed(true);
}
function setTopic(value: string) {
  topic.value = value;
  loadFeed(true);
}
function debouncedLoad() {
  clearTimeout(timer);
  timer = setTimeout(() => loadFeed(true), 300);
}
function loadMore() {
  page.value++;
  loadFeed(false);
}
async function toggleFavorite(post: CommunityPost) {
  try {
    const data = post.favorited
      ? await communityApi.unfavorite(post.id)
      : await communityApi.favorite(post.id);
    post.favorited = data.favorited;
    post.favorites = data.favorites;
  } catch {}
}
async function toggleTopic(item: TopicState) {
  try {
    item.followed
      ? await communityApi.unfollowTopic(item.name)
      : await communityApi.followTopic(item.name);
    item.followed = !item.followed;
  } catch {}
}
function assetUrl(url: string) {
  const base = import.meta.env.VITE_API_BASE_URL || "/api/v1";
  return url.startsWith("/api/v1")
    ? `${base.replace(/\/api\/v1$/, "")}${url}`
    : url;
}
function roleLabel(role: string) {
  return role === "admin"
    ? "社区管理员"
    : role === "teacher"
      ? "指导教师"
      : "学习伙伴";
}
function relative(value: string) {
  const diff = Date.now() - new Date(value).getTime(),
    hour = Math.floor(diff / 3600000);
  return hour < 1
    ? "刚刚"
    : hour < 24
      ? `${hour} 小时前`
      : hour < 168
        ? `${Math.floor(hour / 24)} 天前`
        : new Date(value).toLocaleDateString();
}
function formatDate(value: string) {
  return new Date(value).toLocaleDateString();
}
function deadlineDay(value?: string | null) {
  return value ? String(new Date(value).getDate()).padStart(2, "0") : "∞";
}
function deadlineMonth(value?: string | null) {
  return value ? `${new Date(value).getMonth() + 1}月` : "长期";
}
function taskStatus(task: TeacherTask) {
  return task.submission?.status === "reviewed"
    ? "已批阅"
    : task.submission?.status === "submitted"
      ? "已提交"
      : task.submission?.status === "draft"
        ? "草稿中"
        : task.status === "expired"
          ? "已截止"
          : "进行中";
}
onShow(refresh);
</script>

<style scoped>
.commons {
  min-height: 100vh;
  background: #eee8de;
  color: #302720;
}
.commons-hero {
  position: relative;
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 40px;
  padding: 42px clamp(24px, 5vw, 64px);
  overflow: hidden;
  background: #431b18;
  color: #fff8e9;
}
.commons-hero:after {
  content: "COMMONS";
  position: absolute;
  right: -24px;
  bottom: -46px;
  font:
    italic 112px Georgia,
    serif;
  color: rgba(255, 255, 255, 0.035);
}
.hero-copy,
.hero-actions {
  position: relative;
  z-index: 1;
}
.hero-copy small {
  color: #dfc174;
  font:
    11px Georgia,
    serif;
  letter-spacing: 3px;
}
.hero-copy h1 {
  margin: 13px 0 10px;
  font: 700 var(--page-title-size)/1.15 var(--font-display);
}
.hero-copy p {
  max-width: 540px;
  margin: 0;
  color: rgba(255, 248, 233, 0.62);
  font-size: 14px;
}
.hero-actions {
  display: flex;
  gap: 10px;
}
.hero-actions button {
  position: relative;
  padding: 11px 16px;
  border: 1px solid rgba(229, 202, 135, 0.42);
  color: #e8d39d;
}
.hero-actions button.primary {
  background: #dfc174;
  color: #3d1715;
  font-weight: 700;
}
.hero-actions b {
  position: absolute;
  right: -6px;
  top: -8px;
  min-width: 18px;
  height: 18px;
  border-radius: 9px;
  background: #fff;
  color: #7f211d;
  font: 10px/18px sans-serif;
}
.commons-tabs {
  display: flex;
  padding: 0 clamp(20px, 4vw, 48px);
  border-bottom: 1px solid #d3c6b5;
  background: #faf6ee;
  overflow: auto;
}
.commons-tabs button {
  flex: 1;
  min-width: 110px;
  padding: 17px 10px 15px;
  border-bottom: 3px solid transparent;
  color: #776a5d;
}
.commons-tabs button span {
  margin-right: 8px;
  color: #ae8748;
  font:
    10px Georgia,
    serif;
}
.commons-tabs button.active {
  border-color: #7f211d;
  color: #411d1a;
  font-weight: 700;
}
.commons-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 285px;
  gap: 26px;
  max-width: 1080px;
  width: 100%;
  box-sizing: border-box;
  margin: auto;
  padding: 28px;
}
.commons-feed { min-width: 0; }
.feed-tools {
  display: flex;
  align-items: center;
  gap: 14px;
}
.search {
  display: flex;
  align-items: center;
  flex: 1;
  border-bottom: 1px solid #b9aa97;
}
.search span {
  flex: none;
  margin-right: 10px;
  color: #8a2a25;
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}
.search input {
  flex: 1;
  min-width: 0;
  width: auto;
  height: 42px;
  border: 0;
  background: transparent;
  box-shadow: none;
}
.sorts {
  display: flex;
  gap: 4px;
}
.sorts button,
.topic-strip button {
  padding: 8px 10px;
  color: #796b5e;
  font-size: 12px;
}
.sorts button.active {
  background: #3b332c;
  color: #fff;
}
.topic-strip {
  display: flex;
  gap: 5px;
  margin: 15px 0 21px;
  overflow: auto;
}
.topic-strip button {
  flex: none;
  border: 1px solid #d8ccbc;
  background: #f9f4ec;
}
.topic-strip button.active {
  border-color: #7f211d;
  color: #7f211d;
}
.topic-strip i {
  margin-left: 5px;
  color: #aa7d35;
  font-size: 9px;
  font-style: normal;
}
.overview-strip {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-bottom: 27px;
}
.overview-strip button {
  display: grid;
  gap: 2px;
  padding: 17px;
  border: 1px solid #d7cabb;
  background: #fffaf1;
  text-align: left;
}
.overview-strip small {
  color: #9b7c52;
}
.overview-strip strong {
  font:
    700 30px Georgia,
    serif;
  color: #762722;
}
.overview-strip span {
  font-size: 11px;
  color: #7c6d60;
}
.section-heading {
  display: flex;
  align-items: end;
  justify-content: space-between;
  margin: 12px 0 17px;
}
.section-heading small {
  color: #a27632;
  font:
    9px Georgia,
    serif;
  letter-spacing: 2px;
}
.section-heading h2 {
  margin: 2px 0 0;
  font-size: 23px;
}
.section-heading > button {
  color: #7c2924;
  font-size: 12px;
}
.discussion-card {
  position: relative;
  margin-bottom: 15px;
  padding: 22px 23px 17px;
  border: 1px solid #d8cdbf;
  background: #fffaf2;
  box-shadow: 0 8px 25px rgba(55, 39, 25, 0.045);
  cursor: pointer;
}
.discussion-card.question {
  border-left: 4px solid #a97a34;
}
.discussion-card > header {
  display: flex;
  align-items: center;
  gap: 10px;
}
.discussion-card header img {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  object-fit: cover;
}
.discussion-card header div {
  display: grid;
  flex: 1;
}
.discussion-card header strong {
  font-size: 13px;
}
.discussion-card header span {
  font-size: 10px;
  color: #9a8e81;
}
.discussion-card header em {
  padding: 4px 8px;
  background: #f2e8d9;
  color: #8b612d;
  font-size: 10px;
  font-style: normal;
}
.discussion-card__kind {
  display: flex;
  gap: 5px;
  margin-top: 14px;
}
.discussion-card__kind span {
  padding: 3px 7px;
  background: #fff0dd;
  color: #9b5d15;
  font-size: 9px;
}
.discussion-card__kind span.resolved {
  background: #e8f1e8;
  color: #3d6c4d;
}
.discussion-card h3 {
  margin: 8px 0 7px;
  font: 700 19px/1.4 var(--font-display);
}
.discussion-card > p {
  display: -webkit-box;
  overflow: hidden;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  margin: 0;
  color: #776b60;
  font-size: 13px;
  line-height: 1.7;
}
.discussion-card > footer {
  display: flex;
  justify-content: space-between;
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid #eee5d9;
}
.discussion-card footer div {
  display: flex;
  gap: 17px;
  color: #95887b;
  font-size: 10px;
}
.discussion-card footer button {
  color: #8d7e70;
  font-size: 10px;
}
.discussion-card footer button.active {
  color: #7f211d;
  font-weight: 700;
}
.image-preview {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 5px;
  margin-top: 12px;
}
.image-preview img {
  width: 100%;
  height: 110px;
  object-fit: cover;
}
.load-more {
  width: 100%;
  padding: 14px;
  border: 1px solid #cdbfac;
  color: #7a2b25;
}
.state-card {
  display: grid;
  place-items: center;
  min-height: 180px;
  padding: 24px;
  border: 1px dashed #cdbda8;
  background: rgba(255, 250, 241, 0.65);
  color: #817469;
}
.state-card.error {
  color: #983b34;
}
.state-card button {
  margin-top: 9px;
  color: #7b2823;
}
.task-file {
  display: grid;
  grid-template-columns: 64px 1fr;
  margin-bottom: 14px;
  border: 1px solid #d6c9b8;
  background: #fffaf1;
  cursor: pointer;
}
.task-file__date {
  display: grid;
  place-items: center;
  align-content: center;
  border-right: 1px solid #e2d7c8;
  color: #772822;
}
.task-file__date strong {
  font:
    700 27px Georgia,
    serif;
}
.task-file__date span {
  font-size: 10px;
}
.task-file > div:last-child {
  padding: 18px;
}
.task-file header,
.task-file footer {
  display: flex;
  justify-content: space-between;
}
.task-file header span {
  color: #9a6e2c;
  font-size: 10px;
}
.task-file header small {
  color: #988b7e;
}
.task-file h3 {
  margin: 7px 0 5px;
  font-size: 18px;
}
.task-file p {
  margin: 0;
  color: #7b6e62;
  font-size: 12px;
}
.task-file footer {
  margin-top: 13px;
  padding-top: 11px;
  border-top: 1px solid #eee4d7;
  font-size: 10px;
}
.task-file footer b {
  color: #7a2924;
}
.commons-aside {
  display: grid;
  align-content: start;
  gap: 15px;
}
.aside-card {
  padding: 19px;
  border: 1px solid #d4c7b6;
  background: #f9f4eb;
}
.aside-card > small {
  color: #a47d3e;
  font:
    9px Georgia,
    serif;
  letter-spacing: 2px;
}
.aside-card h3 {
  margin: 4px 0 8px;
  font-size: 17px;
}
.aside-card p {
  margin: 0;
  color: #7b6e61;
  font-size: 12px;
}
.aside-card > button {
  margin-top: 14px;
  color: #792923;
  font-size: 11px;
}
.aside-card > header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 9px;
}
.aside-card > header h3 {
  margin: 0;
}
.aside-card > header span {
  color: #9c8d7e;
  font-size: 9px;
}
.topic-row {
  display: flex;
  justify-content: space-between;
  width: 100%;
  padding: 11px 0;
  border-top: 1px solid #e8ded0;
  text-align: left;
}
.topic-row span {
  display: grid;
}
.topic-row b {
  font-size: 12px;
}
.topic-row small {
  color: #9c8d7f;
  font-size: 9px;
}
.topic-row i {
  align-self: center;
  padding: 4px 7px;
  border: 1px solid #cabca9;
  color: #847566;
  font-size: 9px;
  font-style: normal;
}
.topic-row i.active {
  border-color: #345d49;
  color: #345d49;
}
.identity {
  border-top: 4px solid #7f211d;
}
.rule {
  border-top: 4px solid #b28a47;
}
/* #ifndef H5 */
@media (max-width: 760px) {
  .commons-hero {
    padding: 28px 20px;
  }
  .hero-copy h1 {
    font-size: 31px;
  }
  .hero-copy p {
    font-size: 12px;
  }
  .hero-actions {
    flex-direction: column;
  }
  .commons-layout {
    grid-template-columns: 1fr;
    padding: 17px 12px;
  }
  .commons-aside {
    display: none;
  }
  .feed-tools {
    display: block;
  }
  .sorts {
    margin-top: 10px;
    overflow: auto;
  }
  .overview-strip {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    overflow: visible;
  }
  .overview-strip button {
    min-width: 0;
    padding: 13px 11px;
  }
  .overview-strip span {
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
  }
  .discussion-card {
    padding: 18px 16px;
  }
  .image-preview img {
    height: 86px;
  }
  .commons-tabs {
    padding: 0;
  }
  .commons-tabs button {
    min-width: 96px;
    font-size: 12px;
  }
  .commons-tabs button span {
    display: none;
  }
}
/* #endif */
/* #ifdef H5 */
@container (max-width: 760px) {
  .commons-hero {
    padding: 28px 20px;
  }
  .hero-copy h1 {
    font-size: 31px;
  }
  .hero-copy p {
    font-size: 12px;
  }
  .hero-actions {
    flex-direction: column;
  }
  .commons-layout {
    grid-template-columns: 1fr;
    padding: 17px 12px;
  }
  .commons-aside {
    display: none;
  }
  .feed-tools {
    display: block;
  }
  .sorts {
    margin-top: 10px;
    overflow: auto;
  }
  .overview-strip {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    overflow: visible;
  }
  .overview-strip button {
    min-width: 0;
    padding: 13px 11px;
  }
  .overview-strip span {
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
  }
  .discussion-card {
    padding: 18px 16px;
  }
  .image-preview img {
    height: 86px;
  }
  .commons-tabs {
    padding: 0;
  }
  .commons-tabs button {
    min-width: 96px;
    font-size: 12px;
  }
  .commons-tabs button span {
    display: none;
  }
}
/* #endif */
/* #ifndef H5 */
@media (max-width: 430px) {
  .hero-copy h1 br {
    display: none;
  }
  .commons-hero {
    display: block;
  }
  .hero-actions {
    flex-direction: row;
    margin-top: 20px;
  }
}
/* #endif */
/* #ifdef H5 */
@container (max-width: 430px) {
  .hero-copy h1 br {
    display: none;
  }
  .commons-hero {
    display: block;
  }
  .hero-actions {
    flex-direction: row;
    margin-top: 20px;
  }
}
/* #endif */
</style>
