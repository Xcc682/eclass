<template>
  <div class="manage-page">
    <header class="page-header">
      <div>
        <span class="eyebrow">CONTENT DESK</span>
        <h1>知识资料管理</h1>
        <p>从上传、审核到维护，每一份资料都有清晰状态，也能随时修正。</p>
      </div>
      <div class="header-actions">
        <span class="document-count"
          >当前 {{ visibleDocuments.length }} 份</span
        >
        <button class="refresh-button" :disabled="loading" @click="load">
          {{ loading ? "正在刷新" : "刷新列表" }}
        </button>
      </div>
    </header>

    <section class="workflow-strip">
      <div><b>01</b><span>上传原始文件</span></div>
      <div><b>02</b><span>解析并审核</span></div>
      <div><b>03</b><span>编辑与维护</span></div>
    </section>

    <section class="upload-card">
      <div class="section-heading">
        <div>
          <span>新资料</span>
          <h2>上传并进入审核</h2>
        </div>
        <small>上传完成后保留分类和来源，方便连续整理同一批资料。</small>
      </div>

      <div class="upload-layout">
        <div
          class="file-pick"
          :class="{ 'file-pick--selected': selectedName }"
          @click="chooseFile"
        >
          <div class="file-pick__number">01</div>
          <div class="file-pick__content">
            <b>{{ selectedName || "选择 PDF / DOCX / TXT / Markdown" }}</b>
            <small v-if="selectedName"
              >{{ formatFileSize(selectedSize) }} · 再次点击可更换文件</small
            >
            <small v-else>单个文件不超过 20MB，扫描版 PDF 暂不支持</small>
          </div>
          <button
            v-if="selectedName && !uploading"
            class="remove-file"
            @click.stop="clearSelection"
          >
            移除
          </button>
        </div>

        <div class="form-grid">
          <label
            ><span>资料标题 <i>必填</i></span
            ><input
              v-model="form.title"
              placeholder="选择文件后自动填充，也可修改"
          /></label>
          <label
            ><span>分类 <i>必填</i></span
            ><input v-model="form.category" placeholder="例如：党史、党章党规"
          /></label>
          <label
            ><span>权威来源 <i>必填</i></span
            ><input v-model="form.source" placeholder="例如：中国政府网"
          /></label>
          <label
            ><span>来源链接</span
            ><input v-model="form.source_url" placeholder="原始发布页面，可选"
          /></label>
        </div>
      </div>

      <button class="submit" :disabled="!canSubmit" @click="submit">
        {{ uploading ? uploadButtonText : "上传并开始解析" }}
      </button>

      <div
        v-if="uploadJob"
        class="task-panel"
        :class="`task-panel--${uploadJob.status}`"
      >
        <div class="task-panel__header">
          <div>
            <b>{{ uploadJob.document_title || selectedName }}</b
            ><small>{{ jobStatusLabel(uploadJob.status) }}</small>
          </div>
          <strong>{{ uploadJob.progress }}%</strong>
        </div>
        <div class="progress">
          <i :style="{ width: `${uploadJob.progress}%` }"></i>
        </div>
        <p>{{ progressText(uploadJob.progress, uploadJob.status) }}</p>
        <p v-if="uploadJob.error" class="task-warning">{{ uploadJob.error }}</p>
        <button
          v-if="
            !uploading && ['queued', 'processing'].includes(uploadJob.status)
          "
          class="task-retry"
          @click="resumeUploadJob"
        >
          继续检查进度
        </button>
      </div>
    </section>

    <section class="library-toolbar">
      <nav class="status-tabs">
        <button
          v-for="item in statuses"
          :key="item.value"
          :class="{ active: filter === item.value }"
          @click="setFilter(item.value)"
        >
          {{ item.label }}
        </button>
      </nav>
      <input
        v-model="query"
        class="search-input"
        placeholder="搜索标题、文件名或来源"
      />
    </section>

    <div v-if="loading && !documents.length" class="empty">正在加载资料…</div>
    <div v-else-if="!visibleDocuments.length" class="empty">
      当前条件下没有资料
    </div>

    <section class="document-list">
      <article
        v-for="doc in visibleDocuments"
        :key="doc.id"
        class="document-card"
      >
        <div class="doc-main">
          <div class="doc-main__top">
            <span :class="['status', doc.status]">{{
              statusLabel(doc.status)
            }}</span>
            <span class="version">第 {{ doc.version || 1 }} 版</span>
            <span v-if="doc.file_name" class="file-name">{{
              doc.file_name
            }}</span>
          </div>
          <h2>{{ doc.title }}</h2>
          <p v-if="doc.summary" class="summary">{{ doc.summary }}</p>
          <div class="doc-meta">
            <span><b>分类</b>{{ doc.category || "未分类" }}</span>
            <span><b>来源</b>{{ doc.source || "待补充" }}</span>
            <span><b>索引</b>{{ doc.chunk_count }} 个片段</span>
          </div>
          <small v-if="doc.processing_error" class="document-error">{{
            doc.processing_error
          }}</small>
        </div>

        <div class="doc-actions">
          <button
            class="edit-button"
            :disabled="documentBusy(doc)"
            @click="openEditor(doc)"
          >
            编辑资料
          </button>
          <button
            v-if="doc.status === 'pending_review'"
            class="publish"
            @click="publish(doc.id)"
          >
            审核发布
          </button>
          <button
            v-if="['pending_review', 'published'].includes(doc.status)"
            @click="beginReject(doc.id)"
          >
            驳回
          </button>
          <button
            v-if="doc.status === 'rejected'"
            class="resubmit-button"
            @click="resubmit(doc.id)"
          >
            重新提交
          </button>
          <button
            v-if="doc.file_name"
            class="reindex-button"
            :disabled="documentBusy(doc)"
            @click="reindex(doc)"
          >
            {{ reindexButtonText(doc.id) }}
          </button>
          <button
            class="delete-button"
            :disabled="documentBusy(doc)"
            @click="deleteDocument(doc)"
          >
            删除
          </button>
        </div>

        <div
          v-if="reindexJobs[doc.id]"
          class="inline-task"
          :class="`inline-task--${reindexJobs[doc.id]?.status}`"
        >
          <div>
            <b>{{ jobStatusLabel(reindexJobs[doc.id]?.status || "queued") }}</b
            ><span>{{ reindexJobs[doc.id]?.progress || 0 }}%</span>
          </div>
          <div class="progress">
            <i :style="{ width: `${reindexJobs[doc.id]?.progress || 0}%` }"></i>
          </div>
          <p>
            {{
              progressText(
                reindexJobs[doc.id]?.progress || 0,
                reindexJobs[doc.id]?.status || "queued",
              )
            }}
          </p>
          <small v-if="reindexJobs[doc.id]?.error">{{
            reindexJobs[doc.id]?.error
          }}</small>
        </div>

        <div v-if="rejectingId === doc.id" class="reject-panel">
          <input
            v-model="reasons[doc.id]"
            class="reason"
            placeholder="填写驳回原因，便于后续修改"
          />
          <button @click="rejectingId = ''">取消</button>
          <button class="danger-confirm" @click="reject(doc.id)">
            确认驳回
          </button>
        </div>
      </article>
    </section>

    <div v-if="editingDocument" class="dialog-layer" @click.self="closeEditor">
      <section class="editor-dialog">
        <header>
          <div>
            <span class="eyebrow">DOCUMENT DETAILS</span>
            <h2>编辑资料信息</h2>
          </div>
          <button :disabled="savingEdit" @click="closeEditor">关闭</button>
        </header>

        <div
          v-if="duplicateTargetId === editingDocument.id"
          class="duplicate-notice"
        >
          你刚才选择的文件与这份资料相同。可以直接修正信息；如果确实要重新上传，请先删除这份资料。
        </div>

        <div class="editor-file">
          <span>原始文件</span>
          <b>{{ editingDocument.file_name || "无原始文件" }}</b>
          <small>修改资料信息不会重新解析文件，也不会改变现有索引。</small>
        </div>

        <div class="editor-grid">
          <label class="wide"
            ><span>资料标题 <i>必填</i></span
            ><input v-model="editForm.title" maxlength="500"
          /></label>
          <label
            ><span>分类 <i>必填</i></span
            ><input v-model="editForm.category" maxlength="100"
          /></label>
          <label
            ><span>版本号</span
            ><input
              v-model.number="editForm.version"
              type="number"
              min="1"
              max="9999"
          /></label>
          <label class="wide"
            ><span>权威来源 <i>必填</i></span
            ><input v-model="editForm.source" maxlength="200"
          /></label>
          <label class="wide"
            ><span>来源链接</span
            ><input
              v-model="editForm.source_url"
              maxlength="1000"
              placeholder="https://"
          /></label>
          <label class="wide"
            ><span>资料摘要</span
            ><textarea
              v-model="editForm.summary"
              maxlength="2000"
              placeholder="用于资料列表展示，可留空"
            ></textarea>
          </label>
        </div>

        <footer>
          <button
            class="delete-button"
            :disabled="savingEdit"
            @click="deleteDocument(editingDocument)"
          >
            删除这份资料
          </button>
          <div>
            <button :disabled="savingEdit" @click="closeEditor">取消</button>
            <button
              class="save-button"
              :disabled="!canSaveEdit"
              @click="saveEdit(false)"
            >
              {{ savingEdit ? "正在保存" : "保存修改" }}
            </button>
            <button
              v-if="editingDocument.status === 'rejected'"
              class="resubmit-button"
              :disabled="!canSaveEdit"
              @click="saveEdit(true)"
            >
              保存并重新提交
            </button>
          </div>
        </footer>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import {
  DuplicateKnowledgeDocumentError,
  knowledgeApi,
  type KnowledgeDocument,
  type KnowledgeDocumentUpdate,
  type KnowledgeIngestionJob,
} from "@/api/knowledge";

const MAX_FILE_SIZE = 20 * 1024 * 1024;
const ALLOWED_EXTENSIONS = ["pdf", "docx", "txt", "md"];

const documents = ref<KnowledgeDocument[]>([]);
const filter = ref("");
const query = ref("");
const loading = ref(false);
const selectedFile = ref<any>();
const selectedName = ref("");
const selectedSize = ref(0);
const uploading = ref(false);
const uploadJob = ref<KnowledgeIngestionJob | null>(null);
const reindexJobs = reactive<Record<string, KnowledgeIngestionJob | undefined>>(
  {},
);
const reasons = reactive<Record<string, string>>({});
const rejectingId = ref("");
const deletingId = ref("");
const editingDocument = ref<KnowledgeDocument | null>(null);
const duplicateTargetId = ref("");
const savingEdit = ref(false);
const form = reactive({ title: "", category: "", source: "", source_url: "" });
const editForm = reactive<KnowledgeDocumentUpdate>({
  title: "",
  category: "",
  source: "",
  source_url: "",
  summary: "",
  version: 1,
});

const statuses = [
  { value: "", label: "全部" },
  { value: "processing", label: "处理中" },
  { value: "pending_review", label: "待审核" },
  { value: "published", label: "已发布" },
  { value: "rejected", label: "已驳回" },
  { value: "failed", label: "失败" },
];

const visibleDocuments = computed(() => {
  const keyword = query.value.trim().toLowerCase();
  if (!keyword) return documents.value;
  return documents.value.filter((doc) =>
    [doc.title, doc.file_name, doc.category, doc.source].some((value) =>
      value?.toLowerCase().includes(keyword),
    ),
  );
});
const canSubmit = computed(() =>
  Boolean(
    selectedFile.value &&
    form.title.trim() &&
    form.category.trim() &&
    form.source.trim() &&
    !uploading.value,
  ),
);
const canSaveEdit = computed(() =>
  Boolean(
    editForm.title.trim() &&
    editForm.category.trim() &&
    editForm.source.trim() &&
    editForm.version >= 1 &&
    !savingEdit.value,
  ),
);
const uploadButtonText = computed(() =>
  uploadJob.value
    ? `${progressText(uploadJob.value.progress, uploadJob.value.status)} ${uploadJob.value.progress}%`
    : "正在上传",
);

async function load() {
  loading.value = true;
  try {
    documents.value = await knowledgeApi.manageDocuments(filter.value);
  } catch (event: any) {
    uni.showToast({ title: event.message || "资料加载失败", icon: "none" });
  } finally {
    loading.value = false;
  }
}

function setFilter(value: string) {
  filter.value = value;
  rejectingId.value = "";
  load();
}

function chooseFile() {
  if (uploading.value) return;
  const chooser = (uni as any).chooseFile || (uni as any).chooseMessageFile;
  if (!chooser) {
    uni.showToast({ title: "当前端不支持选取文件", icon: "none" });
    return;
  }
  chooser({
    count: 1,
    type: "file",
    extension: ALLOWED_EXTENSIONS,
    success: (result: any) => {
      const item = result.tempFiles?.[0];
      const name =
        item?.name ||
        String(item?.path || result.tempFilePaths?.[0] || "")
          .split(/[\\/]/)
          .pop() ||
        "";
      const size = Number(item?.size || item?.file?.size || 0);
      const extension = name.split(".").pop()?.toLowerCase() || "";
      if (!ALLOWED_EXTENSIONS.includes(extension)) {
        uni.showToast({
          title: "仅支持 PDF、DOCX、TXT 和 Markdown",
          icon: "none",
        });
        return;
      }
      if (size > MAX_FILE_SIZE) {
        uni.showToast({ title: "文件不能超过 20MB", icon: "none" });
        return;
      }
      selectedFile.value =
        item?.file || item?.path || result.tempFilePaths?.[0];
      selectedName.value = name;
      selectedSize.value = size;
      form.title = name.replace(/\.[^.]+$/, "");
      uploadJob.value = null;
      duplicateTargetId.value = "";
    },
  });
}

function clearSelection() {
  selectedFile.value = undefined;
  selectedName.value = "";
  selectedSize.value = 0;
  form.title = "";
  duplicateTargetId.value = "";
}

function prepareNextUpload() {
  clearSelection();
  form.source_url = "";
}

async function submit() {
  if (!canSubmit.value) {
    uni.showToast({ title: "请补齐文件、标题、分类和来源", icon: "none" });
    return;
  }
  uploading.value = true;
  let accepted = false;
  try {
    const result = await knowledgeApi.uploadDocument(selectedFile.value, {
      ...form,
      version: 1,
    });
    accepted = true;
    uploadJob.value = queuedJob(
      result.job_id,
      result.document.id,
      result.document.title,
      result.document.file_name,
    );
    const completed = await pollJob(result.job_id, (value) => {
      uploadJob.value = value;
    });
    if (completed.status === "failed")
      throw new Error(completed.error || "文档解析失败");
    uni.showToast({
      title: completed.error ? "全文索引已完成" : "解析完成，等待审核",
      icon: "success",
    });
    await load();
  } catch (event: any) {
    if (
      event instanceof DuplicateKnowledgeDocumentError ||
      event.code === "DUPLICATE_DOCUMENT"
    ) {
      await handleDuplicate(event.document, event.message);
    } else {
      uni.showToast({ title: event.message || "上传处理失败", icon: "none" });
      await load();
    }
  } finally {
    if (accepted) prepareNextUpload();
    uploading.value = false;
  }
}

async function handleDuplicate(
  document: KnowledgeDocument | undefined,
  message: string,
) {
  if (!document) {
    uni.showToast({ title: message, icon: "none" });
    return;
  }
  const open = await confirm(
    "这份文件已经上传过",
    `${message}\n\n是否直接打开已有资料进行修改？`,
  );
  if (!open) return;
  filter.value = "";
  await load();
  const current =
    documents.value.find((item) => item.id === document.id) || document;
  duplicateTargetId.value = current.id;
  openEditor(current, true);
}

async function resumeUploadJob() {
  if (!uploadJob.value) return;
  uploading.value = true;
  try {
    const completed = await pollJob(uploadJob.value.id, (value) => {
      uploadJob.value = value;
    });
    if (completed.status === "failed")
      throw new Error(completed.error || "文档解析失败");
    uni.showToast({ title: "任务已完成", icon: "success" });
    await load();
  } catch (event: any) {
    uni.showToast({ title: event.message || "进度查询失败", icon: "none" });
  } finally {
    uploading.value = false;
  }
}

async function pollJob(
  id: string,
  onUpdate: (value: KnowledgeIngestionJob) => void,
) {
  for (let count = 0; count < 180; count += 1) {
    const value = await knowledgeApi.ingestionJob(id);
    onUpdate(value);
    if (["completed", "failed"].includes(value.status)) return value;
    await delay(1000);
  }
  throw new Error("任务仍在后台处理，可稍后点击“继续检查进度”");
}

function openEditor(doc: KnowledgeDocument, keepDuplicateNotice = false) {
  if (documentBusy(doc)) return;
  editingDocument.value = doc;
  editForm.title = doc.title || "";
  editForm.category = doc.category || "";
  editForm.source = doc.source || "";
  editForm.source_url = doc.source_url || "";
  editForm.summary = doc.summary || "";
  editForm.version = doc.version || 1;
  if (!keepDuplicateNotice) duplicateTargetId.value = "";
}

function closeEditor() {
  if (savingEdit.value) return;
  editingDocument.value = null;
  duplicateTargetId.value = "";
}

async function saveEdit(andResubmit: boolean) {
  const document = editingDocument.value;
  if (!document || !canSaveEdit.value) return;
  savingEdit.value = true;
  try {
    await knowledgeApi.updateDocument(document.id, { ...editForm });
    if (andResubmit) await knowledgeApi.resubmit(document.id);
    uni.showToast({
      title: andResubmit ? "已修改并重新提交" : "资料信息已更新",
      icon: "success",
    });
    editingDocument.value = null;
    duplicateTargetId.value = "";
    await load();
  } catch (event: any) {
    uni.showToast({ title: event.message || "保存失败", icon: "none" });
  } finally {
    savingEdit.value = false;
  }
}

async function publish(id: string) {
  try {
    await knowledgeApi.publish(id);
    uni.showToast({ title: "已发布", icon: "success" });
    await load();
  } catch (event: any) {
    uni.showToast({ title: event.message || "发布失败", icon: "none" });
  }
}

function beginReject(id: string) {
  rejectingId.value = rejectingId.value === id ? "" : id;
}

async function reject(id: string) {
  const reason = (reasons[id] || "").trim();
  if (reason.length < 2) {
    uni.showToast({ title: "请填写驳回原因", icon: "none" });
    return;
  }
  try {
    await knowledgeApi.reject(id, reason);
    reasons[id] = "";
    rejectingId.value = "";
    uni.showToast({ title: "已驳回", icon: "success" });
    await load();
  } catch (event: any) {
    uni.showToast({ title: event.message || "驳回失败", icon: "none" });
  }
}

async function resubmit(id: string) {
  try {
    await knowledgeApi.resubmit(id);
    uni.showToast({ title: "已重新提交审核", icon: "success" });
    await load();
  } catch (event: any) {
    uni.showToast({ title: event.message || "重新提交失败", icon: "none" });
  }
}

async function deleteDocument(doc: KnowledgeDocument) {
  if (documentBusy(doc)) return;
  const publishedNotice =
    doc.status === "published"
      ? "删除后，学生将无法继续查看或检索这份资料。"
      : "删除后，这份资料及其索引会被永久移除。";
  if (
    !(await confirm(
      "确认删除资料",
      `${publishedNotice}\n\n“${doc.title}”删除后不可恢复。`,
    ))
  )
    return;
  deletingId.value = doc.id;
  try {
    const result = await knowledgeApi.deleteDocument(doc.id);
    if (editingDocument.value?.id === doc.id) editingDocument.value = null;
    delete reindexJobs[doc.id];
    delete reasons[doc.id];
    duplicateTargetId.value = "";
    uni.showToast({
      title: result.warnings?.length
        ? "资料已删除，部分清理需检查"
        : "资料已删除",
      icon: result.warnings?.length ? "none" : "success",
    });
    await load();
  } catch (event: any) {
    uni.showToast({ title: event.message || "删除失败", icon: "none" });
  } finally {
    deletingId.value = "";
  }
}

async function reindex(doc: KnowledgeDocument) {
  if (documentBusy(doc)) return;
  const message =
    doc.status === "published"
      ? "将重新解析原文件并更新全文与向量索引。重建期间资料仍可访问，发布状态不会改变。"
      : "将重新解析原文件并更新全文与向量索引，不会改变当前审核状态。";
  if (!(await confirm("确认重建索引", message))) return;
  try {
    const result = await knowledgeApi.reindex(doc.id);
    reindexJobs[doc.id] = queuedJob(
      result.job_id,
      doc.id,
      doc.title,
      doc.file_name,
    );
    const completed = await pollJob(result.job_id, (value) => {
      reindexJobs[doc.id] = value;
    });
    if (completed.status === "failed")
      throw new Error(
        completed.error || "索引重建失败，资料状态已保留，可稍后重试",
      );
    uni.showToast({
      title: completed.error ? "全文索引已更新" : "索引重建完成",
      icon: "success",
    });
    await load();
  } catch (event: any) {
    uni.showToast({ title: event.message || "索引重建失败", icon: "none" });
    await load();
  }
}

function confirm(title: string, content: string): Promise<boolean> {
  return new Promise((resolve) =>
    uni.showModal({
      title,
      content,
      success: (result) => resolve(Boolean(result.confirm)),
      fail: () => resolve(false),
    }),
  );
}

function queuedJob(
  id: string,
  documentId: string,
  title: string,
  fileName?: string,
): KnowledgeIngestionJob {
  return {
    id,
    document_id: documentId,
    document_title: title,
    file_name: fileName,
    status: "queued",
    progress: 0,
  };
}

function isReindexing(id: string) {
  return ["queued", "processing"].includes(reindexJobs[id]?.status || "");
}
function documentBusy(doc: KnowledgeDocument) {
  return (
    doc.status === "processing" ||
    isReindexing(doc.id) ||
    deletingId.value === doc.id ||
    (savingEdit.value && editingDocument.value?.id === doc.id)
  );
}
function reindexButtonText(id: string) {
  return isReindexing(id)
    ? `重建中 ${reindexJobs[id]?.progress || 0}%`
    : reindexJobs[id]?.status === "completed"
      ? "再次重建"
      : "重建索引";
}
function delay(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
function formatFileSize(size: number) {
  return size
    ? size < 1024 * 1024
      ? `${(size / 1024).toFixed(1)} KB`
      : `${(size / 1024 / 1024).toFixed(1)} MB`
    : "大小未知";
}
function statusLabel(value: string) {
  return (
    (
      {
        processing: "处理中",
        pending_review: "待审核",
        published: "已发布",
        rejected: "已驳回",
        failed: "失败",
      } as Record<string, string>
    )[value] || value
  );
}
function jobStatusLabel(value: string) {
  return (
    (
      {
        queued: "等待处理",
        processing: "正在建立索引",
        completed: "处理完成",
        failed: "处理失败",
      } as Record<string, string>
    )[value] || value
  );
}
function progressText(progress: number, status: string) {
  if (status === "failed") return "处理失败";
  if (status === "completed") return "索引已经更新";
  if (progress < 10) return "正在排队";
  if (progress < 35) return "正在读取原文件";
  if (progress < 70) return "正在解析并切分内容";
  if (progress < 90) return "正在更新全文索引";
  return "正在更新向量索引";
}

onMounted(load);
</script>

<style scoped>
.manage-page {
  --ink: #2d2924;
  --muted: #7d7165;
  --paper: #fffdf8;
  --line: #dfd2bf;
  --red: #83201b;
  --green: #2f6548;
  min-height: 100vh;
  background: linear-gradient(180deg, #e9e0d2 0, #f3eee6 480rpx, #efe9de 100%);
  padding: 34rpx 28rpx 100rpx;
  color: var(--ink);
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 24rpx;
  max-width: 1000px;
  margin: auto;
}
.eyebrow {
  font-size: 18rpx;
  letter-spacing: 5rpx;
  color: #8d211b;
}
.page-header h1 {
  font-family: "STSong", "SimSun", serif;
  font-size: var(--page-title-size);
  margin: 8rpx 0;
}
.page-header p {
  color: #6f6459;
  font-size: 22rpx;
}
.header-actions {
  display: flex;
  align-items: center;
  gap: 16rpx;
}
.document-count {
  font-size: 19rpx;
  color: #7f7163;
  white-space: nowrap;
}
.manage-page button {
  border: 1rpx solid #cdbfae;
  background: #fff9ef;
  border-radius: 9rpx;
  padding: 14rpx 22rpx;
  color: #3c342c;
  line-height: 1.35;
}
.manage-page button:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}
.refresh-button {
  white-space: nowrap;
}
.workflow-strip {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  max-width: 960px;
  margin: 28rpx auto 0;
  border-top: 1rpx solid #bda98c;
  border-bottom: 1rpx solid #bda98c;
}
.workflow-strip div {
  display: flex;
  align-items: center;
  gap: 14rpx;
  padding: 16rpx 24rpx;
  border-right: 1rpx solid #cdbda8;
}
.workflow-strip div:last-child {
  border-right: 0;
}
.workflow-strip b {
  font-family: Georgia, serif;
  color: #8d211b;
}
.workflow-strip span {
  font-size: 20rpx;
  color: #6f6256;
}
.upload-card,
.library-toolbar,
.document-card {
  box-sizing: border-box;
  max-width: 960px;
  margin: 22rpx auto;
  background: var(--paper);
  border: 1rpx solid var(--line);
  box-shadow: 0 12rpx 36rpx rgba(76, 56, 35, 0.05);
}
.upload-card {
  padding: 30rpx;
  border-radius: 18rpx;
}
.section-heading {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 24rpx;
  margin-bottom: 22rpx;
}
.section-heading span {
  font-size: 18rpx;
  letter-spacing: 3rpx;
  color: #8d211b;
}
.section-heading h2 {
  margin: 6rpx 0 0;
  font-family: "STSong", "SimSun", serif;
  font-size: 32rpx;
}
.section-heading small {
  max-width: 460rpx;
  color: #8e8172;
  line-height: 1.6;
}
.upload-layout {
  display: grid;
  grid-template-columns: 0.8fr 1.2fr;
  gap: 22rpx;
}
.file-pick {
  display: flex;
  align-items: center;
  gap: 18rpx;
  min-height: 146rpx;
  border: 2rpx dashed #bca98e;
  padding: 24rpx;
  background: #f8f1e7;
  cursor: pointer;
  transition: 0.2s ease;
  box-sizing: border-box;
}
.file-pick:hover {
  border-color: #8d211b;
}
.file-pick--selected {
  border-style: solid;
  border-color: #7f9b87;
  background: #f3f7f1;
}
.file-pick__number {
  font-family: Georgia, serif;
  font-size: 34rpx;
  color: #9b281f;
}
.file-pick__content {
  flex: 1;
  min-width: 0;
}
.file-pick b,
.file-pick small {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
}
.file-pick small {
  margin-top: 9rpx;
  color: #8e8172;
  line-height: 1.45;
}
.remove-file {
  flex: none;
  background: transparent !important;
}
.form-grid,
.editor-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16rpx;
}
.form-grid label > span,
.editor-grid label > span {
  display: block;
  margin: 0 0 8rpx 4rpx;
  font-size: 20rpx;
  color: #6f6256;
}
.form-grid label i,
.editor-grid label i {
  font-style: normal;
  color: #9b281f;
}
.form-grid input,
.editor-grid input,
.editor-grid textarea,
.reason,
.search-input {
  box-sizing: border-box;
  width: 100%;
  border: 1rpx solid transparent;
  background: #f3ece1;
  padding: 17rpx 18rpx;
  border-radius: 7rpx;
  color: var(--ink);
}
.form-grid input:focus,
.editor-grid input:focus,
.editor-grid textarea:focus,
.reason:focus,
.search-input:focus {
  border-color: #9d8264;
  background: #fffaf2;
  outline: none;
}
.submit {
  width: 100%;
  margin-top: 20rpx;
  background: var(--red) !important;
  color: #fff !important;
  border-color: var(--red) !important;
  font-weight: 600;
  letter-spacing: 2rpx;
}
.task-panel {
  margin-top: 18rpx;
  padding: 20rpx;
  background: #f4efe6;
  border-left: 6rpx solid #a58c68;
}
.task-panel--completed {
  border-left-color: #52705e;
  background: #eff4ee;
}
.task-panel--failed {
  border-left-color: #a23a32;
  background: #fff0ed;
}
.task-panel__header,
.inline-task > div:first-child {
  display: flex;
  justify-content: space-between;
  gap: 20rpx;
}
.task-panel__header b,
.task-panel__header small {
  display: block;
}
.task-panel__header small {
  margin-top: 6rpx;
  color: #7f7266;
}
.task-panel__header strong {
  color: #7f211b;
}
.progress {
  height: 10rpx;
  margin-top: 14rpx;
  background: #ded5c8;
  overflow: hidden;
  border-radius: 999rpx;
}
.progress i {
  display: block;
  height: 100%;
  background: #52705e;
  transition: width 0.35s ease;
}
.task-panel p,
.inline-task p {
  margin: 10rpx 0 0;
  font-size: 20rpx;
  color: #766b60;
}
.task-warning,
.inline-task small {
  color: #9b4a29 !important;
}
.task-retry {
  margin-top: 14rpx;
}
.library-toolbar {
  display: flex;
  align-items: center;
  gap: 16rpx;
  padding: 10rpx;
  border-radius: 12rpx;
}
.status-tabs {
  display: flex;
  flex: 1;
  min-width: 0;
  overflow-x: auto;
  scrollbar-width: thin;
}
.status-tabs button {
  flex: none;
  border: 0;
  background: transparent;
  white-space: nowrap;
}
.status-tabs .active {
  background: #342f2a;
  color: #fff;
}
.search-input {
  width: 260px;
  flex: none;
  background: #f6f0e7;
}
.document-list {
  max-width: 960px;
  margin: auto;
}
.document-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 20rpx;
  padding: 26rpx;
  border-radius: 14rpx;
  position: relative;
  overflow: hidden;
}
.document-card:before {
  content: "";
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 5rpx;
  background: #c6b79f;
}
.doc-main__top {
  display: flex;
  align-items: center;
  gap: 12rpx;
  min-width: 0;
}
.status,
.version {
  font-size: 18rpx;
  padding: 5rpx 10rpx;
  background: #eee5d9;
  color: #765;
}
.status.published {
  background: #e7f0e8;
  color: #2f6b48;
}
.status.pending_review {
  background: #fff0d9;
  color: #92520e;
}
.status.rejected,
.status.failed {
  background: #f7e4e1;
  color: #96372f;
}
.file-name {
  min-width: 0;
  max-width: 390rpx;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #978979;
  font-size: 18rpx;
}
.doc-main h2 {
  font-family: "STSong", "SimSun", serif;
  font-size: 30rpx;
  margin: 16rpx 0 10rpx;
}
.summary {
  margin: 0 0 16rpx;
  color: #75695f;
  font-size: 20rpx;
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.doc-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10rpx 24rpx;
}
.doc-meta span {
  font-size: 19rpx;
  color: #796d62;
}
.doc-meta b {
  margin-right: 8rpx;
  color: #3c342c;
}
.document-error {
  display: block;
  margin-top: 14rpx;
  color: #a23a32;
  line-height: 1.5;
}
.doc-actions {
  display: flex;
  max-width: 310rpx;
  gap: 8rpx;
  align-content: flex-start;
  justify-content: flex-end;
  flex-wrap: wrap;
}
.doc-actions button {
  padding: 12rpx 17rpx;
}
.doc-actions .publish,
.save-button {
  background: var(--green) !important;
  color: #fff !important;
  border-color: var(--green) !important;
}
.edit-button {
  border-color: #8d211b !important;
  color: #7f211b !important;
}
.resubmit-button {
  background: #6b5137 !important;
  color: #fff !important;
  border-color: #6b5137 !important;
}
.reindex-button {
  border-color: #8a765a !important;
}
.delete-button {
  color: #9b2b24 !important;
  border-color: #d6a7a1 !important;
  background: #fff8f5 !important;
}
.inline-task,
.reject-panel {
  grid-column: 1/-1;
  padding: 16rpx 18rpx;
  background: #f2ede5;
  border-radius: 8rpx;
}
.inline-task--completed {
  background: #edf4ed;
}
.inline-task--failed {
  background: #fff0ed;
}
.reject-panel {
  display: grid;
  grid-template-columns: 1fr auto auto;
  gap: 10rpx;
  background: #fbefea;
}
.danger-confirm {
  background: #9b2b24 !important;
  color: #fff !important;
  border-color: #9b2b24 !important;
}
.empty {
  max-width: 960px;
  box-sizing: border-box;
  margin: 22rpx auto;
  text-align: center;
  padding: 80rpx;
  color: #887b6e;
  border: 1rpx dashed #cdbda8;
  background: rgba(255, 253, 248, 0.55);
}
.dialog-layer {
  position: fixed;
  z-index: 100;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24rpx;
  background: rgba(35, 28, 22, 0.58);
  backdrop-filter: blur(8rpx);
}
.editor-dialog {
  width: min(760px, 94vw);
  max-height: 88vh;
  overflow: auto;
  background: #fffdf8;
  border: 1rpx solid #d5c5ae;
  box-shadow: 0 30rpx 90rpx rgba(20, 12, 7, 0.3);
}
.editor-dialog > header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 28rpx 30rpx;
  border-bottom: 1rpx solid #e5d9c9;
}
.editor-dialog h2 {
  font-family: "STSong", "SimSun", serif;
  font-size: 34rpx;
  margin: 7rpx 0 0;
}
.duplicate-notice {
  margin: 24rpx 30rpx 0;
  padding: 18rpx 20rpx;
  border-left: 6rpx solid #9b2b24;
  background: #f9ebe6;
  color: #6f443a;
  line-height: 1.6;
}
.editor-file {
  margin: 24rpx 30rpx;
  padding: 18rpx 20rpx;
  background: #f3ece1;
}
.editor-file span,
.editor-file b,
.editor-file small {
  display: block;
}
.editor-file span {
  font-size: 18rpx;
  color: #8d211b;
  letter-spacing: 2rpx;
}
.editor-file b {
  margin: 7rpx 0;
  overflow-wrap: anywhere;
}
.editor-file small {
  color: #817366;
}
.editor-grid {
  padding: 0 30rpx 28rpx;
}
.editor-grid .wide {
  grid-column: 1/-1;
}
.editor-grid textarea {
  min-height: 150rpx;
  resize: vertical;
}
.editor-dialog > footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 18rpx;
  padding: 20rpx 30rpx;
  background: #f4eee5;
  border-top: 1rpx solid #ded1bf;
}
.editor-dialog > footer > div {
  display: flex;
  justify-content: flex-end;
  gap: 10rpx;
  flex-wrap: wrap;
}
/* #ifndef H5 */
@media (max-width: 700px) {
  .page-header,
  .section-heading {
    align-items: flex-start;
    flex-direction: column;
  }
  .header-actions {
    width: 100%;
    justify-content: space-between;
  }
  .workflow-strip div {
    padding: 14rpx 12rpx;
  }
  .workflow-strip span {
    font-size: 18rpx;
  }
  .upload-layout {
    grid-template-columns: 1fr;
  }
  .library-toolbar {
    align-items: stretch;
    flex-direction: column;
  }
  .search-input {
    width: 100%;
  }
  .document-card {
    grid-template-columns: 1fr;
  }
  .doc-actions {
    max-width: none;
    justify-content: flex-start;
  }
  .file-name {
    max-width: 260rpx;
  }
  .editor-dialog > footer {
    align-items: stretch;
    flex-direction: column-reverse;
  }
  .editor-dialog > footer > button {
    width: 100%;
  }
  .editor-dialog > footer > div {
    width: 100%;
  }
  .reject-panel {
    grid-template-columns: 1fr 1fr;
  }
  .reject-panel .reason {
    grid-column: 1/-1;
  }
}
/* #endif */
/* #ifdef H5 */
@container (max-width: 700px) {
  .page-header,
  .section-heading {
    align-items: flex-start;
    flex-direction: column;
  }
  .header-actions {
    width: 100%;
    justify-content: space-between;
  }
  .workflow-strip div {
    padding: 14rpx 12rpx;
  }
  .workflow-strip span {
    font-size: 18rpx;
  }
  .upload-layout {
    grid-template-columns: 1fr;
  }
  .library-toolbar {
    align-items: stretch;
    flex-direction: column;
  }
  .search-input {
    width: 100%;
  }
  .document-card {
    grid-template-columns: 1fr;
  }
  .doc-actions {
    max-width: none;
    justify-content: flex-start;
  }
  .file-name {
    max-width: 260rpx;
  }
  .editor-dialog > footer {
    align-items: stretch;
    flex-direction: column-reverse;
  }
  .editor-dialog > footer > button {
    width: 100%;
  }
  .editor-dialog > footer > div {
    width: 100%;
  }
  .reject-panel {
    grid-template-columns: 1fr 1fr;
  }
  .reject-panel .reason {
    grid-column: 1/-1;
  }
}
/* #endif */
/* #ifndef H5 */
@media (max-width: 460px) {
  .form-grid,
  .editor-grid {
    grid-template-columns: 1fr;
  }
  .editor-grid .wide {
    grid-column: auto;
  }
  .workflow-strip span {
    display: none;
  }
  .workflow-strip div {
    justify-content: center;
  }
  .editor-dialog > footer > div button {
    flex: 1;
  }
  .doc-actions button {
    flex: 1;
    min-width: 42%;
  }
}
/* #endif */
/* #ifdef H5 */
@container (max-width: 460px) {
  .form-grid,
  .editor-grid {
    grid-template-columns: 1fr;
  }
  .editor-grid .wide {
    grid-column: auto;
  }
  .workflow-strip span {
    display: none;
  }
  .workflow-strip div {
    justify-content: center;
  }
  .editor-dialog > footer > div button {
    flex: 1;
  }
  .doc-actions button {
    flex: 1;
    min-width: 42%;
  }
}
/* #endif */
</style>
