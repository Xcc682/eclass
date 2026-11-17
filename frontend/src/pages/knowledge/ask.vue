<template>
  <div class="ask-page">
    <aside class="session-panel">
      <div class="session-panel__brand"><small>KNOWLEDGE DESK</small><strong>问答档案</strong></div>
      <button class="new-chat" :disabled="sessionLoading" @click="newChat">＋ 新建问答</button>
      <label class="session-search"><span>⌕</span><input v-model="sessionSearch" placeholder="搜索历史" @input="debouncedRefresh" /></label>
      <div class="session-panel__title"><span>最近会话</span><button :disabled="sessionsLoading" @click="refreshSessions">刷新</button></div>
      <div v-if="sessionsLoading" class="panel-state">正在整理档案…</div>
      <div v-else-if="sessionsError" class="panel-state panel-state--error">{{ sessionsError }}<button @click="refreshSessions">重试</button></div>
      <div v-else-if="!sessions.length" class="panel-state">暂无历史问答</div>
      <div v-else class="session-list">
        <section v-for="group in sessionGroups" :key="group.label">
          <small>{{ group.label }}</small>
          <div v-for="item in group.items" :key="item.id" class="session-item" :class="{active:item.id===sessionId}" @click="openSession(item.id)">
            <span>{{ item.title }}</span>
            <button aria-label="会话菜单" @click.stop="sessionActions(item)">•••</button>
          </div>
        </section>
      </div>
    </aside>

    <div v-if="drawerOpen" class="drawer-mask" @click="drawerOpen=false"></div>
    <aside class="mobile-drawer" :class="{open:drawerOpen}">
      <header><strong>问答档案</strong><button @click="drawerOpen=false">×</button></header>
      <button class="new-chat" @click="newChat();drawerOpen=false">＋ 新建问答</button>
      <label class="session-search"><span>⌕</span><input v-model="sessionSearch" placeholder="搜索历史" @input="debouncedRefresh" /></label>
      <div class="session-list">
        <section v-for="group in sessionGroups" :key="group.label">
          <small>{{ group.label }}</small>
          <div v-for="item in group.items" :key="item.id" class="session-item" :class="{active:item.id===sessionId}" @click="openSession(item.id);drawerOpen=false">
            <span>{{ item.title }}</span><button @click.stop="sessionActions(item)">•••</button>
          </div>
        </section>
      </div>
    </aside>

    <main class="reading-desk">
      <header class="desk-header">
        <button class="history-trigger" @click="drawerOpen=true">☰ <span>历史</span></button>
        <div><small>AUTHORIZED KNOWLEDGE</small><strong>依据已审核资料作答</strong></div>
        <span class="library-count">{{ libraryCount ? `${libraryCount} 份资料` : '引用可追溯' }}</span>
      </header>

      <div class="scope-bar">
        <span>检索范围</span>
        <button :class="{active:scopeMode==='all'}" @click="setScope('all')">全部资料</button>
        <button :class="{active:scopeMode==='category'}" @click="setScope('category')">指定分类</button>
        <button v-if="documentId" :class="{active:scopeMode==='document'}" @click="setScope('document')">当前资料</button>
        <div v-if="scopeMode==='category'" class="category-picker">
          <button v-for="item in categories" :key="item" :class="{active:category===item}" @click="category=item;syncRoute()">{{ item }}</button>
        </div>
        <em v-if="scopeMode==='document'">《{{ documentTitle || '当前资料' }}》</em>
      </div>

      <div ref="messagesEl" class="messages">
        <div v-if="sessionLoading" class="page-state">正在打开历史问答…</div>
        <div v-else-if="sessionError" class="page-state page-state--error">{{ sessionError }}<button @click="sessionId&&openSession(sessionId)">重新打开</button></div>
        <section v-else-if="!messages.length" class="welcome">
          <div class="welcome__seal">问</div>
          <small>从权威资料中寻找答案</small>
          <h1>今天想查证什么？</h1>
          <p>回答会标明原文依据；资料不足时不会凭空补充。</p>
          <div class="suggestion-grid">
            <button @click="send('红船精神的核心内涵是什么？')"><span>01</span>红船精神的核心内涵是什么？</button>
            <button @click="send('入党申请书应包含哪些内容？')"><span>02</span>入党申请书应包含哪些内容？</button>
          </div>
        </section>

        <article v-for="message in messages" :id="`message-${message.id}`" :key="message.id" class="message" :class="[message.role,message.status]">
          <div v-if="message.role==='user'" class="user-row">
            <div class="user-bubble">{{ message.content }}</div>
            <div v-if="message.status==='failed'" class="message-error">
              <span>{{ message.error || '发送失败，请重试' }}</span>
              <button @click="retryMessage(message)">重新发送</button>
            </div>
          </div>

          <div v-else class="answer-sheet">
            <div class="answer-sheet__label"><span>{{ answerLabel(message.response_kind) }}</span><small v-if="message.degraded">已使用降级检索</small></div>
            <div v-if="message.citations?.length" class="citation-legend">方括号为原文依据编号，点击可查看对应资料</div>
            <template v-if="message.answer_blocks?.length">
              <div v-for="(block,index) in message.answer_blocks" :key="index" class="answer-block" :class="`answer-block--${block.type}`">
                <strong v-if="block.type==='heading'">{{ block.text }}</strong>
                <template v-else><span v-if="block.type==='list_item'" class="list-dot">◆</span><p>{{ block.text }}</p></template>
                <button v-for="citationIndex in sortedBlockCitations(block.citations)" :key="citationIndex" class="inline-citation" @click="openCitationByIndex(message,citationIndex)">[{{ citationIndex }}]</button>
              </div>
            </template>
            <p v-else class="answer-fallback">{{ message.content }}</p>

            <div v-if="message.citations?.length" class="evidence">
              <button class="evidence__toggle" @click="toggleEvidence(message.id)">
                <span>依据 {{ groupedCitations(message).length }} 份资料</span><b>{{ evidenceOpen[message.id] ? '收起' : '展开查看' }} {{ evidenceOpen[message.id] ? '↑' : '↓' }}</b>
              </button>
              <div v-if="evidenceOpen[message.id]" class="evidence__list">
                <section v-for="group in groupedCitations(message)" :key="group.document_id">
                  <header><strong>{{ group.document_title }}</strong><small>{{ group.source }}</small></header>
                  <button v-for="citation in group.items" :key="citation.chunk_id" @click="openCitation(message,citation)">
                    <b>[{{ citation.index }}]</b><span>{{ citation.excerpt }}</span><em>第 {{ citation.chunk_index+1 }} 段 →</em>
                  </button>
                </section>
              </div>
            </div>

            <footer class="answer-actions">
              <button @click="copyAnswer(message)">复制回答</button>
              <span></span>
              <button :class="{selected:message.feedback==='helpful'}" @click="rateAnswer(message,true)">有帮助</button>
              <button :class="{selected:message.feedback==='unhelpful'}" @click="rateAnswer(message,false)">需改进</button>
            </footer>
            <div v-if="message.follow_up_suggestions?.length" class="follow-ups">
              <small>继续追问</small>
              <button v-for="item in message.follow_up_suggestions" :key="item" @click="send(item)">{{ item }} →</button>
            </div>
            <div v-if="message.response_kind==='no_evidence'" class="no-evidence-actions">
              <button @click="focusInput">换一种问法</button><button @click="goLibrary">搜索资料库</button>
            </div>
          </div>
        </article>

        <div v-if="asking" class="thinking"><i></i><span>正在查找依据并组织回答…</span><button @click="leavePending">稍后查看</button></div>
        <div id="message-end"></div>
      </div>

      <footer class="composer">
        <div class="composer__main">
          <div v-if="images.length" class="image-chips">
            <figure v-for="(image, index) in images" :key="index" class="image-chip">
              <img :src="image" alt="待发送图片" />
              <button type="button" title="移除图片" @click="images.splice(index, 1)">×</button>
            </figure>
          </div>
          <textarea ref="inputEl" v-model="question" maxlength="1000" placeholder="请输入问题；Enter 发送，Shift+Enter 换行" :disabled="sessionLoading" @keydown.enter.exact.prevent="send()" />
        </div>
        <div class="composer__side">
          <button type="button" class="composer__attach" :disabled="images.length>=2||sessionLoading" @click="pickImage">＋图片</button>
          <small>{{ question.length }}/1000</small>
          <button :disabled="asking||sessionLoading||!question.trim()" @click="send()">{{ asking ? '等待中' : '发送' }}</button>
        </div>
        <input ref="fileEl" type="file" accept="image/png,image/jpeg,image/webp" hidden @change="onPickImages" />
      </footer>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { onHide, onLoad, onUnload } from "@dcloudio/uni-app";
import {
  knowledgeApi,
  type Citation,
  type KnowledgeMessage,
  type KnowledgeSession,
} from "@/api/knowledge";

type ViewMessage = KnowledgeMessage & { degraded?: boolean };
const route = useRoute(),
  router = useRouter();
const sessions = ref<KnowledgeSession[]>([]),
  messages = ref<ViewMessage[]>([]),
  question = ref(""),
  sessionId = ref<string>();
const asking = ref(false),
  sessionsLoading = ref(false),
  sessionLoading = ref(false),
  sessionsError = ref(""),
  sessionError = ref("");
const sessionSearch = ref(""),
  drawerOpen = ref(false),
  evidenceOpen = ref<Record<string, boolean>>({});
const scopeMode = ref<"all" | "category" | "document">("all"),
  category = ref("党史"),
  documentId = ref(""),
  documentTitle = ref("");
const libraryCount = ref(0),
  messagesEl = ref<HTMLElement>(),
  fileEl = ref<HTMLInputElement | null>(null),
  images = ref<string[]>([]),
  inputEl = ref<any>();
const categories = ["党史", "党章党规", "时政", "思政课程", "重要讲话"];
let alive = true,
  requestToken = 0,
  searchTimer: any,
  initialSessionId = "",
  initialMessageId = "";

function uid() {
  return `qa-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}
function answerLabel(kind?: string) {
  if (kind === "assistant_intro") return "助手说明";
  if (kind === "personalized") return "学习档案回答";
  if (kind === "multimodal") return "图片解读";
  return "知识库回答";
}
const IMAGE_MAX_BYTES = 4 * 1024 * 1024;
function pickImage() {
  fileEl.value?.click();
}
function onPickImages(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = "";
  if (!file || images.value.length >= 2) return;
  if (!/^image\/(png|jpeg|webp)$/.test(file.type)) {
    uni.showToast({ title: "仅支持 PNG/JPEG/WebP 图片", icon: "none" });
    return;
  }
  if (file.size > IMAGE_MAX_BYTES) {
    uni.showToast({ title: "图片不得超过 4MB", icon: "none" });
    return;
  }
  const reader = new FileReader();
  reader.onload = () => {
    if (typeof reader.result === "string") images.value.push(reader.result);
  };
  reader.readAsDataURL(file);
}
function isCurrent(token: number) {
  return alive && token === requestToken;
}
function queryText(value: unknown) {
  return Array.isArray(value) ? String(value[0] || "") : String(value || "");
}
function askQuery(messageId = "") {
  const query: Record<string, string> = {};
  if (sessionId.value) query.sessionId = sessionId.value;
  if (messageId) query.messageId = messageId;
  if (scopeMode.value !== "all") query.scope = scopeMode.value;
  if (scopeMode.value === "category") query.category = category.value;
  if (documentId.value) {
    query.documentId = documentId.value;
    if (documentTitle.value) query.documentTitle = documentTitle.value;
  }
  return query;
}
async function syncRoute(messageId = "") {
  await router.replace({
    path: "/pages/knowledge/ask",
    query: askQuery(messageId),
  });
}
function dateLabel(value: string) {
  const d = new Date(value),
    now = new Date(),
    days = Math.floor(
      (new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime() -
        new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime()) /
        86400000,
    );
  return days === 0
    ? "今天"
    : days === 1
      ? "昨天"
      : days < 7
        ? "近 7 天"
        : "更早";
}
const sessionGroups = computed(() => {
  const order = ["今天", "昨天", "近 7 天", "更早"];
  return order
    .map((label) => ({
      label,
      items: sessions.value.filter(
        (item) => dateLabel(item.updated_at) === label,
      ),
    }))
    .filter((group) => group.items.length);
});
function debouncedRefresh() {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(refreshSessions, 260);
}
async function refreshSessions() {
  sessionsLoading.value = true;
  sessionsError.value = "";
  try {
    sessions.value = await knowledgeApi.sessions(sessionSearch.value);
  } catch (e: any) {
    sessionsError.value = e.message || "问答历史暂时加载失败";
  } finally {
    sessionsLoading.value = false;
  }
}
function newChat() {
  requestToken++;
  asking.value = false;
  sessionId.value = undefined;
  messages.value = [];
  sessionError.value = "";
  evidenceOpen.value = {};
  void syncRoute();
  scrollBottom();
}
function showConfirm(title: string, content: string, options: any = {}) {
  return new Promise<any>((resolve) =>
    uni.showModal({
      title,
      content,
      ...options,
      success: resolve,
      fail: () => resolve({ confirm: false }),
    }),
  );
}
function chooseSessionAction() {
  return new Promise<number>((resolve) =>
    uni.showActionSheet({
      itemList: ["修改标题", "删除会话"],
      success: (result) => resolve(result.tapIndex),
      fail: () => resolve(-1),
    }),
  );
}
async function sessionActions(item: KnowledgeSession) {
  const action = await chooseSessionAction();
  if (action === 0) {
    const edit = await showConfirm("修改标题", item.title, {
      editable: true,
      placeholderText: "输入新标题",
    });
    const title = (edit.content || "").trim();
    if (edit.confirm && title) {
      try {
        await knowledgeApi.updateSession(item.id, title);
        item.title = title;
      } catch (e: any) {
        uni.showToast({ title: e.message || "修改失败", icon: "none" });
      }
    }
  } else if (action === 1) {
    const del = await showConfirm("删除会话", "删除后不可恢复，确定继续吗？", {
      confirmText: "删除",
      confirmColor: "#8d211b",
    });
    if (del.confirm) await deleteSession(item);
  }
}
async function deleteSession(item: KnowledgeSession) {
  try {
    await knowledgeApi.deleteSession(item.id);
    sessions.value = sessions.value.filter((x) => x.id !== item.id);
    if (sessionId.value === item.id) newChat();
    uni.showToast({ title: "已删除", icon: "success" });
  } catch (e: any) {
    uni.showToast({ title: e.message || "删除失败", icon: "none" });
  }
}
async function openSession(id: string, messageId = "") {
  requestToken++;
  asking.value = false;
  sessionLoading.value = true;
  sessionError.value = "";
  try {
    const data = await knowledgeApi.session(id);
    if (!alive) return;
    sessionId.value = id;
    messages.value = (data.messages || []) as ViewMessage[];
    if (messageId)
      evidenceOpen.value = { ...evidenceOpen.value, [messageId]: true };
    await syncRoute(messageId);
    await scrollToMessage(messageId);
  } catch (e: any) {
    const missing = /会话不存在|404/.test(e.message || "");
    if (missing) {
      sessionId.value = undefined;
      messages.value = [];
      sessionError.value = "原问答会话已不存在，你可以开始新的问答。";
      await syncRoute();
    } else sessionError.value = e.message || "历史问答暂时无法打开";
  } finally {
    sessionLoading.value = false;
  }
}
function setScope(value: "all" | "category" | "document") {
  scopeMode.value = value;
  void syncRoute();
}
function scopeOptions(submission_id: string) {
  return {
    session_id: sessionId.value,
    submission_id,
    category: scopeMode.value === "category" ? category.value : undefined,
    document_ids:
      scopeMode.value === "document" && documentId.value
        ? [documentId.value]
        : undefined,
  };
}
async function send(preset?: string, existing?: ViewMessage) {
  const value = (preset ?? existing?.content ?? question.value).trim();
  if (!value || asking.value || sessionLoading.value) return;
  const submissionId = existing?.submission_id || uid(),
    token = ++requestToken,
    attached = existing ? [] : images.value.slice();
  if (attached.length) images.value = [];
  let userMessage = existing;
  if (!userMessage) {
    userMessage = {
      id: `local-${submissionId}`,
      role: "user",
      content: value,
      citations: [],
      created_at: new Date().toISOString(),
      submission_id: submissionId,
      status: "pending",
    };
    messages.value.push(userMessage);
    question.value = "";
  } else {
    userMessage.status = "pending";
    userMessage.error = "";
  }
  asking.value = true;
  sessionError.value = "";
  await scrollBottom();
  try {
    const result = await knowledgeApi.ask(value, {
      ...scopeOptions(submissionId),
      images: attached.length ? attached : undefined,
    });
    if (!isCurrent(token)) return;
    sessionId.value = result.session_id;
    userMessage.status = "sent";
    messages.value.push({
      id: result.message_id,
      role: "assistant",
      content: result.answer,
      citations: result.citations,
      answer_blocks: result.answer_blocks,
      follow_up_suggestions: result.follow_up_suggestions,
      response_kind: result.response_kind,
      selected_tool: result.selected_tool,
      submission_id: result.submission_id,
      status: "sent",
      created_at: new Date().toISOString(),
      degraded: result.degraded,
    });
    await syncRoute(result.message_id);
    refreshSessions();
    await scrollBottom();
  } catch (e: any) {
    if (!isCurrent(token)) return;
    userMessage.status = "failed";
    userMessage.error = e.message || "发送失败，请稍后重试";
  } finally {
    if (isCurrent(token)) asking.value = false;
  }
}
function retryMessage(message: ViewMessage) {
  send(undefined, message);
}
function leavePending() {
  requestToken++;
  asking.value = false;
  uni.showToast({ title: "回答完成后可在历史中查看", icon: "none" });
  refreshSessions();
}
function sortedBlockCitations(values: number[] = []) {
  return [
    ...new Set(values.filter((value) => Number.isInteger(value) && value > 0)),
  ].sort((a, b) => a - b);
}
function groupedCitations(message: ViewMessage) {
  const groups: any[] = [];
  for (const item of [...(message.citations || [])].sort(
    (a, b) => a.index - b.index,
  )) {
    let group = groups.find((x) => x.document_id === item.document_id);
    if (!group) {
      group = {
        document_id: item.document_id,
        document_title: item.document_title,
        source: item.source,
        items: [],
      };
      groups.push(group);
    }
    if (!group.items.some((entry: Citation) => entry.index === item.index))
      group.items.push(item);
  }
  return groups;
}
function toggleEvidence(id: string) {
  evidenceOpen.value = { ...evidenceOpen.value, [id]: !evidenceOpen.value[id] };
}
async function openCitation(message: ViewMessage, citation: Citation) {
  await syncRoute(message.id);
  uni.navigateTo({
    url: `/pages/knowledge/document?id=${citation.document_id}&chunk=${citation.chunk_index}&from=ask&sessionId=${encodeURIComponent(sessionId.value || "")}&messageId=${encodeURIComponent(message.id)}`,
  });
}
function openCitationByIndex(message: ViewMessage, index: number) {
  const citation = message.citations?.find((item) => item.index === index);
  if (citation) void openCitation(message, citation);
}
function copyAnswer(message: ViewMessage) {
  (uni as any).setClipboardData({
    data: message.content,
    success: () => uni.showToast({ title: "回答已复制", icon: "success" }),
  });
}
async function rateAnswer(message: ViewMessage, helpful: boolean) {
  if (!message.id || message.id.startsWith("local-")) return;
  try {
    const data = await knowledgeApi.feedback(message.id, helpful);
    message.feedback = data.feedback;
    uni.showToast({ title: "感谢反馈", icon: "none" });
  } catch (e: any) {
    uni.showToast({ title: e.message || "反馈失败", icon: "none" });
  }
}
function focusInput() {
  inputEl.value?.focus?.();
}
function goLibrary() {
  uni.navigateTo({ url: "/pages/knowledge/knowledge" });
}
async function scrollBottom() {
  await nextTick();
  const el = messagesEl.value;
  if (el) el.scrollTop = el.scrollHeight;
}
async function scrollToMessage(messageId = "") {
  await nextTick();
  const el = messagesEl.value;
  if (!el) return;
  if (!messageId) {
    el.scrollTop = el.scrollHeight;
    return;
  }
  const target = document.getElementById(`message-${messageId}`);
  if (target && el.contains(target))
    el.scrollTop = Math.max(0, target.offsetTop - 24);
  else el.scrollTop = el.scrollHeight;
}

onLoad((query: any) => {
  initialSessionId = queryText(query?.sessionId);
  initialMessageId = queryText(query?.messageId);
  const scope = queryText(query?.scope);
  if (scope === "category" || scope === "document") scopeMode.value = scope;
  if (query?.category) category.value = queryText(query.category);
  if (query?.documentId) {
    documentId.value = queryText(query.documentId);
    documentTitle.value = queryText(query.documentTitle);
    if (!scope) scopeMode.value = "document";
  }
});
onMounted(async () => {
  if (!initialSessionId) initialSessionId = queryText(route.query.sessionId);
  if (!initialMessageId) initialMessageId = queryText(route.query.messageId);
  await Promise.all([
    refreshSessions(),
    knowledgeApi
      .status()
      .then((data) => {
        libraryCount.value = data.published_documents;
      })
      .catch(() => {}),
  ]);
  if (initialSessionId) await openSession(initialSessionId, initialMessageId);
});
onHide(() => {
  requestToken++;
  asking.value = false;
});
onUnload(() => {
  alive = false;
  requestToken++;
});
onUnmounted(() => {
  alive = false;
  clearTimeout(searchTimer);
  requestToken++;
});
</script>

<style scoped>
.ask-page{height:100%;min-height:0;display:grid;grid-template-columns:292px minmax(0,1fr);overflow:hidden;background:#e8e0d4;color:#302821}.session-panel,.mobile-drawer{display:flex;flex-direction:column;min-height:0;padding:26px 18px;background:#302a25;color:#eee4d5}.session-panel__brand{display:grid;gap:3px;margin-bottom:20px}.session-panel__brand small{font:11px Georgia,serif;letter-spacing:2px;color:#bfa66d}.session-panel__brand strong{font:700 24px var(--font-display)}.new-chat{width:100%;padding:12px;border:1px solid #887b6a;background:transparent;color:#fff;font-weight:700}.new-chat:disabled{opacity:.45}.session-search{display:flex;align-items:center;gap:7px;margin-top:14px;padding:0 10px;border-bottom:1px solid rgba(255,255,255,.14)}.session-search input{height:38px;padding:0;border:0;background:transparent;color:#fff;box-shadow:none;font-size:13px}.session-search span{color:#c7b99f}.session-panel__title{display:flex;justify-content:space-between;margin:22px 4px 10px;color:#aa9d8a;font-size:12px}.session-panel__title button,.panel-state button{color:#e2c77f}.session-list{min-height:0;overflow:auto}.session-list section>small{display:block;margin:17px 7px 6px;color:#8f8374;font:10px Georgia,serif;letter-spacing:1px}.session-item{display:flex;align-items:center;gap:5px;padding:10px 9px;color:#ddd2c2;cursor:pointer}.session-item span{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:13px}.session-item button{color:#948879;letter-spacing:1px}.session-item.active{background:rgba(226,199,127,.12);color:#fff;border-left:2px solid #dfc374}.panel-state{display:grid;gap:9px;padding:25px 7px;color:#aa9d8a;font-size:13px}.panel-state--error{color:#efb4aa}.reading-desk{min-width:0;min-height:0;display:grid;grid-template-rows:auto auto minmax(0,1fr) auto;background:#f6f1e8}.desk-header{display:flex;align-items:center;justify-content:space-between;padding:17px 28px;border-bottom:1px solid #ddd2c2;background:#fffaf1}.desk-header>div{display:grid;gap:2px}.desk-header small{font:10px Georgia,serif;letter-spacing:2px;color:#a47731}.desk-header strong{font:700 18px var(--font-display)}.library-count{font-size:12px;color:#7c2a24}.history-trigger{display:none}.scope-bar{display:flex;align-items:center;gap:7px;min-height:48px;padding:0 28px;border-bottom:1px solid #e2d8ca;background:#f1eadf;font-size:12px;overflow-x:auto}.scope-bar>span{flex:none;color:#897a69}.scope-bar>button,.category-picker button{flex:none;padding:6px 10px;border:1px solid #d6c9b7;background:#faf5ec;color:#66594d}.scope-bar button.active{border-color:#762722;background:#762722;color:#fff}.scope-bar em{flex:none;color:#7a2b25;font-style:normal}.category-picker{display:flex;gap:5px}.messages{min-height:0;overflow-y:auto;overscroll-behavior:contain;scroll-behavior:smooth;padding:34px clamp(22px,5vw,72px)}.welcome{max-width:680px;margin:8vh auto 0;text-align:center}.welcome__seal{display:grid;place-items:center;width:62px;height:62px;margin:auto;border:4px double #8b3029;border-radius:50%;color:#8b3029;font:700 28px var(--font-display);transform:rotate(-5deg)}.welcome>small{display:block;margin-top:18px;color:#a7772d;letter-spacing:3px}.welcome h1{margin:8px 0;font-size:34px}.welcome p{color:#83776a}.suggestion-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:32px}.suggestion-grid button{display:flex;align-items:center;gap:13px;padding:18px;border:1px solid #ddd0bd;background:#fffaf2;text-align:left;color:#493d34}.suggestion-grid span{color:#a5752f;font:12px Georgia,serif}.message{max-width:780px;margin:0 auto 28px}.user-row{text-align:right}.user-bubble{display:inline-block;max-width:76%;padding:13px 17px;border:1px solid #8a3a33;background:#7e2c27;color:#fff;text-align:left;line-height:1.7}.message-error{display:flex;justify-content:flex-end;gap:9px;margin-top:7px;color:#9a332d;font-size:12px}.message-error button{color:#7a2823;text-decoration:underline}.answer-sheet{padding:25px 28px;border:1px solid #ddd1c0;background:#fffdf8;box-shadow:0 10px 28px rgba(65,45,30,.05)}.answer-sheet__label{display:flex;justify-content:space-between;margin-bottom:12px;padding-bottom:12px;border-bottom:1px solid #ede4d7;color:#7c2924}.answer-sheet__label span{font:700 13px var(--font-display);letter-spacing:2px}.answer-sheet__label small{color:#8e806f}.citation-legend{margin:0 0 15px;padding-left:10px;border-left:2px solid #b8893f;color:#8a7d6f;font-size:11px}.answer-block{position:relative;display:flex;align-items:baseline;flex-wrap:wrap;margin:0 0 12px;line-height:1.85}.answer-block p{display:inline;margin:0;font-size:15px}.answer-block--heading strong{font:700 18px var(--font-display);color:#352921}.list-dot{margin-right:9px;color:#a87930;font-size:8px}.inline-citation{margin-left:3px;color:#8b2823;font:700 11px Georgia,serif;vertical-align:super}.answer-fallback{white-space:pre-wrap;font-size:15px;line-height:1.85}.evidence{margin-top:20px;border-top:1px solid #e8ded0}.evidence__toggle{width:100%;display:flex;justify-content:space-between;padding:13px 0;color:#6f6255}.evidence__toggle b{color:#8a2c27;font-size:12px}.evidence__list{display:grid;gap:10px}.evidence__list section{border-left:3px solid #ae843b;background:#f2eadc}.evidence__list header{display:flex;justify-content:space-between;padding:11px 13px 8px}.evidence__list header strong{font-size:13px}.evidence__list header small{color:#8e806f}.evidence__list section>button{width:100%;display:grid;grid-template-columns:30px 1fr auto;gap:7px;padding:10px 13px;border-top:1px solid rgba(100,75,45,.08);text-align:left}.evidence__list section>button b{color:#872b25}.evidence__list section>button span{display:-webkit-box;overflow:hidden;-webkit-line-clamp:2;-webkit-box-orient:vertical;color:#62574d;font-size:12px;line-height:1.55}.evidence__list section>button em{color:#987337;font-size:10px;font-style:normal}.answer-actions{display:flex;align-items:center;gap:12px;margin-top:18px;padding-top:12px;border-top:1px solid #eee5d8}.answer-actions span{flex:1}.answer-actions button{color:#76695d;font-size:11px}.answer-actions button.selected{color:#7f2823;font-weight:700}.follow-ups{display:grid;gap:7px;margin-top:18px;padding:14px;background:#f4ede1}.follow-ups small{color:#9a7435;letter-spacing:2px}.follow-ups button{text-align:left;color:#51463c;font-size:13px}.no-evidence-actions{display:flex;gap:9px;margin-top:14px}.no-evidence-actions button{padding:8px 12px;border:1px solid #bcae9a;color:#7c2924}.thinking{max-width:780px;display:flex;align-items:center;gap:11px;margin:0 auto 24px;padding:15px 19px;border-left:3px solid #b78b3e;background:#eee6d8;color:#706355;font-size:13px}.thinking i{width:8px;height:8px;border-radius:50%;background:#8b2e28;animation:pulse 1.1s infinite}.thinking span{flex:1}.thinking button{color:#7d2a25}.composer{display:flex;gap:12px;box-sizing:border-box;padding:16px 28px calc(16px + env(safe-area-inset-bottom,0px));border-top:1px solid #ddd2c2;background:#fffaf1}.composer textarea{flex:1;min-height:66px;max-height:150px;resize:none}.composer__side{display:flex;flex-direction:column;justify-content:space-between;align-items:flex-end}.composer__side small{color:#a19588;font-size:10px}.composer__side button{min-width:86px;height:40px;background:#7d2924;color:#fff;font-weight:700}.composer__side button:disabled{opacity:.4}.page-state{max-width:680px;margin:60px auto;padding:22px;border:1px solid #ded1bf;background:#fffaf1;text-align:center}.page-state button{margin-left:10px;color:#832a25}.page-state--error{color:#9a332c}.mobile-drawer,.drawer-mask{display:none}@keyframes pulse{50%{opacity:.3;transform:scale(.75)}}
/* #ifndef H5 */
@media (max-width: 700px){.ask-page{grid-template-columns:1fr}.session-panel{display:none}.reading-desk{grid-template-rows:auto auto minmax(0,1fr) auto}.desk-header{padding:11px 14px}.desk-header>div{align-items:center;text-align:center}.desk-header small{display:none}.desk-header strong{font-size:15px}.history-trigger{display:block;color:#762722;font-size:12px}.library-count{font-size:10px}.scope-bar{min-height:43px;padding:0 12px}.category-picker{max-width:250px;overflow-x:auto}.messages{padding:22px 12px}.welcome{margin-top:7vh}.welcome h1{font-size:27px}.welcome p{font-size:13px}.suggestion-grid{grid-template-columns:1fr;margin-top:24px}.message{margin-bottom:20px}.user-bubble{max-width:83%;font-size:14px}.answer-sheet{padding:20px 16px}.answer-block p,.answer-fallback{font-size:14px}.evidence__list section>button{grid-template-columns:25px 1fr}.evidence__list section>button em{display:none}.composer{padding:10px 9px calc(10px + env(safe-area-inset-bottom,0px));gap:7px}.composer textarea{min-height:58px;padding:10px 12px;font-size:14px}.composer__side button{min-width:62px;height:38px}.drawer-mask{display:block;position:fixed;inset:0;z-index:1100;background:rgba(25,19,15,.5)}.mobile-drawer{display:flex;position:fixed;left:0;top:0;bottom:0;z-index:1101;width:min(82vw,320px);box-sizing:border-box;transform:translateX(-105%);transition:transform .24s ease}.mobile-drawer.open{transform:translateX(0)}.mobile-drawer header{display:flex;justify-content:space-between;margin-bottom:18px}.mobile-drawer header strong{font:700 20px var(--font-display)}.mobile-drawer header button{color:#fff;font-size:24px}}
/* #endif */
/* #ifdef H5 */
@container (max-width: 700px){.ask-page{grid-template-columns:1fr}.session-panel{display:none}.reading-desk{grid-template-rows:auto auto minmax(0,1fr) auto}.desk-header{padding:11px 14px}.desk-header>div{align-items:center;text-align:center}.desk-header small{display:none}.desk-header strong{font-size:15px}.history-trigger{display:block;color:#762722;font-size:12px}.library-count{font-size:10px}.scope-bar{min-height:43px;padding:0 12px}.category-picker{max-width:250px;overflow-x:auto}.messages{padding:22px 12px}.welcome{margin-top:7vh}.welcome h1{font-size:27px}.welcome p{font-size:13px}.suggestion-grid{grid-template-columns:1fr;margin-top:24px}.message{margin-bottom:20px}.user-bubble{max-width:83%;font-size:14px}.answer-sheet{padding:20px 16px}.answer-block p,.answer-fallback{font-size:14px}.evidence__list section>button{grid-template-columns:25px 1fr}.evidence__list section>button em{display:none}.composer{padding:10px 9px calc(10px + env(safe-area-inset-bottom,0px));gap:7px}.composer textarea{min-height:58px;padding:10px 12px;font-size:14px}.composer__side button{min-width:62px;height:38px}.drawer-mask{display:block;position:fixed;inset:0;z-index:1100;background:rgba(25,19,15,.5)}.mobile-drawer{display:flex;position:fixed;left:0;top:0;bottom:0;z-index:1101;width:min(82vw,320px);box-sizing:border-box;transform:translateX(-105%);transition:transform .24s ease}.mobile-drawer.open{transform:translateX(0)}.mobile-drawer header{display:flex;justify-content:space-between;margin-bottom:18px}.mobile-drawer header strong{font:700 20px var(--font-display)}.mobile-drawer header button{color:#fff;font-size:24px}}
/* #endif */
.answer-block{display:block}.answer-block p{display:inline}.answer-block--heading{display:flex}
/* #ifndef H5 */
@media (max-width: 700px){.mobile-drawer{top:46px}.drawer-mask{top:46px}}
/* #endif */
/* #ifdef H5 */
@container (max-width: 700px){.mobile-drawer{top:46px}.drawer-mask{top:46px}}
/* #endif */
.composer__main{flex:1;min-width:0;display:grid;gap:7px}
.composer__main textarea{width:100%;box-sizing:border-box;min-height:66px}
.image-chips{display:flex;flex-wrap:wrap;gap:8px}
.image-chip{position:relative;width:72px;height:72px;margin:0;padding:0;border:1px solid #d8cbb8;background:#fff}
.image-chip img{display:block;width:100%;height:100%;object-fit:cover}
.image-chip button{position:absolute;top:-7px;right:-7px;width:20px;height:20px;border-radius:50%;background:#7d2924;color:#fff;font-size:12px;line-height:1}
.composer__side .composer__attach{min-width:0;height:28px;padding:3px 9px;border:1px solid #d6c9b7;background:#faf5ec;color:#7d2924;font-size:12px;font-weight:400}
.composer__side .composer__attach:disabled{opacity:.4}
</style>
