<template>
  <main class="task-page">
    <div v-if="loading" class="state">正在打开任务档案…</div>
    <div v-else-if="error" class="state error">
      <p>{{ error }}</p>
      <button @click="load">重新加载</button>
    </div>
    <template v-else-if="task">
      <header class="task-hero">
        <div>
          <small>TEACHER ASSIGNMENT · {{ taskStatus }}</small>
          <h1>{{ task.title }}</h1>
          <p>{{ task.description || "老师暂未填写补充要求" }}</p>
        </div>
        <div class="deadline">
          <small>DEADLINE</small
          ><strong>{{
            task.deadline_at ? format(task.deadline_at) : "长期有效"
          }}</strong>
        </div>
      </header>
      <div class="task-layout">
        <section class="work-paper">
          <header>
            <div>
              <small>LEARNING OUTPUT</small>
              <h2>我的学习成果</h2>
            </div>
            <span :class="submissionStatus">{{ submissionLabel }}</span>
          </header>
          <textarea
            v-model="content"
            maxlength="10000"
            :disabled="locked"
            placeholder="填写学习成果、心得或作业内容。草稿会自动保存。"
          />
          <div class="counter">
            <span v-if="saveState === 'saving'">正在保存草稿…</span
            ><span v-else-if="saveState === 'saved'">草稿已保存</span
            ><span v-else-if="saveState === 'failed'"
              >草稿保存失败，内容仍保留在本机</span
            ><small>{{ content.length }}/10000</small>
          </div>
          <div class="file-area">
            <header>
              <strong>成果附件</strong><small>最多 5 个，总计不超过 50MB</small>
            </header>
            <button
              v-for="file in files"
              :key="file.id"
              class="file-row"
              @click="openFile(file)"
            >
              <span
                ><b>{{ file.name }}</b
                ><small>{{ size(file.size) }}</small></span
              ><i v-if="!locked" @click.stop="removeFile(file.id)">移除</i
              ><i v-else>查看</i></button
            ><button
              v-if="!locked && files.length < 5"
              class="add-file"
              :disabled="uploading"
              @click="chooseFiles"
            >
              {{ uploading ? "上传中…" : "＋ 添加图片或资料附件" }}
            </button>
          </div>
          <div
            v-if="task.submission?.status === 'reviewed'"
            class="teacher-feedback"
          >
            <small>TEACHER FEEDBACK</small>
            <h3>教师反馈</h3>
            <p>{{ task.submission.feedback || "教师已完成评分" }}</p>
            <div v-if="task.submission.next_step">
              <strong>下一步建议</strong>
              <p>{{ task.submission.next_step }}</p>
            </div>
          </div>
          <footer v-if="!locked">
            <span>正式提交后，在截止或批阅前仍可更新。</span
            ><button
              :disabled="submitting || (!content.trim() && !files.length)"
              @click="submit"
            >
              {{
                submitting
                  ? "提交中…"
                  : task.submission?.status === "submitted"
                    ? "更新提交"
                    : "正式提交"
              }}
            </button>
          </footer>
        </section>
        <aside>
          <section
            class="score-card"
            v-if="task.submission?.status === 'reviewed'"
          >
            <small>FINAL SCORE</small
            ><strong>{{ task.submission.score }}</strong
            ><span>综合得分</span>
          </section>
          <section class="rubric">
            <small>ASSESSMENT RUBRIC</small>
            <h3>评价量规</h3>
            <article v-for="item in task.rubric" :key="item.id">
              <header>
                <b>{{ item.title }}</b
                ><span>{{ item.weight }}%</span>
              </header>
              <p>{{ item.description || "按该维度评价学习成果" }}</p>
              <div v-if="scoreOf(item.id)" class="rubric-result">
                <strong>{{ scoreOf(item.id)?.score }} 分</strong
                ><span>{{ scoreOf(item.id)?.comment }}</span>
              </div>
            </article>
          </section>
          <section v-if="task.attachments.length" class="resources">
            <small>TASK MATERIALS</small>
            <h3>任务资料</h3>
            <button
              v-for="file in task.attachments"
              :key="file.id"
              @click="openFile(file)"
            >
              <b>{{ file.name }}</b
              ><span>{{ size(file.size) }} · 查看</span>
            </button>
          </section>
        </aside>
      </div>
    </template>
  </main>
</template>
<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { onHide, onLoad } from "@dcloudio/uni-app";
import {
  communityApi,
  type CommunityAttachment,
  type TeacherTask,
} from "@/api/community";
const id = ref(""),
  task = ref<TeacherTask | null>(null),
  content = ref(""),
  files = ref<CommunityAttachment[]>([]),
  loading = ref(true),
  error = ref(""),
  uploading = ref(false),
  submitting = ref(false),
  saveState = ref<"idle" | "saving" | "saved" | "failed">("idle");
let ready = false,
  timer: any;
const locked = computed(
  () =>
    !task.value ||
    ["reviewed"].includes(task.value.submission?.status || "") ||
    ["expired", "closed"].includes(task.value.status),
);
const taskStatus = computed(() =>
  task.value?.status === "expired"
    ? "已截止"
    : task.value?.status === "closed"
      ? "已关闭"
      : task.value?.submission?.status === "reviewed"
        ? "已批阅"
        : "进行中",
);
const submissionStatus = computed(
    () => task.value?.submission?.status || "draft",
  ),
  submissionLabel = computed(
    () =>
      (({ draft: "草稿", submitted: "已提交", reviewed: "已批阅" }) as any)[
        submissionStatus.value
      ] || "未开始",
  );
async function load() {
  loading.value = true;
  error.value = "";
  try {
    task.value = await communityApi.getTask(id.value);
    content.value =
      task.value.submission?.content ||
      uni.getStorageSync(`task-draft:${id.value}`) ||
      "";
    files.value = task.value.submission?.attachments || [];
    ready = true;
  } catch (e: any) {
    error.value = e.message || "任务加载失败";
  } finally {
    loading.value = false;
  }
}
async function saveDraft() {
  if (!ready || locked.value) return;
  uni.setStorageSync(`task-draft:${id.value}`, content.value);
  saveState.value = "saving";
  try {
    const result = await communityApi.saveTaskDraft(id.value, {
      content: content.value,
      attachment_ids: files.value.map((x) => x.id),
    });
    if (task.value) task.value.submission = result;
    saveState.value = "saved";
  } catch {
    saveState.value = "failed";
  }
}
function chooseFiles() {
  const chooser = (uni as any).chooseFile || (uni as any).chooseMessageFile;
  chooser({
    count: 5 - files.value.length,
    extension: ["jpg", "jpeg", "png", "webp", "pdf", "docx", "txt"],
    success: async (result: any) => {
      uploading.value = true;
      try {
        for (const file of result.tempFiles || []) {
          files.value.push(await communityApi.upload(file, "task"));
        }
        await saveDraft();
      } catch (e: any) {
        uni.showToast({ title: e.message || "附件上传失败", icon: "none" });
      } finally {
        uploading.value = false;
      }
    },
  });
}
async function removeFile(fileId: string) {
  files.value = files.value.filter((x) => x.id !== fileId);
  try {
    await communityApi.deleteAttachment(fileId);
  } catch {}
  saveDraft();
}
async function submit() {
  if (!task.value || submitting.value) return;
  submitting.value = true;
  try {
    const result = await communityApi.submitTask(task.value.id, {
      content: content.value.trim(),
      attachment_ids: files.value.map((x) => x.id),
    });
    task.value.submission = result;
    uni.removeStorageSync(`task-draft:${id.value}`);
    uni.showToast({ title: "提交成功", icon: "success" });
  } catch (e: any) {
    uni.showToast({ title: e.message || "提交失败", icon: "none" });
  } finally {
    submitting.value = false;
  }
}
function openFile(file: CommunityAttachment) {
  const token = uni.getStorageSync("token"),
    base = import.meta.env.VITE_API_BASE_URL || "/api/v1",
    origin = base.replace(/\/api\/v1$/, "");
  (uni as any).downloadFile({
    url: `${origin}${file.url}`,
    header: token ? { Authorization: `Bearer ${token}` } : {},
    success: (result: any) => {
      if (result.statusCode >= 400)
        return uni.showToast({ title: "附件下载失败", icon: "none" });
      if (file.mime_type.startsWith("image/"))
        uni.previewImage({ urls: [result.tempFilePath] });
      else
        (uni as any).openDocument({
          filePath: result.tempFilePath,
          showMenu: true,
          fail: () =>
            uni.showToast({ title: "请下载后使用本地应用打开", icon: "none" }),
        });
    },
    fail: () => uni.showToast({ title: "附件下载失败", icon: "none" }),
  });
}
function format(value: string) {
  return new Date(value).toLocaleString();
}
function size(value: number) {
  return value > 1048576
    ? `${(value / 1048576).toFixed(1)} MB`
    : `${Math.ceil(value / 1024)} KB`;
}
function scoreOf(criterionId: string) {
  return task.value?.submission?.rubric_scores?.find(
    (x) => x.criterion_id === criterionId,
  );
}
watch(content, () => {
  if (!ready || locked.value) return;
  clearTimeout(timer);
  timer = setTimeout(saveDraft, 1000);
});
onLoad((query: any) => {
  id.value = query.id || "";
  load();
});
onHide(() => {
  if (ready && !locked.value) saveDraft();
});
</script>
<style scoped>
.task-page {
  min-height: 100vh;
  background: #ece5da;
}
.task-hero {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 30px;
  padding: 38px clamp(22px, 6vw, 68px);
  background: #321e1b;
  color: #fff8ea;
}
.task-hero small,
.work-paper > header small,
.rubric > small,
.resources > small,
.teacher-feedback > small,
.score-card > small {
  color: #d5b76f;
  font:
    9px Georgia,
    serif;
  letter-spacing: 2px;
}
.task-hero h1 {
  margin: 8px 0;
  font-size: 34px;
}
.task-hero p {
  max-width: 680px;
  margin: 0;
  color: rgba(255, 248, 234, 0.6);
  font-size: 13px;
}
.deadline {
  text-align: right;
}
.deadline strong {
  display: block;
  margin-top: 5px;
  color: #e2cb91;
  font:
    18px Georgia,
    serif;
}
.task-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 280px;
  gap: 22px;
  max-width: 1040px;
  margin: auto;
  padding: 28px;
}
.work-paper,
.rubric,
.resources,
.score-card {
  border: 1px solid #d6c9b9;
  background: #fffaf2;
}
.work-paper {
  padding: 26px;
}
.work-paper > header {
  display: flex;
  justify-content: space-between;
}
.work-paper h2 {
  margin: 4px 0 13px;
}
.work-paper > header > span {
  align-self: start;
  padding: 5px 10px;
  background: #eee4d6;
  color: #80674c;
  font-size: 10px;
}
.work-paper > header > span.reviewed {
  background: #e5efe6;
  color: #356147;
}
.work-paper textarea {
  min-height: 300px;
}
.counter {
  display: flex;
  justify-content: space-between;
  margin-top: 6px;
  color: #9c8e80;
  font-size: 9px;
}
.counter span {
  color: #87662f;
}
.file-area {
  margin-top: 23px;
}
.file-area > header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 9px;
}
.file-area header small {
  color: #9e9082;
  font-size: 9px;
}
.file-row {
  display: flex;
  justify-content: space-between;
  width: 100%;
  padding: 11px 12px;
  border-top: 1px solid #e9dfd1;
  text-align: left;
}
.file-row span {
  display: grid;
}
.file-row b {
  font-size: 11px;
}
.file-row small,
.file-row i {
  color: #968778;
  font-size: 9px;
  font-style: normal;
}
.add-file {
  width: 100%;
  padding: 13px;
  border: 1px dashed #bda98b;
  color: #80522c;
  font-size: 11px;
}
.work-paper > footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 25px;
  padding-top: 17px;
  border-top: 1px solid #e9dfd2;
}
.work-paper > footer span {
  color: #97897b;
  font-size: 10px;
}
.work-paper > footer button {
  padding: 11px 18px;
  background: #7f211d;
  color: #fff;
}
.teacher-feedback {
  margin-top: 24px;
  padding: 19px;
  border-left: 4px solid #37634b;
  background: #edf3ed;
}
.teacher-feedback h3 {
  margin: 4px 0;
}
.teacher-feedback p {
  color: #56675d;
  font-size: 12px;
}
.teacher-feedback > div {
  padding-top: 10px;
  border-top: 1px solid #d3e0d4;
}
.task-layout > aside {
  display: grid;
  align-content: start;
  gap: 15px;
}
.rubric,
.resources,
.score-card {
  padding: 19px;
}
.rubric h3,
.resources h3 {
  margin: 4px 0 10px;
}
.rubric article {
  padding: 12px 0;
  border-top: 1px solid #e8ded0;
}
.rubric article header {
  display: flex;
  justify-content: space-between;
}
.rubric article b {
  font-size: 12px;
}
.rubric article header span {
  color: #9b6f2f;
  font:
    11px Georgia,
    serif;
}
.rubric article p {
  margin: 4px 0;
  color: #8a7c6e;
  font-size: 10px;
}
.rubric-result {
  display: grid;
  margin-top: 7px;
  padding: 8px;
  background: #edf2eb;
}
.rubric-result strong {
  color: #376049;
  font-size: 11px;
}
.rubric-result span {
  color: #647368;
  font-size: 9px;
}
.resources button {
  display: grid;
  width: 100%;
  padding: 10px 0;
  border-top: 1px solid #e8ded0;
  text-align: left;
}
.resources b {
  font-size: 11px;
}
.resources span {
  color: #96877a;
  font-size: 9px;
}
.score-card {
  text-align: center;
  border-top: 4px solid #7f211d;
}
.score-card strong {
  display: block;
  color: #7f211d;
  font:
    700 52px Georgia,
    serif;
}
.score-card span {
  font-size: 10px;
  color: #8d7f71;
}
.state {
  max-width: 850px;
  margin: 50px auto;
  padding: 70px;
  text-align: center;
}
.state.error {
  color: #9b3831;
}
/* #ifndef H5 */
@media (max-width: 740px) {
  .task-hero {
    display: block;
    padding: 26px 20px;
  }
  .task-hero h1 {
    font-size: 28px;
  }
  .deadline {
    margin-top: 20px;
    text-align: left;
  }
  .task-layout {
    grid-template-columns: 1fr;
    padding: 13px;
  }
  .work-paper {
    padding: 19px 14px;
  }
  .work-paper textarea {
    min-height: 240px;
  }
  .work-paper > footer {
    align-items: flex-end;
    gap: 12px;
  }
  .work-paper > footer span {
    max-width: 60%;
  }
  .task-layout > aside {
    grid-row: 1;
  }
  .score-card {
    display: none;
  }
}
/* #endif */
/* #ifdef H5 */
@container (max-width: 740px) {
  .task-hero {
    display: block;
    padding: 26px 20px;
  }
  .task-hero h1 {
    font-size: 28px;
  }
  .deadline {
    margin-top: 20px;
    text-align: left;
  }
  .task-layout {
    grid-template-columns: 1fr;
    padding: 13px;
  }
  .work-paper {
    padding: 19px 14px;
  }
  .work-paper textarea {
    min-height: 240px;
  }
  .work-paper > footer {
    align-items: flex-end;
    gap: 12px;
  }
  .work-paper > footer span {
    max-width: 60%;
  }
  .task-layout > aside {
    grid-row: 1;
  }
  .score-card {
    display: none;
  }
}
/* #endif */
</style>
