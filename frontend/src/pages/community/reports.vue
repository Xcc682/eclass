<template>
  <view class="reports">
    <header class="reports-hero">
      <view class="reports-hero__folio"
        ><span>FORMAL REPORT ARCHIVE</span
        ><span
          >{{ String(currentReports.length).padStart(2, "0") }} 份有效报告</span
        ></view
      >
      <view class="reports-hero__body"
        ><view
          ><p>个人学习评估 · 正式归档</p>
          <h1>我的报告</h1>
          <text
            >这里只保存谈话、辩论与研学形成的正式报告，打开后回到原模块完整复盘。</text
          ></view
        ><view class="reports-hero__seal"
          ><strong>档</strong><small>有效报告</small></view
        ></view
      >
    </header>

    <main class="reports__main">
      <view class="reports__tabs">
        <button
          :class="{ active: scope === 'current' }"
          @click="scope = 'current'"
        >
          有效报告 <span>{{ currentReports.length }}</span>
        </button>
        <button
          :class="{ active: scope === 'legacy' }"
          @click="scope = 'legacy'"
        >
          旧版档案 <span>{{ legacyReports.length }}</span>
        </button>
      </view>
      <p v-if="scope === 'legacy'" class="reports__notice">
        旧版报告保留原始内容供回看，不计入当前有效报告、能力画像和成长趋势。
      </p>

      <view v-if="loading" class="reports__state"
        ><i>阅</i><strong>正在调阅正式报告</strong></view
      >
      <view v-else-if="error" class="reports__state reports__state--error"
        ><strong>报告加载失败</strong>
        <p>{{ error }}</p>
        <button @click="loadReports">重新加载</button></view
      >
      <EmptyState
        v-else-if="!visibleReports.length"
        :title="scope === 'legacy' ? '暂无旧版档案' : '暂无有效报告'"
        :description="
          scope === 'legacy'
            ? '旧版流程报告会集中保存在这里。'
            : '完成一次完整谈话、辩论或研学后，正式报告会自动归档。'
        "
      />

      <section v-else class="reports__list">
        <article
          v-for="(report, index) in visibleReports"
          :key="report.id"
          @click="openReport(report)"
        >
          <view class="report-file__rail"
            ><span>{{ String(index + 1).padStart(2, "0") }}</span
            ><i></i
          ></view>
          <view class="report-file__body">
            <view class="report-file__meta"
              ><span>{{ typeLabel[report.type] }}报告</span
              ><span>{{ formatDate(report.created_at) }}</span></view
            >
            <view class="report-file__headline"
              ><view
                ><h2>{{ report.title }}</h2>
                <p>{{ preview(report) }}</p></view
              ><view v-if="report.score !== null" class="report-file__score"
                ><strong>{{ report.score }}</strong
                ><small>分</small></view
              ><view v-else class="report-file__stamp">{{
                typeMark[report.type]
              }}</view></view
            >
            <footer>
              <span>{{
                report.is_legacy
                  ? "旧版流程 · 仅供回看"
                  : "正式归档 · 可追溯原训练"
              }}</span
              ><b>查看完整报告 →</b>
            </footer>
          </view>
        </article>
      </section>
    </main>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import EmptyState from "@/components/common/EmptyState.vue";
import { userApi, type FormalReportItem } from "@/api/user";

const currentReports = ref<FormalReportItem[]>([]);
const legacyReports = ref<FormalReportItem[]>([]);
const scope = ref<"current" | "legacy">("current");
const loading = ref(true);
const error = ref("");
const visibleReports = computed(() =>
  scope.value === "current" ? currentReports.value : legacyReports.value,
);
const typeLabel: Record<FormalReportItem["type"], string> = {
  interview: "谈话",
  debate: "辩论",
  tour: "研学",
};
const typeMark: Record<FormalReportItem["type"], string> = {
  interview: "谈",
  debate: "辩",
  tour: "行",
};

onMounted(loadReports);

async function loadReports() {
  loading.value = true;
  error.value = "";
  try {
    [currentReports.value, legacyReports.value] = await Promise.all([
      userApi.getReports("current"),
      userApi.getReports("legacy"),
    ]);
  } catch (event: any) {
    error.value = event.message || "正式报告暂时无法读取";
  } finally {
    loading.value = false;
  }
}
function content(report: FormalReportItem): Record<string, any> {
  if (typeof report.content !== "string")
    return report.content as Record<string, any>;
  try {
    return JSON.parse(report.content);
  } catch {
    return {};
  }
}
function preview(report: FormalReportItem) {
  const data = content(report);
  return (
    data.suggestion ||
    data.report ||
    data.summary ||
    "打开原模块，查看完整评估、能力分析与复盘建议。"
  );
}
function formatDate(value: string) {
  return new Date(value).toLocaleDateString("zh-CN", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}
function encoded(value?: string | null) {
  return encodeURIComponent(value || "");
}
function openReport(report: FormalReportItem) {
  const context = report.context || {};
  if (
    report.type === "interview" &&
    (context.practice_id || report.source_record_id)
  ) {
    return go(
      `/pages/interview/report?practiceId=${context.practice_id || report.source_record_id}`,
    );
  }
  if (
    report.type === "debate" &&
    (context.session_id || report.source_record_id)
  ) {
    return go(
      `/pages/debate/feedback?sessionId=${context.session_id || report.source_record_id}&topicId=${context.topic_id || ""}&topic=${encoded(context.topic_title || report.title)}&stance=${context.stance || "pro"}&mode=${context.mode || "quick"}`,
    );
  }
  if (
    report.type === "tour" &&
    (context.record_id || report.source_record_id)
  ) {
    return go(
      `/pages/tour/report?recordId=${context.record_id || report.source_record_id}&siteId=${context.site_id || ""}&siteName=${encoded(context.site_name || report.title)}&view=1`,
    );
  }
  uni.showToast({ title: "原训练记录不存在，暂时无法打开", icon: "none" });
}
function go(url: string) {
  uni.navigateTo({ url });
}
</script>

<style scoped>
view {
  display: block;
}
.reports {
  min-height: 100vh;
  padding-bottom: 70rpx;
  background: #eee7dc;
  color: #392d27;
}
.reports-hero {
  position: relative;
  overflow: hidden;
  padding: 32rpx var(--page-gutter) 34rpx;
  color: #fff8e9;
  background: #431a18;
}
.reports-hero:after {
  content: "REPORT";
  position: absolute;
  right: -40rpx;
  bottom: -18rpx;
  color: rgba(255, 255, 255, 0.035);
  font:
    italic 100rpx Georgia,
    serif;
  pointer-events: none;
}
.reports-hero__folio {
  position: relative;
  z-index: 1;
  display: flex;
  justify-content: space-between;
  padding-bottom: 17rpx;
  border-bottom: 1px solid rgba(231, 201, 129, 0.28);
  font-size: 14rpx;
  letter-spacing: 3rpx;
  color: #e7c981;
}
.reports-hero__body {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 28rpx;
  padding-top: 31rpx;
}
.reports-hero__body p {
  margin: 0;
  color: #d8b96f;
  font-size: 15rpx;
  letter-spacing: 3rpx;
}
.reports-hero h1 {
  margin: 7rpx 0 9rpx;
  font: 700 var(--page-title-size) var(--font-display);
}
.reports-hero__body text {
  display: block;
  max-width: 650rpx;
  font-size: 18rpx;
  line-height: 1.65;
  color: rgba(255, 248, 233, 0.58);
}
.reports-hero__seal {
  display: grid;
  place-items: center;
  align-content: center;
  width: 116rpx;
  height: 116rpx;
  flex: none;
  border: 5rpx double #d8b66e;
  border-radius: 50%;
  transform: rotate(-7deg);
}
.reports-hero__seal strong {
  font: 700 34rpx var(--font-display);
  color: #f0d38c;
}
.reports-hero__seal small {
  font-size: 13rpx;
  color: rgba(255, 248, 233, 0.64);
}
.reports__main {
  max-width: 960px;
  margin: auto;
  padding: 27rpx var(--page-gutter);
}
.reports__tabs {
  display: flex;
  margin-bottom: 18rpx;
  border-bottom: 1px solid #cbbba5;
}
.reports__tabs button {
  position: relative;
  margin: 0 26rpx 0 0;
  padding: 14rpx 2rpx 16rpx;
  border: 0;
  background: transparent;
  color: #7c6d60;
  font-size: 18rpx;
}
.reports__tabs button:after {
  content: "";
  position: absolute;
  left: 0;
  right: 0;
  bottom: -1px;
  height: 4rpx;
  background: transparent;
}
.reports__tabs button.active {
  color: #73251f;
  font-weight: 700;
}
.reports__tabs button.active:after {
  background: #73251f;
}
.reports__tabs span {
  margin-left: 6rpx;
  color: #a3732e;
  font:
    15rpx Georgia,
    serif;
}
.reports__notice {
  margin: 0 0 19rpx;
  padding: 14rpx 17rpx;
  border-left: 4rpx solid #a97b36;
  background: #f7efe1;
  color: #7d6d5e;
  font-size: 15rpx;
  line-height: 1.55;
}
.reports__list {
  display: grid;
  gap: 17rpx;
}
.reports__list article {
  display: grid;
  grid-template-columns: 55rpx 1fr;
  border: 1px solid #d7cbbb;
  background: #fffaf0;
  box-shadow: 0 10rpx 28rpx rgba(49, 34, 22, 0.055);
  cursor: pointer;
}
.report-file__rail {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 24rpx;
  border-right: 1px solid #e0d5c6;
  color: #7b2923;
}
.report-file__rail span {
  font:
    700 16rpx Georgia,
    serif;
}
.report-file__rail i {
  width: 1px;
  flex: 1;
  margin-top: 14rpx;
  background: linear-gradient(#b7873e, transparent);
}
.report-file__body {
  padding: 22rpx 23rpx 18rpx;
}
.report-file__meta {
  display: flex;
  justify-content: space-between;
  color: #a47531;
  font-size: 14rpx;
  letter-spacing: 2rpx;
}
.report-file__meta span:last-child {
  letter-spacing: 0;
  color: #94877a;
}
.report-file__headline {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18rpx;
  margin-top: 11rpx;
}
.report-file__headline > view:first-child {
  min-width: 0;
}
.report-file h2 {
  margin: 0;
  font: 700 28rpx/1.35 var(--font-display);
}
.report-file p {
  display: -webkit-box;
  overflow: hidden;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  margin: 7rpx 0 0;
  font-size: 17rpx;
  line-height: 1.55;
  color: #807267;
}
.report-file__score {
  display: flex;
  align-items: baseline;
  flex: none;
  color: #752720;
}
.report-file__score strong {
  font:
    700 45rpx Georgia,
    serif;
}
.report-file__score small {
  font-size: 14rpx;
}
.report-file__stamp {
  display: grid;
  place-items: center;
  width: 64rpx;
  height: 64rpx;
  flex: none;
  border: 3rpx double #7b2923;
  border-radius: 50%;
  font: 700 23rpx var(--font-display);
  color: #7b2923;
  transform: rotate(-6deg);
}
.report-file footer {
  display: flex;
  justify-content: space-between;
  gap: 15rpx;
  margin-top: 17rpx;
  padding-top: 14rpx;
  border-top: 1px solid #e9e0d3;
  font-size: 14rpx;
  color: #8a7b6e;
}
.report-file footer b {
  flex: none;
  color: #762722;
}
.reports__state {
  display: grid;
  place-items: center;
  padding: 85rpx 20rpx;
  color: #7c6e61;
}
.reports__state i {
  display: grid;
  place-items: center;
  width: 70rpx;
  height: 70rpx;
  margin-bottom: 14rpx;
  border: 4rpx double #7c2a24;
  border-radius: 50%;
  font: 700 24rpx var(--font-display);
  color: #7c2a24;
  animation: pulse 1.8s ease-in-out infinite;
}
.reports__state strong {
  font: 700 23rpx var(--font-display);
  color: #44362f;
}
.reports__state p {
  margin: 8rpx 0;
}
.reports__state button {
  margin-top: 16rpx;
  padding: 13rpx 22rpx;
  border-radius: 0;
  background: #762722;
  color: #fff;
  font-size: 16rpx;
}
@keyframes pulse {
  50% {
    opacity: 0.45;
    transform: scale(0.94);
  }
}
/* #ifndef H5 */
@media (min-width: 900px) {
  .reports__list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .reports-hero__folio,
  .reports-hero__body {
    max-width: 960px;
    margin-left: auto;
    margin-right: auto;
  }
}
/* #endif */
/* #ifdef H5 */
@container (min-width: 900px) {
  .reports__list {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .reports-hero__folio,
  .reports-hero__body {
    max-width: 960px;
    margin-left: auto;
    margin-right: auto;
  }
}
/* #endif */
/* #ifndef H5 */
@media (max-width: 420px) {
  .reports-hero__seal {
    width: 92rpx;
    height: 92rpx;
  }
  .reports-hero h1 {
    font-size: 40rpx;
  }
  .report-file footer {
    align-items: flex-end;
  }
  .report-file footer span {
    max-width: 58%;
  }
}
/* #endif */
/* #ifdef H5 */
@container (max-width: 420px) {
  .reports-hero__seal {
    width: 92rpx;
    height: 92rpx;
  }
  .reports-hero h1 {
    font-size: 40rpx;
  }
  .report-file footer {
    align-items: flex-end;
  }
  .report-file footer span {
    max-width: 58%;
  }
}
/* #endif */
</style>
