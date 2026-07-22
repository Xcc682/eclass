<template>
  <div class="profile">
    <!-- 用户信息 -->
    <div class="profile__header">
      <div class="profile__folio"><span>PERSONAL DESK · 01</span><span>个人中心</span></div>
      <img class="profile__avatar" :src="profile?.avatar_url || defaultAvatar" style="object-fit:cover;display:block;max-width:100%">
      <span class="profile__name">{{ profile?.nickname || '同学' }}</span>
      <span class="profile__school">{{ profile?.school || '未填写学校' }}</span>
      <div class="profile__political">
        <span class="profile__political-text">{{ profile?.political_status || '未填写' }}</span>
      </div>
      <button class="profile__edit" @click="openEditor">编辑资料</button>
    </div>

    <!-- 统计数据 -->
    <div class="profile__stats">
      <div class="profile__stat" @click="goToGrowth">
        <span class="profile__stat-value">{{ profile?.growth?.total_interviews || 0 }}</span>
        <span class="profile__stat-label">练习次数</span>
      </div>
      <div class="profile__stat">
        <span class="profile__stat-value">{{ profile?.total_points || 0 }}</span>
        <span class="profile__stat-label">总积分</span>
      </div>
      <div class="profile__stat">
        <span class="profile__stat-value">{{ profile?.growth?.total_reports || 0 }}</span>
        <span class="profile__stat-label">报告</span>
      </div>
      <div class="profile__stat">
        <span class="profile__stat-value">{{ profile?.growth?.rank || '--' }}</span>
        <span class="profile__stat-label">排名</span>
      </div>
    </div>

    <!-- 功能菜单 -->
    <div class="profile__menu">
      <div class="profile__menu-item" @click="goToGrowth">
        <span class="profile__menu-icon"><IconSet name="growth" size="32rpx" /></span>
        <span class="profile__menu-text">成长档案</span>
        <span class="profile__menu-arrow">›</span>
      </div>
      <div class="profile__menu-item" @click="goToKnowledgeFavorites">
        <span class="profile__menu-icon"><IconSet name="star" size="32rpx" /></span>
        <span class="profile__menu-text">我的收藏</span>
        <span class="profile__menu-arrow">›</span>
      </div>
      <div class="profile__menu-item" @click="goToReports">
        <span class="profile__menu-icon"><IconSet name="target" size="32rpx" /></span>
        <span class="profile__menu-text">我的练习</span>
        <span class="profile__menu-arrow">›</span>
      </div>
      <div class="profile__menu-item" @click="goToReports">
        <span class="profile__menu-icon"><IconSet name="clipboard" size="32rpx" /></span>
        <span class="profile__menu-text">我的报告</span>
        <span class="profile__menu-arrow">›</span>
      </div>
      <div class="profile__menu-item" @click="toggleNotifications">
        <span class="profile__menu-icon"><IconSet name="bell" size="32rpx" /></span>
        <span class="profile__menu-text">站内提醒 <small>{{ notificationsEnabled ? '已开启' : '已关闭' }}</small></span>
        <span class="profile__menu-arrow">›</span>
      </div>
      <div class="profile__menu-item" @click="showAbout">
        <span class="profile__menu-icon"><IconSet name="info" size="32rpx" /></span>
        <span class="profile__menu-text">关于我们</span>
        <span class="profile__menu-arrow">›</span>
      </div>
    </div>

    <!-- 易班绑定状态 -->
    <div class="profile__yiban" @click="showYibanStatus">
      <div class="profile__yiban-left">
        <span class="profile__yiban-icon">易</span>
        <div>
          <span class="profile__yiban-title">易班账号</span>
          <span class="profile__yiban-status">{{ yibanStatus?.bound ? '已绑定' : yibanStatus?.message || '状态加载中' }}</span>
        </div>
      </div>
      <span class="profile__yiban-action">{{ yibanStatus?.available ? '去绑定 ›' : '不可用' }}</span>
    </div>

    <!-- 退出登录 -->
    <div class="profile__logout" @click="handleLogout">
      <span>退出登录</span>
    </div>

    <div style="height: 40rpx"></div>

    <div v-if="editing" class="profile__dialog" @click.self="editing=false"><section><h2>编辑个人资料</h2><label>昵称<input v-model="editForm.nickname" /></label><label>学校<input v-model="editForm.school" /></label><label>学院<input v-model="editForm.college" /></label><label>政治面貌<input v-model="editForm.political_status" /></label><footer><button @click="editing=false">取消</button><button class="primary" @click="saveProfile">保存</button></footer></section></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { userApi, type UserInfo } from '@/api/user'
import IconSet from '@/components/common/IconSet.vue'
import defaultAvatar from '@/static/images/icons/default-avatar.png'

const profile = ref<UserInfo | null>(null)
const yibanStatus = ref<Awaited<ReturnType<typeof userApi.getYibanStatus>> | null>(null)
const editing = ref(false)
const notificationsEnabled = ref(uni.getStorageSync('in_app_notifications') !== 'off')
const editForm = ref({ nickname:'', school:'', college:'', political_status:'' })
onMounted(async () => {
  try { [profile.value, yibanStatus.value] = await Promise.all([userApi.getProfile(), userApi.getYibanStatus()]) } catch (error) { console.error(error) }
})

function goToGrowth() { uni.navigateTo({ url: '/pages/community/growth' }) }
function goToKnowledgeFavorites() { uni.navigateTo({ url: '/pages/knowledge/favorites' }) }
function goToReports() { uni.navigateTo({ url: '/pages/community/reports' }) }
function openEditor(){ if(!profile.value)return; editForm.value={nickname:profile.value.nickname||'',school:profile.value.school||'',college:profile.value.college||'',political_status:profile.value.political_status||''};editing.value=true }
async function saveProfile(){try{profile.value=await userApi.updateProfile(editForm.value as any);editing.value=false;uni.showToast({title:'资料已更新',icon:'success'})}catch(error:any){uni.showToast({title:error.message||'保存失败',icon:'none'})}}
function toggleNotifications(){notificationsEnabled.value=!notificationsEnabled.value;uni.setStorageSync('in_app_notifications',notificationsEnabled.value?'on':'off');uni.showToast({title:notificationsEnabled.value?'已开启站内提醒':'已关闭站内提醒',icon:'none'})}
function showAbout(){uni.showModal({title:'关于思政情景工坊',content:'版本 1.0.0\n提供谈话训练、党史情景、红色研学、思政辩论、知识库和成长社区功能。AI 内容仅作学习辅助，重要事实请以权威资料为准。',showCancel:false})}
function showYibanStatus(){uni.showModal({title:'易班账号',content:yibanStatus.value?.message||'状态暂不可用',showCancel:false})}

function handleLogout() {
  uni.showModal({
    title: '提示',
    content: '确定退出登录吗？',
    success: (res) => {
      if (res.confirm) {
        uni.removeStorageSync('token')
        uni.reLaunch({ url: '/pages/login/login' })
      }
    }
  })
}
</script>

<style scoped>
.profile { min-height: 100vh; background: var(--color-bg); }

/* Header */
.profile__header {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 80rpx 32rpx 40rpx;
  background: linear-gradient(180deg, #8B1A1A, #5C0E0E);
}
.profile__avatar { width: 120rpx; height: 120rpx; border-radius: 50%; border: 6rpx solid rgba(255,255,255,0.3); margin-bottom: 16rpx; }
.profile__name { font-family: 'STKaiti', 'Noto Serif SC', serif;
  font-size: 36rpx; font-weight: 700; color: #FFFFFF; margin-bottom: 4rpx; }
.profile__school { font-size: 24rpx; color: rgba(255,255,255,0.8); margin-bottom: 12rpx; }
.profile__political-text { display: inline-block; background: rgba(255,255,255,0.2); color: #FFFFFF; font-size: 22rpx; padding: 6rpx 24rpx; border-radius: 4px; }
.profile__edit{margin-top:16rpx;padding:10rpx 24rpx;border:1rpx solid rgba(255,255,255,.5);border-radius:999rpx;color:#fff}.profile__menu-text small{float:right;color:#9b8e8e;font-weight:400}.profile__dialog{position:fixed;inset:0;z-index:2200;background:rgba(30,20,16,.52);display:flex;align-items:flex-end}.profile__dialog section{width:100%;box-sizing:border-box;padding:36rpx;background:#fffdf8;border-radius:28rpx 28rpx 0 0}.profile__dialog h2{font-family:STKaiti,serif}.profile__dialog label{display:block;margin:18rpx 0;font-size:23rpx}.profile__dialog input{margin-top:8rpx}.profile__dialog footer{display:flex;gap:14rpx;margin-top:26rpx}.profile__dialog footer button{flex:1;padding:20rpx;border:1rpx solid #ddd0bf;border-radius:14rpx}.profile__dialog footer .primary{background:#8b1a1a;color:#fff}

/* Stats */
.profile__stats { display: flex; margin: -20rpx 32rpx 24rpx; background: var(--color-card);
  border-left: 3px solid var(--color-primary-light); border-radius: 4px; padding: 24rpx; box-shadow: 0 4rpx 16rpx rgba(0,0,0,0.08); }
.profile__stat { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 4rpx; }
.profile__stat-value { font-family: 'STKaiti', 'Noto Serif SC', serif;
  font-size: 32rpx; font-weight: 700; color: var(--color-primary-light); }
.profile__stat-label { font-size: 20rpx; color: var(--color-text-muted); }

/* Menu */
.profile__menu { margin: 0 32rpx 24rpx; background: var(--color-card);
  border-left: 3px solid var(--color-primary-light); border-radius: 4px; overflow: hidden; box-shadow: 0 2rpx 8rpx rgba(0,0,0,0.04);
  transition: box-shadow 0.2s ease; }
.profile__menu-item { display: flex; align-items: center; padding: 28rpx 32rpx; border-bottom: 1rpx solid var(--color-border); }
.profile__menu-item:last-child { border-bottom: none; }
.profile__menu-icon { font-size: 32rpx; margin-right: 20rpx; }
.profile__menu-text { flex: 1; font-size: 26rpx; color: var(--color-text); }
.profile__menu-arrow { font-size: 32rpx; color: var(--color-text-muted); }

/* Yiban */
.profile__yiban { display: flex; align-items: center; justify-content: space-between; margin: 0 32rpx 24rpx; background: var(--color-card);
  border-left: 3px solid var(--color-primary-light); border-radius: 4px; padding: 28rpx 32rpx; box-shadow: 0 2rpx 8rpx rgba(0,0,0,0.04);
  transition: box-shadow 0.2s ease; }
.profile__yiban-left { display: flex; align-items: center; gap: 16rpx; }
.profile__yiban-icon { font-size: 32rpx; }
.profile__yiban-title { font-size: 26rpx; font-weight: 500; color: var(--color-text); display: block; }
.profile__yiban-status { font-size: 22rpx; color: var(--color-text-muted); }
.profile__yiban-action { font-size: 24rpx; color: var(--color-primary-light); }

/* Logout */
.profile__logout { margin: 0 32rpx; padding: 28rpx; text-align: center; background: var(--color-card);
  border-left: 3px solid var(--color-primary-light); border-radius: 4px; font-size: 26rpx; color: var(--color-primary-light); box-shadow: 0 2rpx 8rpx rgba(0,0,0,0.04);
  transition: box-shadow 0.2s ease; }

/* Personal archive theme */
.profile__header{position:relative;padding:50rpx 32rpx 55rpx;background:#431a18}.profile__folio{display:flex;justify-content:space-between;width:100%;margin-bottom:34rpx;font-size:15rpx;letter-spacing:3rpx;color:#e7c981}.profile__avatar{width:112rpx;height:112rpx;border:5rpx double rgba(231,201,129,.68)}.profile__name{font:700 35rpx var(--font-display)}.profile__school{font-size:21rpx;color:rgba(255,255,255,.58)}.profile__political-text{border:1px solid rgba(231,201,129,.45);border-radius:2rpx;background:transparent;color:#e7c981;font-size:18rpx;letter-spacing:2rpx}.profile__edit{border-radius:2rpx;border-color:rgba(255,255,255,.24);font-size:19rpx;color:rgba(255,255,255,.72)}
.profile__stats{margin-top:-25rpx;border:1px solid rgba(72,25,22,.12);border-left:1px solid rgba(72,25,22,.12);border-radius:2rpx;box-shadow:0 9rpx 26rpx rgba(45,31,23,.1)}.profile__stat{border-right:1px solid rgba(72,25,22,.09)}.profile__stat:last-child{border:0}.profile__stat-value{font:700 29rpx var(--font-display);color:var(--color-primary)}.profile__stat-label{font-size:17rpx}
.profile__menu,.profile__yiban,.profile__logout{border:1px solid rgba(72,25,22,.11);border-left:1px solid rgba(72,25,22,.11);border-radius:2rpx;box-shadow:0 7rpx 22rpx rgba(48,32,22,.05)}.profile__menu-item{padding:24rpx 27rpx}.profile__menu-icon{display:grid;place-items:center;width:48rpx;height:48rpx;margin-right:17rpx;border:1px solid rgba(72,25,22,.1);color:var(--color-primary)}.profile__menu-text{font-size:23rpx}.profile__yiban-icon{display:grid;place-items:center;width:48rpx;height:48rpx;border-radius:50%;background:#2f5d91;color:white;font:700 20rpx var(--font-display)}.profile__logout{color:var(--color-primary);background:transparent}
</style>
