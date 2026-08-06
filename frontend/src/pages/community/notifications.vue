<template>
  <main class="inbox">
    <header>
      <div>
        <small>COMMUNITY INBOX</small>
        <h1>社区消息</h1>
        <p>回复、采纳和教师反馈都集中在这里。</p>
      </div>
      <button v-if="unread" @click="readAll">全部标为已读</button>
    </header>

    <section>
      <div v-if="loading" class="state">正在整理消息…</div>
      <div v-else-if="error" class="state error">
        {{ error }} <button @click="load">重试</button>
      </div>
      <div v-else-if="!items.length" class="state">暂时没有新消息</div>
      <article
        v-for="item in items"
        v-else
        :key="item.id"
        :class="{ unread: !item.is_read }"
        @click="open(item)"
      >
        <i>{{ mark(item.type) }}</i>
        <div>
          <header>
            <strong>{{ item.title }}</strong
            ><span>{{ relative(item.created_at) }}</span>
          </header>
          <p>{{ item.content }}</p>
          <small>{{ item.is_read ? "已读" : "未读" }}</small>
        </div>
      </article>
    </section>
  </main>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { onShow } from "@dcloudio/uni-app";
import { communityApi, type CommunityNotification } from "@/api/community";

const items = ref<CommunityNotification[]>([]);
const unread = ref(0);
const loading = ref(false);
const error = ref("");

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const data = await communityApi.notifications();
    items.value = data.items;
    unread.value = data.unread;
  } catch (cause: any) {
    error.value = cause.message || "消息加载失败";
  } finally {
    loading.value = false;
  }
}

async function readAll() {
  await communityApi.readAll();
  items.value.forEach((item) => {
    item.is_read = true;
  });
  unread.value = 0;
}

async function open(item: CommunityNotification) {
  if (!item.is_read) {
    await communityApi.readNotification(item.id);
    item.is_read = true;
    unread.value = Math.max(0, unread.value - 1);
  }
  const url =
    item.resource_type === "task"
      ? `/pages/community/task-detail?id=${item.resource_id}`
      : `/pages/community/post-detail?id=${item.resource_id}`;
  uni.navigateTo({ url });
}

function mark(type: string) {
  if (type === "accepted") return "采";
  if (type.startsWith("task")) return "评";
  return "答";
}

function relative(value: string) {
  const hours = Math.floor((Date.now() - new Date(value).getTime()) / 3600000);
  if (hours < 1) return "刚刚";
  if (hours < 24) return `${hours} 小时前`;
  return new Date(value).toLocaleDateString();
}

onShow(load);
</script>

<style scoped>
.inbox {
  min-height: 100vh;
  background: #ece5da;
}
.inbox > header {
  display: flex;
  justify-content: space-between;
  align-items: end;
  padding: 36px clamp(22px, 6vw, 65px);
  background: #431b18;
  color: #fff8e9;
}
.inbox > header small {
  color: #dbc078;
  font:
    9px Georgia,
    serif;
  letter-spacing: 2px;
}
.inbox h1 {
  margin: 5px 0;
  font-size: 34px;
}
.inbox > header p {
  margin: 0;
  color: rgba(255, 248, 233, 0.58);
  font-size: 12px;
}
.inbox > header button {
  color: #e2ca8d;
}
.inbox > section {
  max-width: 820px;
  margin: auto;
  padding: 25px;
}
.inbox article {
  display: grid;
  grid-template-columns: 48px 1fr;
  gap: 13px;
  margin-bottom: 10px;
  padding: 18px;
  border: 1px solid #d9ccbc;
  background: #f9f4eb;
  cursor: pointer;
}
.inbox article.unread {
  border-left: 4px solid #7f211d;
  background: #fffaf1;
}
.inbox article > i {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border: 2px double #a77b37;
  border-radius: 50%;
  color: #8b642e;
  font: 700 16px var(--font-display);
  font-style: normal;
}
.inbox article header {
  display: flex;
  justify-content: space-between;
}
.inbox article header span {
  color: #9b8e80;
  font-size: 9px;
}
.inbox article p {
  margin: 5px 0;
  color: #75695e;
  font-size: 12px;
}
.inbox article small {
  color: #9b6f31;
  font-size: 9px;
}
.state {
  padding: 70px;
  text-align: center;
  color: #8c7e70;
}
.state button {
  margin-left: 8px;
  color: #7f211d;
}
.state.error {
  color: #9d3932;
}
/* #ifndef H5 */
@media (max-width: 600px) {
  .inbox > header {
    padding: 27px 19px;
  }
  .inbox > section {
    padding: 13px;
  }
  .inbox article {
    grid-template-columns: 38px 1fr;
    padding: 14px;
  }
  .inbox article > i {
    width: 34px;
    height: 34px;
  }
}
/* #endif */
/* #ifdef H5 */
@container (max-width: 600px) {
  .inbox > header {
    padding: 27px 19px;
  }
  .inbox > section {
    padding: 13px;
  }
  .inbox article {
    grid-template-columns: 38px 1fr;
    padding: 14px;
  }
  .inbox article > i {
    width: 34px;
    height: 34px;
  }
}
/* #endif */
</style>
