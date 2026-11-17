<template>
  <div class="debate">
    <header class="debate-hero">
      <div class="debate-hero__top"><span>DIALECTIC ARENA · 01</span><span>思政辩论场</span></div>
      <div class="debate-hero__sides"><i>正</i><span>观点交锋</span><i>反</i></div>
      <h1>不是争输赢，<br />而是把观点想得更深</h1>
      <p>选择立场、提出论据、回应质询，在四阶段交锋中训练论证与价值判断。</p>
    </header>

    <main class="debate__main">
      <section class="debate-flow"><div v-for="(stage,index) in stages" :key="stage"><i>{{ String(index+1).padStart(2,'0') }}</i><strong>{{ stage }}</strong></div></section>
      <section v-if="history.length" class="debate-history">
        <div class="debate-history__head"><div><span>SESSION ARCHIVE</span><h2>最近赛训</h2></div><small>旧版记录仅供回看</small></div>
        <article v-for="item in history.slice(0,4)" :key="item.id" @click="openHistory(item)">
          <div><strong>{{ item.topic_title }}</strong><text>{{ item.stance==='pro'?'正方':'反方' }} · {{ item.mode==='full'?'完整赛训':'快速练习' }} · {{ debateCompleted(item) }}/{{ item.total_steps || (item.mode==='full'?6:4) }} 步</text></div>
          <b>{{ item.is_legacy?'旧版':debateHasReport(item)?`${item.score ?? '—'} 分`:item.status==='awaiting_feedback'?'生成报告 →':'继续 →' }}</b>
        </article>
      </section>
      <section class="debate__heading"><div><span>TOPIC ARCHIVE</span><h2>选择今日辩题</h2></div><button :disabled="generating" @click="generateTopics">{{ generating ? '正在拟题…' : '+ AI 拟题' }}</button></section>
      <div v-if="loading" class="debate__state">正在准备辩题…</div>
      <section v-else class="topic-list">
        <article v-for="(topic,index) in topics" :key="topic.id" class="topic-card">
          <div class="topic-card__head"><span>TOPIC {{ String(index+1).padStart(2,'0') }}</span><b>{{ topic.category }}</b></div>
          <h3>{{ topic.title }}</h3><p>{{ topic.context || '围绕命题建立清晰立场，并用事实、逻辑与价值判断完成论证。' }}</p>
          <div class="topic-card__divider"><span>选择你的立场</span><i></i></div>
          <div class="topic-card__actions"><button class="pro" @click="startDebate(topic,'pro')"><i>正</i><span><strong>正方出战</strong><small>支持命题</small></span></button><button class="con" @click="startDebate(topic,'con')"><i>反</i><span><strong>反方出战</strong><small>反对命题</small></span></button></div>
        </article>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { debateApi, type DebateHistoryItem, type DebateTopic } from "@/api/debate";

const topics = ref<DebateTopic[]>([]);
const loading = ref(true);
const generating = ref(false);
const history = ref<DebateHistoryItem[]>([]);
const stages = ["立论", "质询", "驳论", "总结"];

onMounted(async () => {
  try {
    const [rows, archive] = await Promise.all([debateApi.getTopics(), debateApi.getHistory()]);
    topics.value = rows || [];
    history.value = archive || [];
  } catch (error: any) {
    uni.showToast({ title: error.message || "辩题加载失败", icon: "none" });
  } finally {
    loading.value = false;
  }
});

async function generateTopics() {
  if (generating.value) return;
  generating.value = true;
  try {
    const rows = await debateApi.generateTopics();
    if (rows?.length) topics.value = [...rows, ...topics.value];
    uni.showToast({ title: "新辩题已加入", icon: "success" });
  } catch (error: any) {
    uni.showToast({ title: error.message || "生成失败", icon: "none" });
  } finally {
    generating.value = false;
  }
}

function debateCompleted(item: DebateHistoryItem) {
  return item.completed_steps ?? item.step_index ?? item.rounds ?? 0;
}

function debateHasReport(item: DebateHistoryItem) {
  return item.has_report ?? (item.status === "completed" && item.score != null);
}

function openHistory(item: DebateHistoryItem) {
  const feedbackUrl =
    `/pages/debate/feedback?sessionId=${item.id}&topicId=${item.topic_id}` +
    `&topic=${encodeURIComponent(item.topic_title)}&stance=${item.stance}&mode=${item.mode}`;
  if (item.is_legacy) {
    if (debateHasReport(item)) return uni.navigateTo({ url: feedbackUrl });
    return uni.showToast({ title: "这条旧版记录没有可用报告", icon: "none" });
  }
  if (debateHasReport(item)) return uni.navigateTo({ url: feedbackUrl });
  uni.navigateTo({
    url:
      `/pages/debate/arena?sessionId=${item.id}&topicId=${item.topic_id}` +
      `&stance=${item.stance}&mode=${item.mode}&title=${encodeURIComponent(item.topic_title)}`,
  });
}

function startDebate(topic: DebateTopic, stance: string) {
  uni.showModal({
    title: "选择训练模式",
    content:
      "完整赛训包含立论、双向质询、两轮攻防和总结，共6步；快速练习保留4个核心阶段。",
    confirmText: "完整赛训",
    cancelText: "快速练习",
    success: (result) => {
      const mode = result.confirm ? "full" : "quick";
      uni.navigateTo({
        url:
          `/pages/debate/arena?topicId=${topic.id}&stance=${stance}` +
          `&mode=${mode}&title=${encodeURIComponent(topic.title)}`,
      });
    },
  });
}</script>

<style scoped>
.debate{min-height:100vh;padding-bottom:65rpx;background:var(--color-bg)}.debate-hero{position:relative;overflow:hidden;padding:52rpx var(--page-gutter) 48rpx;color:#fff9ed;background:#24221f}.debate-hero::before,.debate-hero::after{content:'';position:absolute;top:115rpx;width:220rpx;height:220rpx;border:1px solid rgba(231,201,129,.13);border-radius:50%}.debate-hero::before{left:-110rpx}.debate-hero::after{right:-110rpx}.debate-hero__top{display:flex;justify-content:space-between;font-size:16rpx;letter-spacing:3rpx;color:#d7bd7a}.debate-hero__sides{display:flex;align-items:center;justify-content:center;gap:30rpx;margin:42rpx 0 22rpx}.debate-hero__sides i{display:grid;place-items:center;width:74rpx;height:74rpx;border:3rpx double #d7bd7a;border-radius:50%;font:700 27rpx var(--font-display);font-style:normal;color:#d7bd7a}.debate-hero__sides span{font-size:17rpx;letter-spacing:6rpx;color:rgba(255,249,237,.5)}.debate-hero h1{position:relative;margin:0;text-align:center;font:700 47rpx/1.28 var(--font-display);letter-spacing:2rpx}.debate-hero>p{width:84%;margin:18rpx auto 0;text-align:center;font-size:20rpx;line-height:1.65;color:rgba(255,249,237,.58)}.debate__main{padding:0 var(--page-gutter)}.debate-flow{display:grid;grid-template-columns:repeat(4,1fr);margin-top:-1rpx;padding:20rpx 8rpx;background:#fffaf0;border:1px solid rgba(72,25,22,.12);box-shadow:0 10rpx 28rpx rgba(45,31,23,.07)}.debate-flow div{text-align:center;border-right:1px solid rgba(72,25,22,.1)}.debate-flow div:last-child{border:0}.debate-flow i,.debate-flow strong{display:block}.debate-flow i{font-style:normal;font-size:15rpx;color:var(--color-gold)}.debate-flow strong{margin-top:4rpx;font:700 20rpx var(--font-display);color:var(--color-text)}.debate__heading{display:flex;align-items:end;justify-content:space-between;margin:38rpx 0 22rpx;padding-bottom:17rpx;border-bottom:1px solid rgba(72,25,22,.16)}.debate__heading span{font-size:16rpx;letter-spacing:4rpx;color:var(--color-gold)}.debate__heading h2{margin:5rpx 0 0;font:700 33rpx var(--font-display);color:var(--color-text)}.debate__heading button{margin:0;padding:13rpx 19rpx;border:1px solid rgba(72,25,22,.16);border-radius:2rpx;background:#fffaf0;color:var(--color-primary);font-size:18rpx;line-height:1.2}.debate__state{padding:70rpx;text-align:center;color:var(--color-text-muted)}.topic-card{margin-bottom:22rpx;padding:27rpx;background:var(--color-card);border:1px solid rgba(72,25,22,.11);box-shadow:0 7rpx 23rpx rgba(47,32,23,.055)}.topic-card__head{display:flex;justify-content:space-between;font-size:16rpx;letter-spacing:3rpx;color:var(--color-gold)}.topic-card__head b{padding:4rpx 9rpx;background:rgba(127,33,29,.06);color:var(--color-primary);font-weight:500;letter-spacing:1rpx}.topic-card h3{margin:15rpx 0 9rpx;font:700 29rpx/1.45 var(--font-display);color:var(--color-text)}.topic-card>p{margin:0;font-size:20rpx;line-height:1.6;color:var(--color-text-muted)}.topic-card__divider{display:flex;align-items:center;gap:13rpx;margin:22rpx 0 16rpx;font-size:16rpx;color:var(--color-text-muted)}.topic-card__divider i{flex:1;height:1px;background:rgba(72,25,22,.1)}.topic-card__actions{display:flex;gap:13rpx}.topic-card__actions button{display:flex;align-items:center;gap:12rpx;flex:1;margin:0;padding:16rpx;border-radius:2rpx;text-align:left}.topic-card__actions button>i{display:grid;place-items:center;width:40rpx;height:40rpx;border-radius:50%;font:700 18rpx var(--font-display);font-style:normal}.topic-card__actions span,.topic-card__actions strong,.topic-card__actions small{display:block}.topic-card__actions strong{font-size:20rpx}.topic-card__actions small{margin-top:2rpx;font-size:15rpx;opacity:.62}.topic-card__actions .pro{border:1px solid rgba(49,91,73,.25);background:rgba(49,91,73,.07);color:var(--color-green)}.topic-card__actions .pro i{color:white;background:var(--color-green)}.topic-card__actions .con{border:1px solid rgba(127,33,29,.22);background:rgba(127,33,29,.055);color:var(--color-primary)}.topic-card__actions .con i{color:white;background:var(--color-primary)}
.debate-history{margin:25rpx 0 0;padding:23rpx;background:#f8f1e4;border:1px solid rgba(72,25,22,.12)}.debate-history__head{display:flex;align-items:end;justify-content:space-between;margin-bottom:12rpx}.debate-history__head span{font-size:14rpx;letter-spacing:3rpx;color:var(--color-gold)}.debate-history__head h2{margin:3rpx 0 0;font:700 27rpx var(--font-display)}.debate-history__head small{font-size:14rpx;color:var(--color-text-muted)}.debate-history article{display:flex;align-items:center;justify-content:space-between;padding:15rpx 0;border-top:1px solid rgba(72,25,22,.1)}.debate-history strong,.debate-history text{display:block}.debate-history strong{max-width:490rpx;font-size:20rpx;line-height:1.35}.debate-history text{margin-top:3rpx;font-size:15rpx;color:var(--color-text-muted)}.debate-history b{flex:none;font-size:17rpx;color:var(--color-primary)}
/* #ifndef H5 */
@media (min-width: 769px){.debate__main{padding:0 28px 52px}.topic-list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}.topic-card{margin-bottom:0}.debate-history{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));column-gap:28px}.debate-history__head{grid-column:1/-1}.debate-hero>p{max-width:720px}}
/* #endif */
/* #ifdef H5 */
@container (min-width: 769px){.debate__main{padding:0 28px 52px}.topic-list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}.topic-card{margin-bottom:0}.debate-history{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));column-gap:28px}.debate-history__head{grid-column:1/-1}.debate-hero>p{max-width:720px}}
/* #endif */
</style>
