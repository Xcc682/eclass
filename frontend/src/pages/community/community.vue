<template>
  <div class="community">
    <header class="community-hero">
      <div><span>LEARNING COMMONS · 01</span><h1>在交流中，让思考继续生长</h1><p>分享学习心得、提出真实问题，也在教师任务中完成一次有反馈的学习。</p></div>
      <button @click="goCreatePost">＋ 发布</button>
    </header>
    <!-- 顶部 tabs -->
    <div class="filter-bar community__tabs" style="display:flex">
      <div v-for="tab in tabs" :key="tab.key"
        class="community__tab"
        :class="{ 'community__tab--active': activeTab === tab.key }"
        @click="activeTab = tab.key">
        <span>{{ tab.label }}</span>
      </div>
    </div>

    <!-- 学习圈 -->
    <div v-show="activeTab === 'circle'">
      <div class="community__post" v-for="post in posts" :key="post.id" @click="goToPost(post)">
        <div class="community__post-header">
          <img class="community__post-avatar" :src="defaultAvatar" style="object-fit:cover;display:block;max-width:100%">
          <div class="community__post-user">
            <span class="community__post-name">{{ post.author }}</span>
            <span class="community__post-time">{{ post.time }}</span>
          </div>
          <span class="community__post-category">{{ post.category }}</span>
        </div>
        <span class="community__post-title">{{ post.title }}</span>
        <span class="community__post-excerpt">{{ post.excerpt }}</span>
        <div class="community__post-stats">
          <span>回复 {{ post.replies }}</span>
          <span>赞同 {{ post.likes }}</span>
          <span>阅读 {{ post.views }}</span>
        </div>
      </div>
      <EmptyState v-if="posts.length === 0" title="暂无帖子" description="快来发布第一条学习心得吧！" actionText="发布帖子" @action="goCreatePost" />
    </div>

    <!-- 互助问答 -->
    <div v-show="activeTab === 'qa'">
      <div class="community__qa" v-for="qa in qaList" :key="qa.id" @click="goToPost(qa)">
        <span class="community__qa-tag" :class="{ resolved: qa.resolved }">{{ qa.resolved ? '✓ 已解决' : '？ 待解答' }}</span>
        <span class="community__qa-title">{{ qa.title }}</span>
        <span class="community__qa-meta">{{ qa.author }} · {{ qa.time }}</span>
      </div>
      <EmptyState v-if="qaList.length === 0" title="暂无问答" description="有问题就来问吧，老师和同学会共同解答" actionText="我要提问" @action="goCreateQuestion" />
      <button class="community__create-question" @click="goCreateQuestion">提出新问题</button>
    </div>

    <!-- 教师任务 -->
    <div v-show="activeTab === 'tasks'">
      <button v-if="canManageTasks" class="community__create-task" @click="showTaskCreator=true">发布教师任务</button>
      <div class="community__task" v-for="task in tasks" :key="task.id" @click="openTask(task)">
        <div class="community__task-left">
          <span class="community__task-title">{{ task.title }}</span>
          <span class="community__task-desc">{{ task.description }}</span>
          <span class="community__task-deadline">截止 · {{ task.deadline || '长期有效' }}</span>
        </div>
        <div class="community__task-status" :class="'community__task-status--' + task.status">
          {{ task.submission?.status === 'reviewed' ? `${task.submission.score ?? 0} 分` : task.submission ? '已提交' : task.statusLabel }}
        </div>
      </div>
      <EmptyState v-if="tasks.length === 0" title="暂无任务" description="老师还没有发布任务" />
    </div>

    <div v-if="activeTask" class="task-dialog" @click.self="closeTask">
      <section class="task-sheet" @click.stop>
        <div class="task-sheet__handle"></div>
        <header class="task-sheet__header">
          <div>
            <span class="task-sheet__eyebrow">教师任务</span>
            <h2>{{ activeTask.title }}</h2>
          </div>
          <span class="task-sheet__status">{{ activeTask.submission?.status === 'reviewed' ? '已批阅' : activeTask.submission ? '已提交' : '待提交' }}</span>
        </header>
        <p class="task-sheet__description">{{ activeTask.description || '老师暂未填写补充要求' }}</p>
        <p v-if="activeTask.deadline" class="task-sheet__deadline">截止时间：{{ activeTask.deadline }}</p>
        <label class="task-sheet__field">
          <span>学习成果</span>
          <textarea
            v-model="taskContent"
            maxlength="5000"
            :disabled="activeTask.submission?.status === 'reviewed' || taskSubmitting"
            placeholder="填写学习成果、心得或作业内容"
          />
          <small>{{ taskContent.length }}/5000</small>
        </label>
        <p v-if="activeTask.submission?.feedback" class="task-feedback">教师反馈：{{ activeTask.submission.feedback }}</p>
        <footer>
          <button :disabled="taskSubmitting" @click="closeTask">关闭</button>
          <button v-if="activeTask.submission?.status !== 'reviewed'" class="primary" :disabled="taskSubmitting || taskContent.trim().length < 2" @click="submitTask">
            {{ taskSubmitting ? '提交中…' : activeTask.submission ? '更新提交' : '提交任务' }}
          </button>
        </footer>
      </section>
    </div>
    <div v-if="showTaskCreator" class="task-dialog" @click.self="showTaskCreator=false">
      <section class="task-sheet" @click.stop>
        <div class="task-sheet__handle"></div>
        <header class="task-sheet__header"><div><span class="task-sheet__eyebrow">教师工作台</span><h2>发布教师任务</h2></div></header>
        <label class="task-sheet__field"><span>任务标题</span><input v-model="taskForm.title" maxlength="120" placeholder="请输入任务标题"/></label>
        <label class="task-sheet__field"><span>任务要求</span><textarea v-model="taskForm.description" maxlength="3000" placeholder="说明学习目标、提交内容和评价要求"/></label>
        <label class="task-sheet__field"><span>截止日期</span><input v-model="taskForm.deadline" placeholder="例如：2026-12-31"/></label>
        <footer><button :disabled="taskSubmitting" @click="showTaskCreator=false">取消</button><button class="primary" :disabled="taskSubmitting" @click="createTask">{{ taskSubmitting ? '发布中…' : '发布任务' }}</button></footer>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import EmptyState from '@/components/common/EmptyState.vue'
import { communityApi, type TeacherTask } from '@/api/community'
import defaultAvatar from '@/static/images/icons/default-avatar.png'
import { userApi } from '@/api/user'

const activeTab = ref('circle')
const tabs = ref([
  { key: 'circle', label: '学习圈' },
  { key: 'qa', label: '互助问答' },
  { key: 'tasks', label: '教师任务' }
])

const posts = ref<Array<any>>([])

const qaList = ref<Array<any>>([])

const tasks = ref<Array<any>>([])
const activeTask = ref<TeacherTask | null>(null)
const taskContent = ref('')
const taskSubmitting = ref(false)
const canManageTasks = ref(false)
const showTaskCreator = ref(false)
const taskForm = ref({ title:'', description:'', deadline:'' })

function goToPost(post: any) {
  uni.navigateTo({ url: `/pages/community/post-detail?id=${post.id}` })
}

onMounted(async () => {
  try {
    const [postRows, questionRows, taskRows] = await Promise.all([
      communityApi.getPosts('post'), communityApi.getPosts('question'), communityApi.getTasks()
    ])
    posts.value = postRows.map(post => ({ ...post, time: new Date(post.created_at).toLocaleString() }))
    qaList.value = questionRows.map(post => ({ ...post, time: new Date(post.created_at).toLocaleString() }))
    tasks.value = taskRows.map(task => ({ ...task, statusLabel: task.status === 'active' ? '进行中' : task.status }))
    const profile = await userApi.getProfile(); canManageTasks.value = ['teacher','admin'].includes(profile.role)
  } catch (error) { console.error(error) }
})
function goCreatePost() { uni.navigateTo({ url: '/pages/community/create-post' }) }
function goCreateQuestion() { uni.navigateTo({ url: '/pages/community/create-post?type=question' }) }
function openTask(task: TeacherTask) { activeTask.value = task; taskContent.value = '' }
function closeTask() { if (!taskSubmitting.value) activeTask.value = null }
async function submitTask() {
  if (!activeTask.value || taskContent.value.trim().length < 2) return uni.showToast({ title: '请填写任务内容', icon: 'none' })
  taskSubmitting.value = true
  try { await communityApi.submitTask(activeTask.value.id, taskContent.value.trim()); uni.showToast({ title: '提交成功', icon: 'success' }); activeTask.value = null; const rows = await communityApi.getTasks(); tasks.value = rows.map(task => ({ ...task, statusLabel: task.status === 'active' ? '进行中' : task.status })) }
  catch (error: any) { uni.showToast({ title: error.message || '提交失败', icon: 'none' }) }
  finally { taskSubmitting.value = false }
}
async function createTask(){if(taskForm.value.title.trim().length<2)return uni.showToast({title:'请填写任务标题',icon:'none'});taskSubmitting.value=true;try{await communityApi.createTask(taskForm.value);showTaskCreator.value=false;taskForm.value={title:'',description:'',deadline:''};tasks.value=await communityApi.getTasks();uni.showToast({title:'任务已发布',icon:'success'})}catch(error:any){uni.showToast({title:error.message||'发布失败',icon:'none'})}finally{taskSubmitting.value=false}}
</script>

<style scoped>
.community { min-height: 100vh; background: var(--color-bg); }

/* Tabs */
.community__tabs { display: flex; margin: 24rpx 32rpx; background: var(--color-card);
  border-left: 3px solid var(--color-primary-light); border-radius: 48rpx; padding: 8rpx; box-shadow: 0 2rpx 8rpx rgba(0,0,0,0.06);
  transition: box-shadow 0.2s ease; }
.community__tab { flex: 1; text-align: center; padding: 16rpx 0; font-size: 26rpx; color: var(--color-text-secondary); border-radius: 4px; font-weight: 500; }
.community__tab--active { background: #C41E1A; color: #FFFFFF; }

/* Posts */
.community__post { margin: 0 32rpx 20rpx; background: var(--color-card);
  border-left: 3px solid var(--color-primary-light); border-radius: 4px; padding: 28rpx; box-shadow: 0 2rpx 8rpx rgba(0,0,0,0.04);
  transition: box-shadow 0.2s ease; }
.community__post-header { display: flex; align-items: center; gap: 12rpx; margin-bottom: 12rpx; }
.community__post-avatar { width: 48rpx; height: 48rpx; border-radius: 50%; }
.community__post-user { flex: 1; }
.community__post-name { font-size: 24rpx; font-weight: 500; color: var(--color-text); }
.community__post-time { font-size: 20rpx; color: var(--color-text-muted); margin-left: 8rpx; }
.community__post-category { font-size: 20rpx; color: var(--color-primary-light); background: rgba(139,26,26,0.06); padding: 4rpx 16rpx; border-radius: 4px; }
.community__post-title { font-size: 28rpx; font-weight: 600; color: var(--color-text); display: block; margin-bottom: 8rpx; }
.community__post-excerpt { font-size: 24rpx; color: var(--color-text-muted); display: block; margin-bottom: 12rpx; line-height: 1.5; }
.community__post-stats { display: flex; gap: 24rpx; font-size: 20rpx; color: var(--color-text-muted); }

/* QA */
.community__qa { margin: 0 32rpx 16rpx; background: var(--color-card);
  border-left: 3px solid var(--color-primary-light); border-radius: 4px; padding: 24rpx; box-shadow: 0 2rpx 8rpx rgba(0,0,0,0.04);
  transition: box-shadow 0.2s ease; }
.community__qa-tag { font-size: 20rpx; color: #F57C00; background: #FFF3E0; padding: 4rpx 14rpx; border-radius: 12rpx; margin-bottom: 8rpx; display: inline-block; }
.community__qa-title { font-size: 26rpx; font-weight: 500; color: var(--color-text); display: block; margin-bottom: 6rpx; }
.community__qa-meta { font-size: 20rpx; color: var(--color-text-muted); }
.community__qa-tag.resolved{background:#e8f5e9;color:#2e7d32}.community__create-question{display:block;margin:20rpx auto 32rpx;padding:16rpx 28rpx;border:1rpx solid #c41e1a;color:#8b1a1a;border-radius:999rpx}

/* Tasks */
.community__task { display: flex; margin: 0 32rpx 16rpx; background: var(--color-card);
  border-left: 3px solid var(--color-primary-light); border-radius: 4px; padding: 24rpx; box-shadow: 0 2rpx 8rpx rgba(0,0,0,0.04);
  transition: box-shadow 0.2s ease; gap: 16rpx; }
.community__task-left { flex: 1; }
.community__task-title { font-size: 26rpx; font-weight: 600; color: var(--color-text); display: block; margin-bottom: 6rpx; }
.community__task-desc { font-size: 22rpx; color: var(--color-text-muted); display: block; margin-bottom: 8rpx; }
.community__task-deadline { font-size: 20rpx; color: var(--color-text-muted); }
.community__task-status { padding: 8rpx 20rpx; border-radius: 4px; font-size: 22rpx; font-weight: 500; white-space: nowrap; align-self: center; }
.community__task-status--pending { background: #FFF3E0; color: #F57C00; }
.community__task-status--completed { background: #E8F5E9; color: var(--color-primary-light); }
.community__task-status--new { background: rgba(139,26,26,0.06); color: var(--color-primary-light); }
.community__create-task{display:block;margin:0 32rpx 18rpx;padding:18rpx 24rpx;background:#2d4938;color:#fff;border-radius:12rpx}
.task-dialog{position:fixed;top:0;right:0;bottom:calc(88rpx + env(safe-area-inset-bottom, 0px));left:0;z-index:2000;display:flex;align-items:flex-end;justify-content:center;padding:24rpx;background:rgba(30,20,16,.56);box-sizing:border-box;backdrop-filter:blur(4rpx)}
.task-sheet{position:relative;width:min(720rpx,100%);max-height:calc(100vh - 180rpx);overflow-y:auto;box-sizing:border-box;background:#fffdf8;border:1rpx solid #e2d5c3;border-radius:28rpx;padding:24rpx 32rpx 30rpx;box-shadow:0 28rpx 80rpx rgba(28,18,12,.28)}
.task-sheet__handle{width:72rpx;height:7rpx;margin:0 auto 22rpx;border-radius:999rpx;background:#d8cbbb}
.task-sheet__header{display:flex;align-items:flex-start;justify-content:space-between;gap:20rpx;margin-bottom:16rpx}.task-sheet__eyebrow{display:block;margin-bottom:7rpx;color:#8b1a1a;font-size:18rpx;letter-spacing:3rpx}.task-sheet h2{margin:0;font-family:STKaiti,serif;font-size:34rpx;line-height:1.35;color:#312a24}.task-sheet__status{flex:none;padding:7rpx 14rpx;border-radius:999rpx;background:#f2e8d9;color:#755b3d;font-size:19rpx}.task-sheet__description{margin:0;color:#746b62;line-height:1.65}.task-sheet__deadline{margin:12rpx 0 0!important;color:#91622e!important;font-size:21rpx}
.task-sheet__field{display:block;margin-top:22rpx}.task-sheet__field>span{display:block;margin-bottom:10rpx;color:#4d433a;font-size:22rpx;font-weight:600}.task-sheet input,.task-sheet textarea{display:block;width:100%;box-sizing:border-box;border:1rpx solid #e3d8c8;border-radius:14rpx;background:#f5efe6;color:#332d27;font-size:24rpx;padding:18rpx 20rpx}.task-sheet input{height:76rpx}.task-sheet textarea{min-height:220rpx;line-height:1.65}.task-sheet textarea:disabled{opacity:.72;background:#eee8df}.task-sheet__field small{display:block;margin-top:8rpx;color:#a09283;text-align:right;font-size:18rpx}
.task-sheet footer{position:sticky;bottom:-30rpx;display:flex;gap:16rpx;margin:24rpx -4rpx -6rpx;padding:16rpx 4rpx 6rpx;background:#fffdf8}.task-sheet footer button{flex:1;min-height:76rpx;margin:0;border:1rpx solid #dbcfc0;border-radius:14rpx;background:#fffdf8;color:#65594e;font-size:24rpx}.task-sheet footer .primary{border-color:#8b1a1a;background:#8b1a1a;color:#fff}.task-sheet footer button:disabled{opacity:.45}.task-feedback{margin-top:18rpx;padding:16rpx;border-left:5rpx solid #2e6a43;background:#edf3ed;color:#2e6a43!important;line-height:1.6}

/* Editorial community surface */
.community-hero{display:flex;align-items:end;gap:25rpx;padding:45rpx var(--page-gutter) 35rpx;color:#fff9ed;background:#4a1917}.community-hero>div{flex:1}.community-hero span{font-size:15rpx;letter-spacing:4rpx;color:#e6ca83}.community-hero h1{margin:10rpx 0 8rpx;font:700 36rpx/1.35 var(--font-display)}.community-hero p{margin:0;font-size:19rpx;line-height:1.55;color:rgba(255,249,237,.58)}.community-hero button{flex:none;margin:0 0 3rpx;padding:13rpx 17rpx;border:1px solid rgba(231,201,129,.55);border-radius:2rpx;background:transparent;color:#e7c981;font-size:19rpx;line-height:1.2}
.community__tabs{border:1px solid rgba(72,25,22,.12);border-left:1px solid rgba(72,25,22,.12);border-radius:2rpx;padding:7rpx;box-shadow:0 5rpx 18rpx rgba(45,31,23,.05)}.community__tab{padding:14rpx 0;border-radius:1px;font-size:22rpx}.community__tab--active{background:var(--color-primary)}
.community__post,.community__qa,.community__task{border:1px solid rgba(72,25,22,.11);border-left:1px solid rgba(72,25,22,.11);border-radius:2rpx;box-shadow:0 7rpx 22rpx rgba(48,32,22,.05)}.community__post-title{font:700 28rpx var(--font-display)}.community__post-stats{padding-top:14rpx;border-top:1px solid rgba(72,25,22,.08);font-size:18rpx}.community__create-question{border-radius:2rpx!important;background:transparent}.community__create-task{border-radius:2rpx;background:var(--color-green)}
</style>
