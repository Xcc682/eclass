<template>
  <main class="moderation">
    <header>
      <div>
        <small>CONTENT REVIEW DESK</small>
        <h1>社区内容审核</h1>
        <p>举报只作为人工判断线索，系统不会自动删除内容。</p>
      </div>
      <nav>
        <button
          v-for="item in filters"
          :key="item.key"
          :class="{ active: status === item.key }"
          @click="changeStatus(item.key)"
        >
          {{ item.label }}
        </button>
      </nav>
    </header>
    <section>
      <div v-if="loading" class="state">正在读取审核队列…</div>
      <div v-else-if="error" class="state error">
        {{ error }} <button @click="load">重试</button>
      </div>
      <div v-else-if="!reports.length" class="state">
        <strong>队列已清空</strong><span>当前没有需要处理的内容</span>
      </div>
      <article v-for="item in reports" v-else :key="item.id">
        <header>
          <span>{{ item.target_type === "post" ? "帖子" : "回复" }}</span
          ><time>{{ format(item.created_at) }}</time>
        </header>
        <h2>{{ item.reason }}</h2>
        <p>{{ item.detail || "举报人未补充说明" }}</p>
        <footer>
          <button @click="view(item)">查看原内容</button>
          <template v-if="status === 'pending'">
            <button @click="decide(item, 'dismiss')">不予处理</button>
            <button class="danger" @click="decide(item, 'hide')">
              隐藏内容
            </button>
          </template>
          <button v-else @click="decide(item, 'restore')">恢复内容</button>
        </footer>
      </article>
    </section>
  </main>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { onShow } from "@dcloudio/uni-app";
import { communityApi, type ModerationReport } from "@/api/community";

const filters = [
  { key: "pending", label: "待处理" },
  { key: "resolved", label: "已处理" },
  { key: "dismissed", label: "已驳回" },
];
const status = ref("pending"),
  reports = ref<ModerationReport[]>([]),
  loading = ref(false),
  error = ref("");

async function load() {
  loading.value = true;
  error.value = "";
  try {
    reports.value = await communityApi.moderationReports(status.value);
  } catch (cause: any) {
    error.value = cause.message || "审核队列加载失败";
  } finally {
    loading.value = false;
  }
}
function changeStatus(value: string) {
  status.value = value;
  load();
}
function view(item: ModerationReport) {
  if (item.target_type === "post")
    uni.navigateTo({
      url: `/pages/community/post-detail?id=${item.target_id}`,
    });
  else uni.showToast({ title: "请从所属帖子查看该回复", icon: "none" });
}
async function decide(
  item: ModerationReport,
  action: "hide" | "restore" | "dismiss",
) {
  const labels = { hide: "隐藏内容", restore: "恢复内容", dismiss: "不予处理" };
  const result = await new Promise<any>((resolve) =>
    uni.showModal({
      title: labels[action],
      editable: true,
      placeholderText: "填写处理说明（可选）",
      success: resolve,
    }),
  );
  if (!result.confirm) return;
  try {
    await communityApi.moderate(item.id, {
      action,
      resolution: result.content || "",
    });
    reports.value = reports.value.filter((row) => row.id !== item.id);
    uni.showToast({ title: "处理结果已保存", icon: "success" });
  } catch (cause: any) {
    uni.showToast({ title: cause.message || "处理失败", icon: "none" });
  }
}
function format(value: string) {
  return new Date(value).toLocaleString();
}
onShow(load);
</script>

<style scoped>
.moderation {
  min-height: 100vh;
  background: #ebe4d9;
  color: #362d27;
}
.moderation > header {
  display: flex;
  align-items: end;
  justify-content: space-between;
  padding: 35px clamp(22px, 6vw, 68px);
  background: #302824;
  color: #fff9ec;
}
.moderation > header small {
  color: #d9bd77;
  font:
    9px Georgia,
    serif;
  letter-spacing: 2px;
}
.moderation h1 {
  margin: 6px 0;
  font-size: 34px;
}
.moderation > header p {
  margin: 0;
  color: rgba(255, 249, 236, 0.56);
  font-size: 11px;
}
.moderation nav {
  display: flex;
  gap: 5px;
}
.moderation nav button {
  padding: 8px 12px;
  border: 1px solid rgba(225, 203, 151, 0.25);
  color: #d6c8aa;
  font-size: 10px;
}
.moderation nav button.active {
  background: #d6b96e;
  color: #342821;
}
.moderation > section {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 13px;
  max-width: 980px;
  margin: auto;
  padding: 25px;
}
.moderation article {
  padding: 19px;
  border: 1px solid #d5c8b8;
  background: #fffaf1;
}
.moderation article header,
.moderation article footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.moderation article header span {
  padding: 3px 7px;
  background: #eee2cf;
  color: #815f31;
  font-size: 9px;
}
.moderation time {
  color: #95887b;
  font-size: 9px;
}
.moderation h2 {
  margin: 13px 0 5px;
  font-size: 17px;
}
.moderation article p {
  min-height: 35px;
  margin: 0;
  color: #75695d;
  font-size: 11px;
}
.moderation article footer {
  justify-content: flex-end;
  gap: 7px;
  margin-top: 17px;
  padding-top: 12px;
  border-top: 1px solid #e8dfd2;
}
.moderation article footer button {
  padding: 6px 9px;
  border: 1px solid #cfc1ae;
  color: #6f6257;
  font-size: 9px;
}
.moderation article footer .danger {
  border-color: #9a4640;
  background: #812a25;
  color: #fff;
}
.state {
  grid-column: 1/-1;
  display: grid;
  gap: 6px;
  padding: 90px;
  text-align: center;
  color: #8b7e70;
}
.state strong {
  font-size: 20px;
}
.state span {
  font-size: 11px;
}
.state button {
  color: #7e2924;
}
.state.error {
  color: #9a3731;
}
/* #ifndef H5 */
@media (max-width: 650px) {
  .moderation > header {
    display: block;
    padding: 27px 19px;
  }
  .moderation nav {
    margin-top: 18px;
  }
  .moderation > section {
    grid-template-columns: 1fr;
    padding: 13px;
  }
  .state {
    padding: 65px 20px;
  }
}
/* #endif */
/* #ifdef H5 */
@container (max-width: 650px) {
  .moderation > header {
    display: block;
    padding: 27px 19px;
  }
  .moderation nav {
    margin-top: 18px;
  }
  .moderation > section {
    grid-template-columns: 1fr;
    padding: 13px;
  }
  .state {
    padding: 65px 20px;
  }
}
/* #endif */
</style>
