<template>
  <div class="writer-page">
    <header>
      <span>WRITING STUDIO</span>
      <h1>思政写作台</h1>
      <p>AI 生成的是可编辑初稿，请结合本人真实经历核对修改。</p>
    </header>
    <div class="workspace">
      <aside>
        <button
          v-for="tpl in templates"
          :key="tpl.id"
          :class="{ active: selected?.id === tpl.id }"
          @click="selectTemplate(tpl)"
        >
          <b>{{ tpl.name }}</b
          ><small>{{ tpl.desc }}</small></button
        ><button class="history-button" @click="showHistory = !showHistory">
          历史记录
        </button>
      </aside>
      <main>
        <div v-if="loadError" class="load-error">
          <p>{{ loadError }}</p>
          <button @click="loadAll">重试</button>
        </div>
        <template v-else-if="!showHistory">
          <label
            >个人情况<textarea
              v-model="background"
              maxlength="3000"
              placeholder="如：专业年级、成长经历、近期学习实践。请勿填写身份证号等敏感信息。"
            />
          </label>
          <label
            >具体要求<textarea
              v-model="requirements"
              maxlength="3000"
              placeholder="篇幅、主题、希望重点表达的内容…"
            />
          </label>
          <button
            class="generate"
            :disabled="!selected || generating"
            @click="generate"
          >
            {{ generating ? "正在生成…" : "生成可编辑初稿" }}
          </button>
          <label v-if="content"
            >生成结果<textarea v-model="content" class="result" maxlength="30000" />
          </label>
          <div v-if="content" class="result-actions">
            <div>
              <button @click="copy">复制全文</button
              ><button @click="saveEdit">保存修改</button>
            </div>
            <span>{{ saved ? "修改已保存" : "内容有修改" }}</span>
          </div>
        </template>
        <template v-else
          ><article v-for="item in history" :key="item.id">
            <b>{{ item.title }}</b
            ><small>{{ formatTime(item.created_at) }}</small>
            <p>{{ item.content }}</p>
            <footer>
              <button @click="openHistory(item)">继续编辑</button
              ><button @click="removeHistory(item.id)">删除</button>
            </footer>
          </article>
          <div v-if="!history.length" class="empty">暂无生成记录</div></template
        >
      </main>
    </div>
  </div>
</template>
<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import { knowledgeApi, type KnowledgeTemplate } from "@/api/knowledge";
const templates = ref<KnowledgeTemplate[]>([]);
const selected = ref<KnowledgeTemplate>();
const background = ref("");
const requirements = ref("");
const content = ref("");
const generating = ref(false);
const showHistory = ref(false);
const history = ref<any[]>([]);
const reportId = ref("");
const saved = ref(true);
const savedContent = ref("");
const loadError = ref("");

// P0-1: 统一加载入口，失败时展示错误态 + 重试
async function loadAll() {
  loadError.value = "";
  try {
    const [tpls, hist] = await Promise.all([
      knowledgeApi.getTemplates(),
      knowledgeApi.templateHistory(),
    ]);
    templates.value = tpls || [];
    history.value = hist || [];
    if (!selected.value && templates.value.length) selected.value = templates.value[0];
  } catch (event: any) {
    loadError.value = event.message || "模板加载失败，请重试";
  }
}

function selectTemplate(tpl: KnowledgeTemplate) {
  // 切换模板时清空上一次的生成结果，并回到生成界面，避免点了模板界面却不变或卡在历史记录。
  showHistory.value = false;
  selected.value = tpl;
  content.value = "";
  reportId.value = "";
  savedContent.value = "";
  saved.value = true;
}

// P1-5: 历史刷新独立容错，不因它失败而误报生成失败
async function refreshHistory() {
  try {
    history.value = await knowledgeApi.templateHistory();
  } catch { /* 历史刷新失败不打断主流程 */ }
}

async function generate() {
  if (!selected.value) return;
  generating.value = true;
  try {
    const result = await knowledgeApi.generate(
      selected.value.id,
      requirements.value,
      background.value,
    );
    reportId.value = result.id;
    savedContent.value = result.content;
    content.value = result.content;
    saved.value = true;
  } catch (event: any) {
    uni.showToast({ title: event.message, icon: "none" });
  } finally {
    generating.value = false;
  }
  refreshHistory();
}
function copy() {
  (uni as any).setClipboardData({
    data: content.value,
    success: () => uni.showToast({ title: "已复制", icon: "success" }),
    // P1-7: 复制失败给用户明确提示（非安全上下文 clipboard 可能不可用）
    fail: () => uni.showToast({ title: "复制失败，请手动选择复制", icon: "none" }),
  });
}
async function saveEdit() {
  if (!reportId.value) return;
  try {
    await knowledgeApi.updateTemplateHistory(reportId.value, content.value);
    savedContent.value = content.value;
    saved.value = true;
    refreshHistory();
    uni.showToast({ title: "修改已保存", icon: "success" });
  } catch (event: any) {
    uni.showToast({ title: event.message || "保存失败", icon: "none" });
  }
}
function openHistory(item: any) {
  // P1-6: 按标题匹配模板，让左侧选中态与历史内容一致
  const match = templates.value.find((tpl) => tpl.name === item.title);
  if (match) selected.value = match;
  reportId.value = item.id;
  savedContent.value = item.content;
  content.value = item.content;
  showHistory.value = false;
  saved.value = true;
}
async function removeHistory(id: string) {
  const confirmed = await new Promise<boolean>((resolve) =>
    uni.showModal({
      title: "删除记录",
      content: "确定删除这份生成记录吗？",
      success: (r) => resolve(Boolean(r.confirm)),
      fail: () => resolve(false),
    }),
  );
  if (!confirmed) return;
  try {
    await knowledgeApi.deleteTemplateHistory(id);
    history.value = history.value.filter((item) => item.id !== id);
    // P1-4: 若删除的正是当前编辑记录，清空编辑状态，避免后续保存 404
    if (reportId.value === id) {
      reportId.value = "";
      content.value = "";
      savedContent.value = "";
      saved.value = true;
    }
  } catch (event: any) {
    uni.showToast({ title: event.message || "删除失败", icon: "none" });
  }
}
function formatTime(value: string) {
  // P1-8: 后端存的是无时区 UTC，补 Z 后按本地时区正确显示
  const date = new Date(value.endsWith("Z") ? value : value + "Z");
  return date.toLocaleString();
}
watch(content, (value) => {
  if (reportId.value) saved.value = value === savedContent.value;
});
watch(showHistory, (value) => {
  if (value) refreshHistory();
});
onMounted(loadAll);
</script>
<style scoped>
.writer-page {
  min-height: 100vh;
  background: #f0eadf;
  padding: 32rpx;
  color: #302b25;
}
.writer-page > header {
  max-width: 960px;
  margin: 0 auto 24rpx;
}
.writer-page > header span {
  font-size: 18rpx;
  letter-spacing: 5rpx;
  color: #8d211b;
}
.writer-page h1 {
  font-family: "STKaiti", "KaiTi", serif;
  font-size: var(--page-title-size);
  margin: 8rpx 0;
}
.writer-page header p {
  font-size: 22rpx;
  color: #786d62;
}
.workspace {
  max-width: 960px;
  margin: auto;
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr);
  background: #fffdf8;
  border: 1rpx solid #ded1be;
  min-height: 650rpx;
}
.workspace aside {
  padding: 18rpx;
  background: #36312c;
}
.workspace aside button {
  display: block;
  width: 100%;
  text-align: left;
  border: 0;
  background: transparent;
  color: #ded3c4;
  padding: 20rpx;
  border-radius: 10rpx;
}
.workspace aside b,
.workspace aside small {
  display: block;
}
.workspace aside small {
  margin-top: 6rpx;
  color: #a99d8e;
}
.workspace aside .active {
  background: #8d211b;
  color: #fff;
}
.workspace aside .active small {
  color: #f1cfc5;
}
.history-button {
  margin-top: 22rpx;
  border-top: 1rpx solid #635b53 !important;
}
.workspace main {
  padding: 30rpx;
}
.workspace label {
  display: block;
  font-size: 22rpx;
  color: #6f6357;
  margin-bottom: 22rpx;
}
.workspace textarea {
  display: block;
  width: 100%;
  box-sizing: border-box;
  min-height: 130rpx;
  margin-top: 9rpx;
  padding: 20rpx;
  background: #f3ece1;
  border-radius: 10rpx;
  font-size: 24rpx;
}
.workspace textarea.result {
  min-height: 360rpx;
  font-family: "STSong", "SimSun", serif;
  line-height: 1.8;
}
.generate {
  width: 100%;
  border: 0;
  border-radius: 10rpx;
  background: #8d211b;
  color: #fff;
  padding: 20rpx;
  margin-bottom: 24rpx;
}
.generate:disabled {
  opacity: 0.45;
}
.result-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: #887b6f;
  font-size: 20rpx;
}
.result-actions button {
  border: 1rpx solid #8d211b;
  background: #fff;
  color: #8d211b;
  padding: 12rpx 24rpx;
  border-radius: 8rpx;
}
.workspace article {
  border-bottom: 1rpx solid #e6dac9;
  padding: 18rpx 0;
}
.workspace article b,
.workspace article small {
  display: block;
}
.workspace article small {
  color: #9b8f82;
  margin: 6rpx 0;
}
.workspace article p {
  white-space: pre-wrap;
  max-height: 180rpx;
  overflow: auto;
  font-size: 22rpx;
  line-height: 1.6;
}
.empty {
  text-align: center;
  padding: 100rpx;
  color: #8b7e70;
}
.load-error {
  text-align: center;
  padding: 60rpx 20rpx;
  color: #a13a32;
}
.load-error p {
  margin: 0 0 18rpx;
  font-size: 24rpx;
}
.load-error button {
  padding: 12rpx 34rpx;
  border: 1rpx solid #8d211b;
  border-radius: 8rpx;
  color: #8d211b;
}
/* #ifndef H5 */
@media (max-width: 600px) {
  .workspace {
    grid-template-columns: 1fr;
  }
  .workspace aside {
    display: flex;
    overflow: auto;
  }
  .workspace aside button {
    min-width: 190rpx;
  }
  .history-button {
    margin: 0 !important;
    border-top: 0 !important;
  }
}
/* #endif */
/* #ifdef H5 */
@container (max-width: 600px) {
  .workspace {
    grid-template-columns: 1fr;
  }
  .workspace aside {
    display: flex;
    overflow: auto;
  }
  .workspace aside button {
    min-width: 190rpx;
  }
  .history-button {
    margin: 0 !important;
    border-top: 0 !important;
  }
}
/* #endif */
.workspace article footer,
.result-actions > div {
  display: flex;
  gap: 12rpx;
}
.workspace article footer button {
  padding: 10rpx 16rpx;
  border: 1rpx solid #d7c8b5;
  border-radius: 8rpx;
  color: #7d211b;
}
</style>
