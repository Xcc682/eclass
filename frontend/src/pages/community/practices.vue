<template>
  <view class="training-archive">
    <view class="archive-cover">
      <view class="archive-cover__folio"
        ><text>TRAINING ARCHIVE · 2026</text><text>个人训练卷宗</text></view
      >
      <view class="archive-cover__title">
        <view
          ><text class="archive-cover__eyebrow">四类实践 · 一处续接</text>
          <h1>我的训练</h1>
          <p>继续未完成的训练，回看已经形成的成绩与报告。</p></view
        >
        <view class="archive-cover__seal"
          ><strong>{{ archive.summary.completed }}</strong
          ><text>有效完成</text></view
        >
      </view>
      <view class="archive-stats">
        <view
          ><strong>{{ archive.summary.in_progress }}</strong
          ><text>进行中</text></view
        >
        <view
          ><strong>{{ archive.summary.awaiting_report }}</strong
          ><text>待归档</text></view
        >
        <view
          ><strong>{{ scoredCount }}</strong
          ><text>有成绩</text></view
        >
        <view
          ><strong>{{ archive.summary.legacy }}</strong
          ><text>旧版记录</text></view
        >
      </view>
    </view>

    <view class="archive-body">
      <view class="archive-filters">
        <button
          v-for="filter in filters"
          :key="filter.key"
          :class="{ active: activeFilter === filter.key }"
          @click="activeFilter = filter.key"
        >
          {{ filter.label }}<text>{{ filterCount(filter.key) }}</text>
        </button>
      </view>

      <view v-if="loading" class="archive-state"
        ><span class="archive-state__stamp">阅</span
        ><strong>正在调阅训练卷宗</strong
        ><text>四个模块的记录正在汇总，请稍候。</text></view
      >
      <view v-else-if="error" class="archive-state archive-state--error"
        ><strong>卷宗加载失败</strong><text>{{ error }}</text
        ><button @click="loadArchive">重新调阅</button></view
      >
      <EmptyState
        v-else-if="!visibleItems.length"
        title="这一栏还没有记录"
        description="完成或开始一次对应训练后，记录会自动归档到这里。"
      />

      <view v-else class="archive-list">
        <article
          v-for="(item, index) in visibleItems"
          :key="item.id"
          class="training-file"
          :class="`training-file--${item.module}`"
        >
          <view class="training-file__rail"
            ><text>{{ String(index + 1).padStart(2, "0") }}</text
            ><i></i
          ></view>
          <view class="training-file__main">
            <view class="training-file__meta">
              <span>{{ moduleMeta[item.module].label }}</span>
              <span>{{ formatDate(item.updated_at) }}</span>
            </view>
            <view class="training-file__heading">
              <view
                ><h2>{{ item.title }}</h2>
                <p>{{ statusCopy(item) }}</p></view
              >
              <view v-if="item.score !== null" class="training-file__score"
                ><strong>{{ item.score }}</strong
                ><text>分</text></view
              >
              <view v-else class="training-file__mark">{{
                moduleMeta[item.module].mark
              }}</view>
            </view>
            <view class="training-file__progress"
              ><i :style="{ width: `${item.progress_percent}%` }"></i
            ></view>
            <view class="training-file__progress-copy">
              <span>{{ item.completed_steps }}/{{ item.total_steps }} 步</span>
              <span>{{ item.progress_percent }}%</span>
            </view>
            <view class="training-file__footer">
              <view class="training-file__tags">
                <span :class="`status-${item.status}`">{{
                  statusLabel[item.status]
                }}</span>
                <span v-if="item.has_report">已有报告</span>
              </view>
              <view class="training-file__actions">
                <button
                  v-if="item.status === 'completed'"
                  class="secondary"
                  @click="restart(item)"
                >
                  再次训练
                </button>
                <button @click="openItem(item)">
                  {{ actionLabel(item) }} →
                </button>
              </view>
            </view>
          </view>
        </article>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import EmptyState from "@/components/common/EmptyState.vue";
import {
  userApi,
  type PracticeArchive,
  type PracticeArchiveItem,
  type PracticeArchiveStatus,
  type PracticeModule,
} from "@/api/user";

type FilterKey = "all" | PracticeArchiveStatus;
const emptyArchive: PracticeArchive = {
  summary: {
    total: 0,
    in_progress: 0,
    awaiting_report: 0,
    completed: 0,
    legacy: 0,
  },
  items: [],
};
const archive = ref<PracticeArchive>(emptyArchive);
const loading = ref(true);
const error = ref("");
const activeFilter = ref<FilterKey>("all");
const filters: Array<{ key: FilterKey; label: string }> = [
  { key: "all", label: "全部" },
  { key: "in_progress", label: "进行中" },
  { key: "awaiting_report", label: "待归档" },
  { key: "completed", label: "已完成" },
  { key: "legacy", label: "旧版" },
];
const moduleMeta: Record<PracticeModule, { label: string; mark: string }> = {
  interview: { label: "入党谈话", mark: "谈" },
  debate: { label: "思政辩论", mark: "辩" },
  history: { label: "党史情景", mark: "史" },
  tour: { label: "红色研学", mark: "行" },
};
const statusLabel: Record<PracticeArchiveStatus, string> = {
  in_progress: "进行中",
  awaiting_report: "待生成报告",
  completed: "有效完成",
  legacy: "旧版档案",
};
const visibleItems = computed(() =>
  activeFilter.value === "all"
    ? archive.value.items
    : archive.value.items.filter((item) => item.status === activeFilter.value),
);
const scoredCount = computed(
  () =>
    archive.value.items.filter((item) => item.score !== null && !item.is_legacy)
      .length,
);

onMounted(loadArchive);

async function loadArchive() {
  loading.value = true;
  error.value = "";
  try {
    archive.value = await userApi.getPractices();
  } catch (event: any) {
    error.value = event.message || "训练记录暂时无法读取";
  } finally {
    loading.value = false;
  }
}

function filterCount(key: FilterKey) {
  return key === "all"
    ? archive.value.summary.total
    : archive.value.summary[key];
}
function formatDate(value: string) {
  return new Date(value).toLocaleDateString("zh-CN", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}
function statusCopy(item: PracticeArchiveItem) {
  if (item.is_legacy) return "旧版流程记录仅供回看，不参与当前成长统计。";
  if (item.status === "awaiting_report")
    return "训练步骤已经完成，等待生成正式评估报告。";
  if (item.status === "completed")
    return item.has_report
      ? "训练和正式报告均已归档，可继续复盘。"
      : "本次学习已经完成，可重新进入场景回顾。";
  return `进度已保存，下次将从第 ${Math.min(item.completed_steps + 1, item.total_steps)} 步继续。`;
}
function actionLabel(item: PracticeArchiveItem) {
  if (
    item.has_report &&
    (item.status === "completed" || item.status === "legacy")
  )
    return "查看报告";
  if (item.status === "awaiting_report") return "完成归档";
  if (item.status === "legacy") return "返回模块";
  if (item.status === "completed") return "再次学习";
  return "继续训练";
}
function encoded(value?: string | null) {
  return encodeURIComponent(value || "");
}
function openItem(item: PracticeArchiveItem) {
  const context = item.context;
  if (
    item.has_report &&
    (item.status === "completed" || item.status === "legacy")
  ) {
    if (item.module === "interview")
      return go(
        `/pages/interview/report?practiceId=${context.practice_id || item.id}`,
      );
    if (item.module === "debate")
      return go(
        `/pages/debate/feedback?sessionId=${context.session_id || item.id}&topicId=${context.topic_id || ""}&topic=${encoded(context.topic_title || item.title)}&stance=${context.stance || "pro"}&mode=${context.mode || "quick"}`,
      );
    if (item.module === "tour")
      return go(
        `/pages/tour/report?recordId=${context.record_id || item.id}&siteId=${context.site_id || item.source_id}&siteName=${encoded(context.site_name || item.title)}&view=1`,
      );
  }
  if (item.module === "interview")
    return go(
      `/pages/interview/practice?practiceId=${context.practice_id || item.id}`,
    );
  if (item.module === "debate")
    return go(
      `/pages/debate/arena?sessionId=${context.session_id || item.id}&topicId=${context.topic_id || ""}&title=${encoded(context.topic_title || item.title)}&stance=${context.stance || "pro"}&mode=${context.mode || "full"}`,
    );
  if (item.module === "history")
    return go(
      `/pages/history/scenario?bookId=${context.book_id || `history-${item.source_id}`}`,
    );
  return go(
    `/pages/tour/site?bookId=${context.book_id || `tour-${item.source_id}`}`,
  );
}
function restart(item: PracticeArchiveItem) {
  if (item.module === "interview") return go("/pages/interview/interview");
  if (item.module === "debate") return go("/pages/debate/debate");
  if (item.module === "history")
    return go(
      `/pages/history/scenario?bookId=${item.context.book_id || `history-${item.source_id}`}`,
    );
  return go(
    `/pages/tour/site?bookId=${item.context.book_id || `tour-${item.source_id}`}`,
  );
}
function go(url: string) {
  uni.navigateTo({ url });
}
</script>

<style scoped>
view {
  display: block;
}
.training-archive {
  min-height: 100vh;
  padding-bottom: 70rpx;
  background: #eee7dc;
  color: #382b25;
}
.archive-cover {
  position: relative;
  overflow: hidden;
  padding: 34rpx var(--page-gutter) 0;
  background: #431a18;
  color: #fff8e9;
}
.archive-cover:after {
  content: "训";
  position: absolute;
  right: -18rpx;
  top: 60rpx;
  font: 700 250rpx/0.8 var(--font-display);
  color: rgba(255, 255, 255, 0.035);
  pointer-events: none;
}
.archive-cover__folio {
  position: relative;
  z-index: 1;
  display: flex;
  justify-content: space-between;
  padding-bottom: 17rpx;
  border-bottom: 1px solid rgba(229, 199, 127, 0.28);
  font-size: 14rpx;
  letter-spacing: 3rpx;
  color: #e4c67e;
}
.archive-cover__title {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24rpx;
  padding: 35rpx 0 31rpx;
}
.archive-cover__eyebrow {
  font-size: 16rpx;
  letter-spacing: 4rpx;
  color: #d9b968;
}
.archive-cover h1 {
  margin: 7rpx 0 7rpx;
  font: 700 var(--page-title-size) var(--font-display);
  letter-spacing: 2rpx;
}
.archive-cover p {
  margin: 0;
  font-size: 18rpx;
  color: rgba(255, 248, 233, 0.58);
}
.archive-cover__seal {
  display: grid;
  place-items: center;
  align-content: center;
  width: 130rpx;
  height: 130rpx;
  flex: none;
  border: 5rpx double #d8b66e;
  border-radius: 50%;
  transform: rotate(-6deg);
}
.archive-cover__seal strong {
  font:
    700 42rpx Georgia,
    serif;
  color: #f0d58f;
}
.archive-cover__seal text {
  font-size: 14rpx;
  color: rgba(255, 248, 233, 0.7);
}
.archive-stats {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  border-top: 1px solid rgba(229, 199, 127, 0.22);
}
.archive-stats view {
  padding: 18rpx 10rpx 21rpx;
  border-right: 1px solid rgba(229, 199, 127, 0.16);
}
.archive-stats view:last-child {
  border: 0;
}
.archive-stats strong,
.archive-stats text {
  display: block;
  text-align: center;
}
.archive-stats strong {
  font:
    700 30rpx Georgia,
    serif;
  color: #e8ca83;
}
.archive-stats text {
  margin-top: 3rpx;
  font-size: 14rpx;
  color: rgba(255, 248, 233, 0.55);
}
.archive-body {
  max-width: 980px;
  margin: auto;
  padding: 27rpx var(--page-gutter);
}
.archive-filters {
  width: 100%;
  white-space: nowrap;
  margin-bottom: 23rpx;
}
.archive-filters button {
  display: inline-flex;
  align-items: center;
  gap: 9rpx;
  margin: 0 10rpx 0 0;
  padding: 13rpx 20rpx;
  border: 1px solid #d0c2af;
  border-radius: 0;
  background: #f8f2e8;
  color: #68594d;
  font-size: 17rpx;
}
.archive-filters button.active {
  border-color: #70241f;
  background: #70241f;
  color: #fff9ea;
}
.archive-filters text {
  display: grid;
  place-items: center;
  min-width: 28rpx;
  height: 28rpx;
  border-radius: 50%;
  background: rgba(128, 92, 44, 0.11);
  font:
    13rpx Georgia,
    serif;
}
.archive-filters .active text {
  background: rgba(255, 255, 255, 0.16);
}
.archive-list {
  display: grid;
  gap: 17rpx;
}
.training-file {
  display: grid;
  grid-template-columns: 55rpx 1fr;
  border: 1px solid #d7cbbb;
  background: #fffaf0;
  box-shadow: 0 10rpx 26rpx rgba(52, 37, 25, 0.05);
}
.training-file__rail {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 23rpx;
  border-right: 1px solid #dfd4c5;
  color: #7c2924;
}
.training-file__rail text {
  font:
    700 16rpx Georgia,
    serif;
}
.training-file__rail i {
  width: 1px;
  flex: 1;
  margin-top: 14rpx;
  background: linear-gradient(#b88639, transparent);
}
.training-file__main {
  padding: 22rpx 23rpx 19rpx;
}
.training-file__meta {
  display: flex;
  justify-content: space-between;
  color: #a17331;
  font-size: 14rpx;
  letter-spacing: 2rpx;
}
.training-file__meta span:last-child {
  letter-spacing: 0;
  color: #918478;
}
.training-file__heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18rpx;
  margin-top: 12rpx;
}
.training-file__heading > view:first-child {
  min-width: 0;
}
.training-file h2 {
  margin: 0;
  font: 700 27rpx/1.35 var(--font-display);
}
.training-file__heading p {
  margin: 6rpx 0 0;
  font-size: 16rpx;
  line-height: 1.5;
  color: #84766a;
}
.training-file__score {
  display: flex;
  align-items: baseline;
  flex: none;
  color: #742720;
}
.training-file__score strong {
  font:
    700 43rpx Georgia,
    serif;
}
.training-file__score text {
  font-size: 15rpx;
}
.training-file__mark {
  display: grid;
  place-items: center;
  width: 64rpx;
  height: 64rpx;
  flex: none;
  border: 3rpx double currentColor;
  border-radius: 50%;
  font: 700 23rpx var(--font-display);
  color: #7a2a24;
  transform: rotate(-5deg);
}
.training-file--debate .training-file__mark {
  color: #8c6429;
}
.training-file--history .training-file__mark {
  color: #48604c;
}
.training-file--tour .training-file__mark {
  color: #315c64;
}
.training-file__progress {
  height: 6rpx;
  margin-top: 19rpx;
  overflow: hidden;
  background: #e7ded1;
}
.training-file__progress i {
  display: block;
  height: 100%;
  background: #7a2823;
}
.training-file--debate .training-file__progress i {
  background: #a7772e;
}
.training-file--history .training-file__progress i {
  background: #4f6952;
}
.training-file--tour .training-file__progress i {
  background: #37636b;
}
.training-file__progress-copy {
  display: flex;
  justify-content: space-between;
  margin-top: 6rpx;
  font-size: 13rpx;
  color: #9a8c7e;
}
.training-file__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 15rpx;
  margin-top: 16rpx;
  padding-top: 14rpx;
  border-top: 1px solid #e9e0d3;
}
.training-file__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 7rpx;
}
.training-file__tags span {
  padding: 5rpx 9rpx;
  background: #eee6d9;
  color: #76685b;
  font-size: 13rpx;
}
.training-file__tags .status-in_progress {
  background: #e6efe8;
  color: #365b44;
}
.training-file__tags .status-awaiting_report {
  background: #f5ead3;
  color: #8b5d17;
}
.training-file__tags .status-completed {
  background: #f2dfdc;
  color: #7a2924;
}
.training-file__tags .status-legacy {
  background: #ebe8e3;
  color: #6f6b66;
}
.training-file__actions {
  display: flex;
  gap: 9rpx;
  flex: none;
}
.training-file__actions button {
  margin: 0;
  padding: 11rpx 16rpx;
  border-radius: 0;
  background: #762722;
  color: #fff;
  font-size: 15rpx;
  line-height: 1.2;
}
.training-file__actions .secondary {
  border: 1px solid #b8a997;
  background: transparent;
  color: #6e6054;
}
.archive-state {
  display: grid;
  place-items: center;
  padding: 90rpx 20rpx;
  text-align: center;
  color: #796b5e;
}
.archive-state__stamp {
  display: grid;
  place-items: center;
  width: 74rpx;
  height: 74rpx;
  margin-bottom: 15rpx;
  border: 4rpx double #8b332c;
  border-radius: 50%;
  color: #8b332c;
  font: 700 27rpx var(--font-display);
  animation: pulse 1.8s ease-in-out infinite;
}
.archive-state strong,
.archive-state text {
  display: block;
}
.archive-state strong {
  font: 700 24rpx var(--font-display);
  color: #43342c;
}
.archive-state text {
  margin-top: 7rpx;
  font-size: 17rpx;
}
.archive-state button {
  margin-top: 20rpx;
  padding: 13rpx 24rpx;
  background: #762722;
  color: white;
  border-radius: 0;
  font-size: 17rpx;
}
@keyframes pulse {
  50% {
    opacity: 0.45;
    transform: scale(0.94);
  }
}
/* #ifndef H5 */
@media (min-width: 900px) {
  .archive-list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .archive-cover__title,
  .archive-stats,
  .archive-cover__folio {
    max-width: 980px;
    margin-left: auto;
    margin-right: auto;
  }
}
/* #endif */
/* #ifdef H5 */
@container (min-width: 900px) {
  .archive-list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .archive-cover__title,
  .archive-stats,
  .archive-cover__folio {
    max-width: 980px;
    margin-left: auto;
    margin-right: auto;
  }
}
/* #endif */
/* #ifndef H5 */
@media (max-width: 480px) {
  .archive-cover__seal {
    width: 104rpx;
    height: 104rpx;
  }
  .archive-cover h1 {
    font-size: 41rpx;
  }
  .archive-cover p {
    max-width: 470rpx;
  }
  .archive-stats {
    grid-template-columns: repeat(2, 1fr);
  }
  .archive-stats view:nth-child(2) {
    border-right: 0;
  }
  .archive-stats view:nth-child(-n + 2) {
    border-bottom: 1px solid rgba(229, 199, 127, 0.16);
  }
  .training-file__footer {
    align-items: flex-end;
  }
  .training-file__actions {
    flex-direction: column;
  }
  .training-file__actions button {
    padding: 10rpx 13rpx;
  }
}
/* #endif */
/* #ifdef H5 */
@container (max-width: 480px) {
  .archive-cover__seal {
    width: 104rpx;
    height: 104rpx;
  }
  .archive-cover h1 {
    font-size: 41rpx;
  }
  .archive-cover p {
    max-width: 470rpx;
  }
  .archive-stats {
    grid-template-columns: repeat(2, 1fr);
  }
  .archive-stats view:nth-child(2) {
    border-right: 0;
  }
  .archive-stats view:nth-child(-n + 2) {
    border-bottom: 1px solid rgba(229, 199, 127, 0.16);
  }
  .training-file__footer {
    align-items: flex-end;
  }
  .training-file__actions {
    flex-direction: column;
  }
  .training-file__actions button {
    padding: 10rpx 13rpx;
  }
}
/* #endif */
</style>
