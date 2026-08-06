<template>
  <main class="workbench">
    <header class="workbench-hero">
      <div>
        <small>TEACHER WORKBENCH</small>
        <h1>教师任务工作台</h1>
        <p>发布清晰任务，用结构化量规给学生可继续行动的反馈。</p>
      </div>
      <div class="hero-actions">
        <button class="ghost" @click="openModeration">内容审核</button
        ><button @click="openCreator">＋ 新建任务</button>
      </div>
    </header>
    <div class="workbench-layout">
      <aside class="task-list">
        <header>
          <h2>任务档案</h2>
          <button @click="loadTasks">刷新</button>
        </header>
        <div v-if="loading" class="mini-state">加载中…</div>
        <button
          v-for="task in tasks"
          :key="task.id"
          :class="{ active: selected?.id === task.id }"
          @click="selectTask(task)"
        >
          <span
            ><strong>{{ task.title }}</strong
            ><small
              >{{ statusLabel(task.status) }} ·
              {{
                task.deadline_at ? format(task.deadline_at) : "长期有效"
              }}</small
            ></span
          ><i>{{ task.submission?.status === "reviewed" ? "已阅" : "" }}</i>
        </button>
      </aside>
      <section v-if="selected" class="task-console">
        <header>
          <div>
            <small>ASSIGNMENT DETAIL</small>
            <h2>{{ selected.title }}</h2>
            <p>{{ selected.description || "暂无任务说明" }}</p>
          </div>
          <div>
            <button @click="editSelected">编辑</button
            ><button
              v-if="selected.status === 'draft'"
              class="publish"
              @click="publishSelected"
            >
              发布</button
            ><button
              v-if="selected.status === 'published'"
              class="danger"
              @click="closeSelected"
            >
              关闭
            </button>
          </div>
        </header>
        <div class="metrics">
          <div>
            <small>任务状态</small
            ><strong>{{ statusLabel(selected.status) }}</strong>
          </div>
          <div>
            <small>评价维度</small><strong>{{ selected.rubric.length }}</strong>
          </div>
          <div>
            <small>提交人数</small><strong>{{ submissions.length }}</strong>
          </div>
          <div>
            <small>待批阅</small><strong>{{ pendingCount }}</strong>
          </div>
        </div>
        <nav>
          <button
            :class="{ active: submissionFilter === '' }"
            @click="setFilter('')"
          >
            全部</button
          ><button
            :class="{ active: submissionFilter === 'submitted' }"
            @click="setFilter('submitted')"
          >
            待批阅</button
          ><button
            :class="{ active: submissionFilter === 'reviewed' }"
            @click="setFilter('reviewed')"
          >
            已批阅
          </button>
        </nav>
        <div v-if="submissionLoading" class="console-state">
          正在加载提交记录…
        </div>
        <div v-else-if="!submissions.length" class="console-state">
          当前筛选下暂无学生提交
        </div>
        <article
          v-for="item in submissions"
          :key="item.id"
          class="submission"
          @click="openReview(item)"
        >
          <header>
            <div>
              <strong>{{ item.user_name }}</strong
              ><span>{{
                item.status === "reviewed"
                  ? `${item.score} 分`
                  : item.status === "draft"
                    ? "草稿"
                    : "等待批阅"
              }}</span>
            </div>
            <small>{{ item.updated_at ? format(item.updated_at) : "" }}</small>
          </header>
          <p>{{ item.content || "仅提交了附件" }}</p>
          <footer>
            <span>{{ item.attachments.length }} 个附件</span
            ><b
              >{{
                item.status === "reviewed" ? "查看并修改评价" : "开始批阅"
              }}
              →</b
            >
          </footer>
        </article>
      </section>
      <section v-else class="task-console empty">
        选择一项任务查看提交与评价
      </section>
    </div>

    <div v-if="creatorOpen" class="modal" @click.self="creatorOpen = false">
      <section class="creator">
        <header>
          <div>
            <small>ASSIGNMENT EDITOR</small>
            <h2>{{ editingTaskId ? "编辑任务" : "新建教师任务" }}</h2>
          </div>
          <button @click="creatorOpen = false">关闭</button>
        </header>
        <label
          >任务标题<input
            v-model="form.title"
            maxlength="300"
            placeholder="明确说明学习任务" /></label
        ><label
          >任务要求<textarea
            v-model="form.description"
            maxlength="5000"
            placeholder="写明学习目标、提交内容和评价要求"
          ></textarea></label
        ><label>截止时间<input v-model="form.deadline" type="date" /></label>
        <div class="material-editor">
          <header>
            <strong>任务资料</strong><span>最多 5 个，总计不超过 50MB</span>
          </header>
          <button
            v-for="file in taskFiles"
            :key="file.id"
            class="material-row"
            @click="openFile(file)"
          >
            <span
              ><b>{{ file.name }}</b
              ><small>{{ fileSize(file.size) }}</small></span
            >
            <i @click.stop="removeTaskFile(file.id)">移除</i>
          </button>
          <button
            v-if="taskFiles.length < 5"
            class="add"
            :disabled="uploading"
            @click="chooseTaskFiles"
          >
            {{ uploading ? "上传中…" : "＋ 添加图片、PDF、Word 或文本资料" }}
          </button>
        </div>
        <div class="rubric-editor">
          <header>
            <strong>评价量规</strong><span>权重合计 {{ weightTotal }}%</span>
          </header>
          <article v-for="(item, index) in form.rubric" :key="index">
            <input
              v-model="item.title"
              maxlength="100"
              placeholder="评价维度"
            /><input
              v-model.number="item.weight"
              type="number"
              min="1"
              max="100"
            /><textarea
              v-model="item.description"
              maxlength="500"
              placeholder="说明这一维度看什么"
            ></textarea
            ><button
              v-if="form.rubric.length > 2"
              @click="form.rubric.splice(index, 1)"
            >
              移除
            </button>
          </article>
          <button
            v-if="form.rubric.length < 5"
            class="add"
            @click="form.rubric.push({ title: '', description: '', weight: 0 })"
          >
            ＋ 添加评价维度
          </button>
        </div>
        <footer>
          <button @click="saveTask('draft')">保存草稿</button
          ><button
            class="primary"
            :disabled="saving || weightTotal !== 100"
            @click="saveTask('published')"
          >
            {{ saving ? "保存中…" : "保存并发布" }}
          </button>
        </footer>
      </section>
    </div>

    <div v-if="reviewing" class="modal" @click.self="reviewing = null">
      <section class="review">
        <header>
          <div>
            <small>STRUCTURED FEEDBACK</small>
            <h2>批阅 · {{ reviewing.user_name }}</h2>
          </div>
          <button @click="reviewing = null">关闭</button>
        </header>
        <div class="student-work">
          <small>学生提交</small>
          <p>{{ reviewing.content || "仅提交了附件" }}</p>
        </div>
        <article
          v-for="criterion in selected?.rubric || []"
          :key="criterion.id"
        >
          <header>
            <div>
              <strong>{{ criterion.title }}</strong
              ><span>权重 {{ criterion.weight }}%</span>
            </div>
            <b>{{ reviewScore(criterion.id).score }} 分</b>
          </header>
          <input
            v-model.number="reviewScore(criterion.id).score"
            type="range"
            min="0"
            max="100"
          /><textarea
            v-model="reviewScore(criterion.id).comment"
            maxlength="1000"
            placeholder="这一维度的具体反馈"
          ></textarea>
        </article>
        <label
          >总体反馈<textarea
            v-model="reviewFeedback"
            maxlength="5000"
            placeholder="总结学生本次完成情况"
          ></textarea></label
        ><label
          >下一步建议<textarea
            v-model="reviewNext"
            maxlength="2000"
            placeholder="给出一条可以立即执行的改进建议"
          ></textarea>
        </label>
        <footer>
          <span
            >加权总分 <strong>{{ weightedScore }}</strong></span
          ><button :disabled="reviewSaving" @click="submitReview">
            {{ reviewSaving ? "保存中…" : "完成批阅" }}
          </button>
        </footer>
      </section>
    </div>
  </main>
</template>
<script setup lang="ts">
import { computed, ref } from "vue";
import { onShow } from "@dcloudio/uni-app";
import {
  communityApi,
  type CommunityAttachment,
  type RubricScore,
  type TaskSubmission,
  type TeacherTask,
} from "@/api/community";
interface TaskForm {
  title: string;
  description: string;
  deadline: string;
  status: string;
  attachment_ids: string[];
  rubric: Array<{ title: string; description: string; weight: number }>;
}
const tasks = ref<TeacherTask[]>([]),
  selected = ref<TeacherTask | null>(null),
  submissions = ref<TaskSubmission[]>([]),
  loading = ref(false),
  submissionLoading = ref(false),
  submissionFilter = ref(""),
  creatorOpen = ref(false),
  editingTaskId = ref(""),
  saving = ref(false),
  reviewing = ref<TaskSubmission | null>(null),
  reviewScores = ref<RubricScore[]>([]),
  reviewFeedback = ref(""),
  reviewNext = ref(""),
  reviewSaving = ref(false),
  taskFiles = ref<CommunityAttachment[]>([]),
  uploading = ref(false);
const defaultForm = (): TaskForm => ({
  title: "",
  description: "",
  deadline: "",
  status: "published",
  attachment_ids: [],
  rubric: [
    {
      title: "内容质量",
      description: "内容完整、准确并回应任务要求",
      weight: 60,
    },
    {
      title: "思考深度",
      description: "能够联系实际形成自己的理解",
      weight: 40,
    },
  ],
});
const form = ref<TaskForm>(defaultForm());
const pendingCount = computed(
    () => submissions.value.filter((x) => x.status === "submitted").length,
  ),
  weightTotal = computed(() =>
    form.value.rubric.reduce((sum, x) => sum + Number(x.weight || 0), 0),
  ),
  weightedScore = computed(() =>
    Math.round(
      (selected.value?.rubric || []).reduce(
        (sum, item) => sum + (reviewScore(item.id).score * item.weight) / 100,
        0,
      ),
    ),
  );
async function loadTasks() {
  loading.value = true;
  try {
    tasks.value = await communityApi.getTasks();
    if (selected.value) {
      selected.value =
        tasks.value.find((x) => x.id === selected.value?.id) || null;
    }
  } finally {
    loading.value = false;
  }
}
async function selectTask(task: TeacherTask) {
  selected.value = task;
  submissionFilter.value = "";
  await loadSubmissions();
}
async function loadSubmissions() {
  if (!selected.value) return;
  submissionLoading.value = true;
  try {
    submissions.value = await communityApi.getSubmissions(
      selected.value.id,
      submissionFilter.value,
    );
  } finally {
    submissionLoading.value = false;
  }
}
function setFilter(value: string) {
  submissionFilter.value = value;
  loadSubmissions();
}
function openCreator() {
  editingTaskId.value = "";
  form.value = defaultForm();
  taskFiles.value = [];
  creatorOpen.value = true;
}
function editSelected() {
  if (!selected.value) return;
  editingTaskId.value = selected.value.id;
  taskFiles.value = [...selected.value.attachments];
  form.value = {
    title: selected.value.title,
    description: selected.value.description,
    deadline: selected.value.deadline_at?.slice(0, 10) || "",
    status: selected.value.status === "draft" ? "draft" : "published",
    attachment_ids: selected.value.attachments.map((x) => x.id),
    rubric: selected.value.rubric.map((x) => ({
      title: x.title,
      description: x.description,
      weight: x.weight,
    })),
  };
  creatorOpen.value = true;
}
async function saveTask(status: string) {
  if (form.value.title.trim().length < 2 || weightTotal.value !== 100)
    return uni.showToast({ title: "请完整填写任务与量规", icon: "none" });
  saving.value = true;
  try {
    const data = { ...form.value, status };
    const task = editingTaskId.value
      ? await communityApi.updateTask(editingTaskId.value, data)
      : await communityApi.createTask(data);
    creatorOpen.value = false;
    await loadTasks();
    await selectTask(tasks.value.find((x) => x.id === task.id) || task);
    uni.showToast({
      title: status === "draft" ? "草稿已保存" : "任务已发布",
      icon: "success",
    });
  } catch (e: any) {
    uni.showToast({ title: e.message || "保存失败", icon: "none" });
  } finally {
    saving.value = false;
  }
}
async function publishSelected() {
  if (!selected.value) return;
  await communityApi.publishTask(selected.value.id);
  await loadTasks();
}
async function closeSelected() {
  if (!selected.value) return;
  const result = await new Promise<any>((resolve) =>
    uni.showModal({
      title: "关闭任务",
      content: "关闭后学生不能继续提交，确定吗？",
      success: resolve,
    }),
  );
  if (result.confirm) {
    await communityApi.closeTask(selected.value.id);
    await loadTasks();
  }
}
function openReview(item: TaskSubmission) {
  if (!selected.value) return;
  reviewing.value = item;
  reviewFeedback.value = item.feedback || "";
  reviewNext.value = item.next_step || "";
  reviewScores.value = selected.value.rubric.map(
    (c) =>
      item.rubric_scores?.find((x) => x.criterion_id === c.id) || {
        criterion_id: c.id,
        score: 80,
        comment: "",
      },
  );
}
function reviewScore(id: string) {
  let value = reviewScores.value.find((x) => x.criterion_id === id);
  if (!value) {
    value = { criterion_id: id, score: 80, comment: "" };
    reviewScores.value.push(value);
  }
  return value;
}
async function submitReview() {
  if (!reviewing.value) return;
  reviewSaving.value = true;
  try {
    await communityApi.reviewSubmission(reviewing.value.id, {
      rubric_scores: reviewScores.value,
      feedback: reviewFeedback.value,
      next_step: reviewNext.value,
    });
    reviewing.value = null;
    await loadSubmissions();
    uni.showToast({ title: "批阅已保存", icon: "success" });
  } catch (e: any) {
    uni.showToast({ title: e.message || "批阅失败", icon: "none" });
  } finally {
    reviewSaving.value = false;
  }
}
function statusLabel(value: string) {
  return (
    (
      {
        draft: "草稿",
        published: "已发布",
        expired: "已截止",
        closed: "已关闭",
      } as any
    )[value] || value
  );
}
function chooseTaskFiles() {
  const chooser = (uni as any).chooseFile || (uni as any).chooseMessageFile;
  chooser({
    count: 5 - taskFiles.value.length,
    extension: ["jpg", "jpeg", "png", "webp", "pdf", "docx", "txt"],
    success: async (result: any) => {
      uploading.value = true;
      try {
        for (const file of result.tempFiles || [])
          taskFiles.value.push(await communityApi.upload(file, "task"));
        form.value.attachment_ids = taskFiles.value.map((item) => item.id);
      } catch (cause: any) {
        uni.showToast({ title: cause.message || "资料上传失败", icon: "none" });
      } finally {
        uploading.value = false;
      }
    },
  });
}
async function removeTaskFile(id: string) {
  taskFiles.value = taskFiles.value.filter((item) => item.id !== id);
  form.value.attachment_ids = taskFiles.value.map((item) => item.id);
  try {
    await communityApi.deleteAttachment(id);
  } catch {}
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
  });
}
function fileSize(value: number) {
  return value > 1048576
    ? `${(value / 1048576).toFixed(1)} MB`
    : `${Math.ceil(value / 1024)} KB`;
}
function openModeration() {
  uni.navigateTo({ url: "/pages/community/moderation" });
}
function format(value: string) {
  return new Date(value).toLocaleDateString();
}
onShow(loadTasks);
</script>
<style scoped>
.workbench {
  min-height: 100vh;
  background: #e9e2d7;
}
.workbench-hero {
  display: flex;
  align-items: end;
  justify-content: space-between;
  padding: 34px clamp(24px, 5vw, 60px);
  background: #2d2621;
  color: #fff8e9;
}
.workbench-hero small,
.task-console > header small,
.creator > header small,
.review > header small {
  color: #d4b66f;
  font:
    9px Georgia,
    serif;
  letter-spacing: 2px;
}
.workbench-hero h1 {
  margin: 7px 0 5px;
  font-size: 34px;
}
.workbench-hero p {
  margin: 0;
  color: rgba(255, 248, 233, 0.56);
  font-size: 12px;
}
.workbench-hero button {
  padding: 11px 16px;
  background: #d9bc76;
  color: #33261f;
  font-weight: 700;
}
.hero-actions {
  display: flex;
  gap: 8px;
}
.workbench-hero button.ghost {
  border: 1px solid rgba(222, 198, 137, 0.45);
  background: transparent;
  color: #ead9ad;
}
.workbench-layout {
  display: grid;
  grid-template-columns: 270px minmax(0, 1fr);
  max-width: 1080px;
  min-height: 650px;
  margin: 24px auto;
  border: 1px solid #d0c3b2;
  background: #f8f3eb;
}
.task-list {
  border-right: 1px solid #d8ccbc;
  background: #f1eadf;
}
.task-list > header {
  display: flex;
  justify-content: space-between;
  padding: 18px;
}
.task-list h2 {
  margin: 0;
  font-size: 18px;
}
.task-list > header button {
  color: #7d2a25;
  font-size: 10px;
}
.task-list > button {
  display: flex;
  justify-content: space-between;
  width: 100%;
  padding: 14px 17px;
  border-top: 1px solid #ded3c4;
  text-align: left;
}
.task-list > button.active {
  border-left: 4px solid #7f211d;
  background: #fffaf1;
}
.task-list > button span {
  display: grid;
}
.task-list strong {
  font-size: 12px;
}
.task-list small {
  color: #948677;
  font-size: 9px;
}
.task-list i {
  color: #3e684e;
  font-size: 9px;
  font-style: normal;
}
.mini-state {
  padding: 35px;
  text-align: center;
  color: #958779;
}
.task-console {
  padding: 25px;
}
.task-console > header {
  display: flex;
  justify-content: space-between;
  gap: 25px;
}
.task-console h2 {
  margin: 5px 0;
  font-size: 25px;
}
.task-console > header p {
  margin: 0;
  color: #7e7063;
  font-size: 12px;
}
.task-console > header > div:last-child {
  display: flex;
  gap: 7px;
}
.task-console > header button {
  padding: 7px 10px;
  border: 1px solid #c8b9a5;
  color: #736456;
  font-size: 10px;
}
.task-console > header button.publish {
  background: #315b49;
  color: #fff;
}
.task-console > header button.danger {
  color: #982f29;
}
.metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  margin: 23px 0;
  border: 1px solid #ddd1c2;
}
.metrics div {
  display: grid;
  padding: 12px;
  border-right: 1px solid #e2d7c8;
}
.metrics div:last-child {
  border: 0;
}
.metrics small {
  color: #948678;
  font-size: 9px;
}
.metrics strong {
  font:
    700 20px Georgia,
    serif;
  color: #6f2823;
}
.task-console > nav {
  display: flex;
  border-bottom: 1px solid #d8cbbb;
}
.task-console > nav button {
  padding: 9px 12px;
  color: #837466;
  font-size: 10px;
}
.task-console > nav button.active {
  border-bottom: 3px solid #7f211d;
  color: #7f211d;
}
.submission {
  margin-top: 12px;
  padding: 15px;
  border: 1px solid #ded3c5;
  background: #fffaf2;
  cursor: pointer;
}
.submission header,
.submission footer {
  display: flex;
  justify-content: space-between;
}
.submission header div {
  display: flex;
  gap: 10px;
}
.submission header span {
  color: #956b2d;
  font-size: 10px;
}
.submission header small {
  color: #998b7d;
  font-size: 9px;
}
.submission p {
  display: -webkit-box;
  overflow: hidden;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  color: #6e6258;
  font-size: 11px;
}
.submission footer {
  padding-top: 9px;
  border-top: 1px solid #ece3d7;
  color: #948678;
  font-size: 9px;
}
.submission footer b {
  color: #7d2924;
}
.console-state,
.task-console.empty {
  padding: 70px;
  text-align: center;
  color: #948678;
}
.modal {
  position: fixed;
  inset: 0;
  z-index: 3000;
  display: grid;
  place-items: center;
  padding: 20px;
  background: rgba(28, 20, 16, 0.64);
}
.creator,
.review {
  width: min(720px, 100%);
  max-height: 90vh;
  overflow: auto;
  box-sizing: border-box;
  padding: 25px;
  background: #fffaf2;
}
.creator > header,
.review > header {
  display: flex;
  justify-content: space-between;
}
.creator h2,
.review h2 {
  margin: 4px 0 17px;
}
.creator label,
.review > label {
  display: grid;
  gap: 6px;
  margin-top: 14px;
  font-size: 11px;
  font-weight: 700;
}
.creator textarea {
  min-height: 110px;
}
.material-editor,
.rubric-editor {
  margin-top: 20px;
  padding: 15px;
  background: #f1e9dd;
}
.material-editor > header,
.rubric-editor > header {
  display: flex;
  justify-content: space-between;
}
.material-editor > header span {
  color: #8f8173;
  font-size: 9px;
}
.material-row {
  display: flex;
  justify-content: space-between;
  width: 100%;
  margin-top: 8px;
  padding: 10px;
  border: 1px solid #d8cbbb;
  background: #fffaf2;
  text-align: left;
}
.material-row span {
  display: grid;
}
.material-row small {
  color: #938577;
}
.material-row i {
  color: #952f29;
  font-size: 9px;
  font-style: normal;
}
.material-editor .add {
  margin-top: 10px;
  color: #7c2924;
}
.rubric-editor article {
  display: grid;
  grid-template-columns: 1fr 90px auto;
  gap: 7px;
  margin-top: 10px;
}
.rubric-editor article textarea {
  grid-column: 1/3;
  min-height: 65px;
}
.rubric-editor article button {
  color: #982f29;
  font-size: 9px;
}
.rubric-editor .add {
  margin-top: 10px;
  color: #7c2924;
}
.creator > footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 20px;
}
.creator > footer button {
  padding: 10px 16px;
  border: 1px solid #cdbda8;
}
.creator > footer .primary,
.review > footer button {
  background: #7f211d;
  color: #fff;
}
.student-work {
  padding: 14px;
  background: #f1e9dd;
}
.student-work small {
  color: #9a7133;
}
.student-work p {
  white-space: pre-wrap;
}
.review > article {
  margin-top: 14px;
  padding: 13px;
  border: 1px solid #dfd3c4;
}
.review > article header {
  display: flex;
  justify-content: space-between;
}
.review > article header div {
  display: grid;
}
.review > article header span {
  color: #957d5a;
  font-size: 9px;
}
.review > article header b {
  color: #7f211d;
}
.review > article input[type="range"] {
  padding: 0;
  border: 0;
  box-shadow: none;
}
.review > article textarea {
  min-height: 70px;
}
.review > footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 20px;
  padding-top: 15px;
  border-top: 1px solid #ded2c3;
}
.review > footer strong {
  color: #7f211d;
  font:
    700 28px Georgia,
    serif;
}
.review > footer button {
  padding: 11px 18px;
}
/* #ifndef H5 */
@media (max-width: 720px) {
  .workbench-hero {
    align-items: flex-start;
    padding: 25px 18px;
  }
  .hero-actions {
    display: grid;
  }
  .workbench-hero h1 {
    font-size: 28px;
  }
  .workbench-hero p {
    display: none;
  }
  .workbench-layout {
    grid-template-columns: 1fr;
    margin: 12px;
  }
  .task-list {
    border-right: 0;
    border-bottom: 1px solid #d8ccbc;
    max-height: 240px;
    overflow: auto;
  }
  .task-console {
    padding: 18px 13px;
  }
  .task-console > header {
    display: block;
  }
  .task-console > header > div:last-child {
    margin-top: 12px;
  }
  .metrics {
    grid-template-columns: repeat(2, 1fr);
  }
  .rubric-editor article {
    grid-template-columns: 1fr 70px;
  }
  .creator,
  .review {
    padding: 19px 14px;
  }
}
/* #endif */
/* #ifdef H5 */
@container (max-width: 720px) {
  .workbench-hero {
    align-items: flex-start;
    padding: 25px 18px;
  }
  .hero-actions {
    display: grid;
  }
  .workbench-hero h1 {
    font-size: 28px;
  }
  .workbench-hero p {
    display: none;
  }
  .workbench-layout {
    grid-template-columns: 1fr;
    margin: 12px;
  }
  .task-list {
    border-right: 0;
    border-bottom: 1px solid #d8ccbc;
    max-height: 240px;
    overflow: auto;
  }
  .task-console {
    padding: 18px 13px;
  }
  .task-console > header {
    display: block;
  }
  .task-console > header > div:last-child {
    margin-top: 12px;
  }
  .metrics {
    grid-template-columns: repeat(2, 1fr);
  }
  .rubric-editor article {
    grid-template-columns: 1fr 70px;
  }
  .creator,
  .review {
    padding: 19px 14px;
  }
}
/* #endif */
</style>
