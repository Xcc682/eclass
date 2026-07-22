<template>
  <div class="login">
    <div class="login__hero">
      <div class="login__edition"><span>IDEOLOGICAL PRACTICE</span><b>2026 · 学习版</b></div>
      <div class="login__brand">
        <div class="login__seal"><span>思</span></div>
        <div><span class="login__kicker">知行合一 · 以学促行</span><h1>思政情景工坊</h1><p>沉浸式思政实践与成长平台</p></div>
      </div>
      <div class="login__quote"><i></i><span>在真实情景中理解理论，在持续实践中看见成长。</span></div>
    </div>
    <div class="login__content">
      <div class="login__card">
        <header><span>ACCOUNT ACCESS</span><h2>账号登录</h2><p>首次登录将自动创建学习档案</p></header>
        <div class="login__phone-section">
          <div class="login__input-group">
            <span class="login__input-label"><b>01</b> 手机号</span>
            <input class="login__input" v-model="phone" type="text" maxlength="11" placeholder="请输入手机号" placeholder-class="login__placeholder" />
          </div>
          <div class="login__input-group">
            <span class="login__input-label"><b>02</b> 密码</span>
            <input class="login__input" v-model="password" type="password" maxlength="128" placeholder="请输入密码（至少6位）" placeholder-class="login__placeholder" />
          </div>
          <button class="login__submit" @click="handlePhoneLogin"><span class="login__submit-text">进入工坊</span><i>→</i></button>
        </div>
        <button class="login__yiban-btn" :class="{ disabled: !yibanAvailable }" @click="handleYibanLogin">
          <img class="login__yiban-icon" :src="yibanIcon" style="object-fit:contain;display:block;max-width:100%">
          <span class="login__yiban-text">{{ yibanAvailable ? '使用易班统一登录' : '易班登录暂未配置' }}</span><small>学校统一身份</small>
        </button>
        <div class="login__agreement">
          <span class="login__agreement-text">登录即代表同意</span>
          <span class="login__agreement-link" @click="showAgreement('service')">《用户服务协议》</span>
          <span class="login__agreement-text">和</span>
          <span class="login__agreement-link" @click="showAgreement('privacy')">《隐私政策》</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useUserStore } from '@/store/user'
import yibanIcon from '@/static/images/icons/yiban.png'

const userStore = useUserStore()
const phone = ref('')
const password = ref('')
const yibanAvailable = ref(false)

async function handleYibanLogin() {
  uni.showModal({ title: '易班统一登录', content: '当前部署尚未配置学校易班 OAuth 服务，系统不会模拟登录或绑定。请由管理员完成应用参数和换票地址配置。', showCancel: false })
}

function showAgreement(type: 'service' | 'privacy') {
  const content = type === 'service' ? '本平台用于思政学习与训练。请使用本人账号，不发布违法、侵权或虚假内容；AI 生成内容仅作学习辅助。' : '平台仅保存完成业务所需的账号资料、学习记录和用户主动提交的内容，不会把数据用于未经说明的用途。'
  uni.showModal({ title: type === 'service' ? '用户服务协议摘要' : '隐私政策摘要', content, showCancel: false })
}

async function handlePhoneLogin() {
  if (phone.value.length !== 11 || password.value.length < 6) {
    uni.showToast({ title: '请输入正确手机号和至少6位密码', icon: 'none' })
    return
  }
  try {
    await userStore.login({ phone: phone.value, password: password.value })
    uni.showToast({ title: '登录成功', icon: 'success' })
    uni.switchTab({ url: '/pages/index/index' })
  } catch {}
}
</script>

<style scoped>
.login{min-height:100vh;padding-bottom:40rpx;background:#eee8de;color:var(--color-text)}
.login__hero{position:relative;overflow:hidden;padding:34rpx 32rpx 76rpx;background:#481916;color:#fff7ea}.login__hero:after{content:'知行';position:absolute;right:-25rpx;top:65rpx;color:rgba(255,255,255,.035);font:160rpx/1 var(--font-display);writing-mode:vertical-rl}.login__edition{display:flex;justify-content:space-between;padding-bottom:18rpx;border-bottom:1rpx solid rgba(216,185,111,.32);color:#d7b86d;font:15rpx Georgia,serif;letter-spacing:2rpx}.login__edition b{font-weight:400}.login__brand{position:relative;z-index:1;display:flex;align-items:center;gap:24rpx;padding:42rpx 4rpx 32rpx}.login__seal{display:grid;place-items:center;width:92rpx;height:92rpx;flex:none;border:2rpx solid #d7b86d;transform:rotate(-3deg)}.login__seal:before{content:'';position:absolute;width:76rpx;height:76rpx;border:1rpx solid rgba(215,184,109,.45)}.login__seal span{position:relative;font:56rpx/1 var(--font-display);color:#f0d58f}.login__kicker{color:#d7b86d;font-size:17rpx;letter-spacing:4rpx}.login__brand h1{margin:7rpx 0 3rpx;font:700 42rpx/1.2 var(--font-display);letter-spacing:2rpx}.login__brand p{margin:0;color:rgba(255,247,234,.62);font-size:20rpx}.login__quote{display:flex;align-items:center;gap:14rpx;color:rgba(255,247,234,.62);font-size:18rpx}.login__quote i{width:34rpx;height:1rpx;background:#d7b86d}
.login__content{position:relative;z-index:2;padding:0 24rpx;margin-top:-42rpx}.login__card{padding:30rpx;border:1rpx solid #d7ccbd;border-radius:20rpx;background:#fffdf7;box-shadow:0 24rpx 60rpx rgba(55,36,22,.14)}.login__card>header{padding-bottom:24rpx;border-bottom:1rpx solid #e5dbce}.login__card>header span{color:var(--color-primary);font:14rpx Georgia,serif;letter-spacing:3rpx}.login__card>header h2{margin:5rpx 0 2rpx;font-size:32rpx}.login__card>header p{margin:0;color:var(--color-text-muted);font-size:19rpx}.login__phone-section{padding-top:24rpx}.login__input-group{margin-bottom:20rpx}.login__input-label{display:flex;align-items:center;gap:10rpx;margin-bottom:9rpx;color:var(--color-text-secondary);font-size:21rpx}.login__input-label b{color:#a88350;font:15rpx Georgia,serif}.login__input{height:78rpx;padding:0 20rpx;border-radius:10rpx;background:#f6f0e7;font-size:25rpx}.login__submit{display:flex;align-items:center;justify-content:space-between;width:100%;height:80rpx;margin-top:8rpx;padding:0 24rpx;border-radius:10rpx;background:var(--color-primary);box-shadow:0 10rpx 24rpx rgba(127,33,29,.18)}.login__submit-text{color:#fff8ec;font:700 25rpx var(--font-display);letter-spacing:2rpx}.login__submit i{color:#e3c77e;font:28rpx Georgia,serif}.login__yiban-btn{display:grid;grid-template-columns:38rpx 1fr auto;align-items:center;gap:12rpx;width:100%;margin-top:24rpx;padding:17rpx 18rpx;border:1rpx solid #ddd2c3;border-radius:10rpx;background:#f8f3eb;text-align:left}.login__yiban-icon{width:34rpx;height:34rpx}.login__yiban-text{color:#655b51;font-size:21rpx}.login__yiban-btn small{color:#a29587;font-size:16rpx}.login__yiban-btn.disabled{filter:grayscale(.6);opacity:.72}.login__agreement{display:flex;justify-content:center;flex-wrap:wrap;margin-top:22rpx;gap:4rpx}.login__agreement-text,.login__agreement-link{font-size:18rpx}.login__agreement-text{color:var(--color-text-muted)}.login__agreement-link{color:var(--color-primary)}
</style>
