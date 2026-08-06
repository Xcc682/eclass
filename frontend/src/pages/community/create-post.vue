<template>
  <main class="editor-page">
    <header class="editor-hero">
      <small>COMMUNITY EDITOR</small>
      <h1>
        {{
          editing ? "编辑内容" : isQuestion ? "提出一个好问题" : "发布学习分享"
        }}
      </h1>
      <p>
        {{
          isQuestion
            ? "说清背景、已经尝试过什么，以及真正困惑在哪里。"
            : "不追求标准答案，只记录真实过程、可靠依据和自己的思考。"
        }}
      </p>
    </header>
    <div class="editor-layout">
      <section class="editor-paper">
        <div class="type-switch">
          <button
            :class="{ active: !isQuestion }"
            :disabled="editing"
            @click="isQuestion = false"
          >
            学习分享</button
          ><button
            :class="{ active: isQuestion }"
            :disabled="editing"
            @click="isQuestion = true"
          >
            互助问答
          </button>
        </div>
        <label
          ><span>标题</span><small>{{ title.length }}/300</small></label
        ><input
          v-model="title"
          maxlength="300"
          :placeholder="
            isQuestion
              ? '一句话说明你希望解决的问题'
              : '为这次分享写一个清晰标题'
          "
        />
        <label
          ><span>正文</span><small>{{ content.length }}/10000</small></label
        ><textarea
          v-model="content"
          maxlength="10000"
          :placeholder="
            isQuestion
              ? '补充问题背景、自己的判断和具体困惑…'
              : '写下学习过程、关键收获、参考依据和新的思考…'
          "
        />
        <label><span>学习分类</span></label>
        <div class="categories">
          <button
            v-for="item in categories"
            :key="item"
            :class="{ active: category === item }"
            @click="category = item"
          >
            {{ item }}
          </button>
        </div>
        <label><span>配图</span><small>最多 3 张，每张不超过 5MB</small></label>
        <div class="attachments">
          <button v-for="file in attachments" :key="file.id" class="image-file">
            <img :src="assetUrl(file.url)" /><i
              @click.stop="removeFile(file.id)"
              >移除</i
            ></button
          ><button
            v-if="attachments.length < 3"
            class="add-image"
            :disabled="uploading"
            @click="chooseImages"
          >
            {{ uploading ? "上传中…" : "＋ 添加图片" }}
          </button>
        </div>
        <div class="editor-actions">
          <button @click="previewOpen = true">预览</button
          ><button
            class="submit"
            :disabled="submitting || uploading || !ready"
            @click="submit"
          >
            {{
              submitting
                ? "正在保存…"
                : editing
                  ? "保存修改"
                  : isQuestion
                    ? "发布问题"
                    : "发布分享"
            }}
          </button>
        </div>
        <p class="draft-note">
          内容会自动保存在本机草稿中，发布成功后自动清除。
        </p>
      </section>
      <aside>
        <small>WRITING GUIDE</small>
        <h3>
          {{ isQuestion ? "一个好问题通常包含" : "一篇有价值的分享通常包含" }}
        </h3>
        <ol v-if="isQuestion">
          <li>你正在处理的具体情境</li>
          <li>已经查过或尝试过什么</li>
          <li>你卡住的关键判断</li>
        </ol>
        <ol v-else>
          <li>学习或实践发生在哪里</li>
          <li>哪一点改变了原有理解</li>
          <li>接下来准备如何行动</li>
        </ol>
        <p>请勿上传包含手机号、身份证号等敏感个人信息的图片。</p>
      </aside>
    </div>
    <div
      v-if="previewOpen"
      class="preview-mask"
      @click.self="previewOpen = false"
    >
      <article class="preview">
        <header>
          <small
            >{{ category }} · {{ isQuestion ? "互助问答" : "学习分享" }}</small
          ><button @click="previewOpen = false">关闭</button>
        </header>
        <h2>{{ title || "未填写标题" }}</h2>
        <p>{{ content || "尚未填写正文" }}</p>
        <div class="preview-images">
          <img
            v-for="file in attachments"
            :key="file.id"
            :src="assetUrl(file.url)"
          />
        </div>
      </article>
    </div>
  </main>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { onHide, onLoad } from "@dcloudio/uni-app";
import { communityApi, type CommunityAttachment } from "@/api/community";
const title = ref(""),
  content = ref(""),
  category = ref("学习心得"),
  isQuestion = ref(false),
  submitting = ref(false),
  uploading = ref(false),
  previewOpen = ref(false),
  attachments = ref<CommunityAttachment[]>([]),
  editId = ref("");
const categories = ["学习心得", "理论学习", "党史学习", "实践活动", "校园生活"];
let saveTimer: any;
const editing = computed(() => Boolean(editId.value)),
  ready = computed(
    () => title.value.trim().length >= 2 && content.value.trim().length >= 2,
  );
function draftKey() {
  return `community-draft:${editId.value || (isQuestion.value ? "question" : "post")}`;
}
function saveDraft() {
  if (!ready.value && !attachments.value.length) return;
  uni.setStorageSync(
    draftKey(),
    JSON.stringify({
      title: title.value,
      content: content.value,
      category: category.value,
      isQuestion: isQuestion.value,
      attachments: attachments.value,
    }),
  );
}
function restoreDraft() {
  try {
    const data = JSON.parse(uni.getStorageSync(draftKey()) || "{}");
    title.value = data.title || "";
    content.value = data.content || "";
    category.value = data.category || category.value;
    attachments.value = data.attachments || [];
  } catch {}
}
function assetUrl(url: string) {
  const base = import.meta.env.VITE_API_BASE_URL || "/api/v1";
  return url.startsWith("/api/v1")
    ? `${base.replace(/\/api\/v1$/, "")}${url}`
    : url;
}
function chooseImages() {
  const chooser = (uni as any).chooseFile || (uni as any).chooseMessageFile;
  chooser({
    count: 3 - attachments.value.length,
    type: "image",
    extension: ["jpg", "jpeg", "png", "webp"],
    success: async (result: any) => {
      const files = result.tempFiles || [];
      uploading.value = true;
      try {
        for (const file of files) {
          attachments.value.push(await communityApi.upload(file, "post_image"));
        }
      } catch (e: any) {
        uni.showToast({ title: e.message || "图片上传失败", icon: "none" });
      } finally {
        uploading.value = false;
      }
    },
  });
}
async function removeFile(id: string) {
  attachments.value = attachments.value.filter((x) => x.id !== id);
  try {
    await communityApi.deleteAttachment(id);
  } catch {}
}
async function submit() {
  if (!ready.value || submitting.value) return;
  submitting.value = true;
  try {
    let post;
    if (editing.value)
      post = await communityApi.updatePost(editId.value, {
        title: title.value.trim(),
        content: content.value.trim(),
        category: category.value,
        attachment_ids: attachments.value.map((x) => x.id),
      });
    else
      post = await communityApi.createPost({
        title: title.value.trim(),
        content: content.value.trim(),
        category: category.value,
        is_question: isQuestion.value,
        attachment_ids: attachments.value.map((x) => x.id),
        submission_id: `post-${Date.now()}-${Math.random().toString(36).slice(2)}`,
      });
    uni.removeStorageSync(draftKey());
    uni.showToast({ title: "保存成功", icon: "success" });
    uni.redirectTo({ url: `/pages/community/post-detail?id=${post.id}` });
  } catch (e: any) {
    uni.showToast({ title: e.message || "保存失败", icon: "none" });
  } finally {
    submitting.value = false;
  }
}
watch(
  [title, content, category, isQuestion, attachments],
  () => {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(saveDraft, 500);
  },
  { deep: true },
);
onLoad(async (query: any) => {
  isQuestion.value = query?.type === "question";
  if (query?.id) {
    editId.value = query.id;
    try {
      const post = await communityApi.getPost(editId.value);
      title.value = post.title;
      content.value = post.content;
      category.value = post.category;
      isQuestion.value = post.is_question;
      attachments.value = post.attachments || [];
    } catch (e: any) {
      uni.showToast({ title: e.message || "内容加载失败", icon: "none" });
    }
  } else restoreDraft();
});
onHide(saveDraft);
</script>

<style scoped>
.editor-page {
  min-height: 100vh;
  background: #ece5da;
}
.editor-hero {
  padding: 38px clamp(22px, 6vw, 70px) 30px;
  background: #421b18;
  color: #fff8e9;
}
.editor-hero small {
  color: #dfc174;
  font:
    10px Georgia,
    serif;
  letter-spacing: 3px;
}
.editor-hero h1 {
  margin: 8px 0 7px;
  font-size: 36px;
}
.editor-hero p {
  max-width: 650px;
  margin: 0;
  color: rgba(255, 248, 233, 0.62);
  font-size: 13px;
}
.editor-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 250px;
  gap: 24px;
  max-width: 1000px;
  margin: auto;
  padding: 28px;
}
.editor-paper {
  padding: 27px;
  border: 1px solid #d9cdbd;
  background: #fffaf2;
  box-shadow: 0 14px 40px rgba(55, 39, 23, 0.06);
}
.type-switch {
  display: grid;
  grid-template-columns: 1fr 1fr;
  padding: 4px;
  background: #eee5d8;
}
.type-switch button {
  padding: 11px;
  color: #77695d;
}
.type-switch button.active {
  background: #7f211d;
  color: #fff;
}
.editor-paper label {
  display: flex;
  justify-content: space-between;
  margin: 23px 0 8px;
  font-size: 13px;
  font-weight: 700;
}
.editor-paper label small {
  color: #a09487;
  font-size: 10px;
  font-weight: 400;
}
.editor-paper textarea {
  min-height: 280px;
}
.categories {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}
.categories button {
  padding: 8px 11px;
  border: 1px solid #d7cbbb;
  color: #74675b;
  font-size: 11px;
}
.categories button.active {
  border-color: #7f211d;
  background: #7f211d;
  color: #fff;
}
.attachments {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}
.image-file {
  position: relative;
  height: 130px;
  overflow: hidden;
  background: #eee5d8;
}
.image-file img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.image-file i {
  position: absolute;
  right: 6px;
  top: 6px;
  padding: 4px 7px;
  background: rgba(40, 25, 20, 0.75);
  color: #fff;
  font-size: 9px;
  font-style: normal;
}
.add-image {
  height: 130px;
  border: 1px dashed #baa98f;
  color: #82502b;
}
.editor-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 28px;
  padding-top: 18px;
  border-top: 1px solid #ebe1d4;
}
.editor-actions button {
  min-width: 110px;
  padding: 12px;
  border: 1px solid #cdbdaa;
  color: #786a5d;
}
.editor-actions .submit {
  border-color: #7f211d;
  background: #7f211d;
  color: #fff;
}
.editor-actions button:disabled {
  opacity: 0.45;
}
.draft-note {
  text-align: right;
  color: #9b8d80;
  font-size: 10px;
}
.editor-layout > aside {
  align-self: start;
  padding: 20px;
  border-top: 4px solid #af8643;
  background: #f7f0e5;
}
.editor-layout > aside small {
  color: #a17431;
  font:
    9px Georgia,
    serif;
  letter-spacing: 2px;
}
.editor-layout > aside h3 {
  margin: 6px 0 12px;
  font-size: 17px;
}
.editor-layout > aside ol {
  padding-left: 20px;
  color: #6f6257;
  font-size: 12px;
  line-height: 2;
}
.editor-layout > aside p {
  padding-top: 13px;
  border-top: 1px solid #ded1c0;
  color: #9a7b57;
  font-size: 10px;
}
.preview-mask {
  position: fixed;
  inset: 0;
  z-index: 3000;
  display: grid;
  place-items: center;
  padding: 20px;
  background: rgba(34, 22, 17, 0.58);
}
.preview {
  width: min(700px, 100%);
  max-height: 85vh;
  overflow: auto;
  padding: 28px;
  box-sizing: border-box;
  background: #fffaf2;
}
.preview header {
  display: flex;
  justify-content: space-between;
  color: #9b6f31;
  font-size: 10px;
}
.preview h2 {
  font-size: 26px;
}
.preview > p {
  white-space: pre-wrap;
  line-height: 1.8;
}
.preview-images {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
}
.preview-images img {
  width: 100%;
  height: 150px;
  object-fit: cover;
}
/* #ifndef H5 */
@media (max-width: 700px) {
  .editor-layout {
    grid-template-columns: 1fr;
    padding: 14px;
  }
  .editor-layout > aside {
    display: none;
  }
  .editor-hero {
    padding: 26px 20px;
  }
  .editor-hero h1 {
    font-size: 30px;
  }
  .editor-paper {
    padding: 19px 15px;
  }
  .attachments {
    grid-template-columns: repeat(2, 1fr);
  }
  .editor-actions button {
    flex: 1;
    min-width: 0;
  }
}
/* #endif */
/* #ifdef H5 */
@container (max-width: 700px) {
  .editor-layout {
    grid-template-columns: 1fr;
    padding: 14px;
  }
  .editor-layout > aside {
    display: none;
  }
  .editor-hero {
    padding: 26px 20px;
  }
  .editor-hero h1 {
    font-size: 30px;
  }
  .editor-paper {
    padding: 19px 15px;
  }
  .attachments {
    grid-template-columns: repeat(2, 1fr);
  }
  .editor-actions button {
    flex: 1;
    min-width: 0;
  }
}
/* #endif */
</style>
