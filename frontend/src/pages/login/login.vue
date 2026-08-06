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
        <header>
          <span>{{ mode === 'login' ? 'ACCOUNT ACCESS' : 'NEW ACCOUNT' }}</span>
          <h2>{{ mode === 'login' ? '账号登录' : '创建账号' }}</h2>
          <p>{{ mode === 'login' ? '使用已有账号进入学习空间' : '无需验证码，设置密码即可完成注册' }}</p>
        </header>
        <div class="login__mode-switch" aria-label="账号操作方式">
          <button :class="{ active: mode === 'login' }" @click="setMode('login')">账号登录</button>
          <button :class="{ active: mode === 'register' }" @click="setMode('register')">新用户注册</button>
        </div>
        <div class="login__phone-section">
          <div class="login__input-group">
            <span class="login__input-label"><b>01</b> 手机号</span>
            <input class="login__input" v-model="phone" type="tel" maxlength="11" placeholder="请输入11位手机号" placeholder-class="login__placeholder" />
          </div>
          <div class="login__input-group">
            <span class="login__input-label"><b>02</b> 密码</span>
            <input class="login__input" v-model="password" type="password" maxlength="128" placeholder="请输入密码（至少6位）" placeholder-class="login__placeholder" />
          </div>
          <div v-if="mode === 'register'" class="login__input-group">
            <span class="login__input-label"><b>03</b> 确认密码</span>
            <input class="login__input" v-model="confirmPassword" type="password" maxlength="128" placeholder="请再次输入密码" placeholder-class="login__placeholder" @confirm="handleSubmit" />
          </div>
          <button v-if="mode === 'register'" class="login__consent" :class="{ checked: agreed }" @click="agreed = !agreed">
            <span class="login__check">{{ agreed ? '✓' : '' }}</span>
            <span>我已阅读并同意用户服务协议和隐私政策</span>
          </button>
          <button class="login__submit" :disabled="submitting" @click="handleSubmit">
            <span class="login__submit-text">{{ submitLabel }}</span><i>{{ submitting ? '…' : '→' }}</i>
          </button>
        </div>
        <button v-if="mode === 'login'" class="login__yiban-btn" :class="{ disabled: !yibanAvailable }" @click="handleYibanLogin">
          <img class="login__yiban-icon" :src="yibanIcon" style="object-fit:contain;display:block;max-width:100%">
          <span class="login__yiban-text">{{ yibanAvailable ? '使用易班统一登录' : '易班登录暂未配置' }}</span><small>学校统一身份</small>
        </button>
        <div class="login__agreement">
          <span class="login__agreement-text">{{ mode === 'login' ? '登录即代表同意' : '注册前请阅读' }}</span>
          <span class="login__agreement-link" @click="showAgreement('service')">《用户服务协议》</span>
          <span class="login__agreement-text">和</span>
          <span class="login__agreement-link" @click="showAgreement('privacy')">《隐私政策》</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onLoad } from '@dcloudio/uni-app'
import { computed, ref } from 'vue'
import { useUserStore } from '@/store/user'
import { userApi } from '@/api/user'
import yibanIcon from '@/static/images/icons/yiban.png'

const userStore = useUserStore()
type AuthMode = 'login' | 'register'

const mode = ref<AuthMode>('login')
const phone = ref('')
const password = ref('')
const confirmPassword = ref('')
const agreed = ref(false)
const submitting = ref(false)
const yibanAvailable = ref(false)
const yibanMessage = ref('')
const submitLabel = computed(() => {
  if (submitting.value) return mode.value === 'login' ? '正在登录' : '正在注册'
  return mode.value === 'login' ? '进入工坊' : '注册并进入'
})

onLoad(async () => {
  try {
    const status = await userApi.getYibanStatus()
    yibanAvailable.value = Boolean(status?.available)
    yibanMessage.value = status?.message || ''
  } catch { /* 后端不可达时维持默认“未配置”文案 */ }
})

async function handleYibanLogin() {
  uni.showModal({
    title: '易班统一登录',
    content: yibanMessage.value || '当前部署尚未配置学校易班 OAuth 服务，系统不会模拟登录或绑定。请由管理员完成应用参数和换票地址配置。',
    showCancel: false,
  })
}

function showAgreement(type: 'service' | 'privacy') {
  const content = type === 'service' ? '本平台用于思政学习与训练。请使用本人账号，不发布违法、侵权或虚假内容；AI 生成内容仅作学习辅助。' : '平台仅保存完成业务所需的账号资料、学习记录和用户主动提交的内容，不会把数据用于未经说明的用途。'
  uni.showModal({ title: type === 'service' ? '用户服务协议摘要' : '隐私政策摘要', content, showCancel: false })
}

function setMode(value: AuthMode) {
  if (submitting.value || mode.value === value) return
  mode.value = value
  confirmPassword.value = ''
  agreed.value = false
}

async function handleSubmit() {
  if (submitting.value) return
  const normalizedPhone = phone.value.trim()
  if (!/^1\d{10}$/.test(normalizedPhone) || password.value.length < 6) {
    uni.showToast({ title: '请输入正确手机号和至少6位密码', icon: 'none' })
    return
  }
  if (mode.value === 'register' && password.value !== confirmPassword.value) {
    uni.showToast({ title: '两次输入的密码不一致', icon: 'none' })
    return
  }
  if (mode.value === 'register' && !agreed.value) {
    uni.showToast({ title: '请先阅读并同意服务协议与隐私政策', icon: 'none' })
    return
  }
  submitting.value = true
  try {
    const credentials = { phone: normalizedPhone, password: password.value }
    if (mode.value === 'register') await userStore.register(credentials)
    else await userStore.login(credentials)
    uni.showToast({ title: mode.value === 'register' ? '注册成功' : '登录成功', icon: 'success' })
    uni.switchTab({ url: '/pages/index/index' })
  } catch {
    // API 层统一显示后端返回的中文错误信息。
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.login{min-height:100vh;padding-bottom:40rpx;background:#eee8de;color:var(--color-text)}
.login__hero{position:relative;overflow:hidden;padding:34rpx 32rpx 76rpx;background:#481916;color:#fff7ea}.login__hero:after{content:'知行';position:absolute;right:-25rpx;top:65rpx;color:rgba(255,255,255,.035);font:160rpx/1 var(--font-display);writing-mode:vertical-rl}.login__edition{display:flex;justify-content:space-between;padding-bottom:18rpx;border-bottom:1rpx solid rgba(216,185,111,.32);color:#d7b86d;font:15rpx Georgia,serif;letter-spacing:2rpx}.login__edition b{font-weight:400}.login__brand{position:relative;z-index:1;display:flex;align-items:center;gap:24rpx;padding:42rpx 4rpx 32rpx}.login__seal{display:grid;place-items:center;width:92rpx;height:92rpx;flex:none;border:2rpx solid #d7b86d;transform:rotate(-3deg)}.login__seal:before{content:'';position:absolute;width:76rpx;height:76rpx;border:1rpx solid rgba(215,184,109,.45)}.login__seal span{position:relative;font:56rpx/1 var(--font-display);color:#f0d58f}.login__kicker{color:#d7b86d;font-size:17rpx;letter-spacing:4rpx}.login__brand h1{margin:7rpx 0 3rpx;font:700 42rpx/1.2 var(--font-display);letter-spacing:2rpx}.login__brand p{margin:0;color:rgba(255,247,234,.62);font-size:20rpx}.login__quote{display:flex;align-items:center;gap:14rpx;color:rgba(255,247,234,.62);font-size:18rpx}.login__quote i{width:34rpx;height:1rpx;background:#d7b86d}
.login__content{position:relative;z-index:2;padding:0 24rpx;margin-top:-42rpx}.login__card{padding:30rpx;border:1rpx solid #d7ccbd;border-radius:20rpx;background:#fffdf7;box-shadow:0 24rpx 60rpx rgba(55,36,22,.14)}.login__card>header{padding-bottom:24rpx;border-bottom:1rpx solid #e5dbce}.login__card>header span{color:var(--color-primary);font:14rpx Georgia,serif;letter-spacing:3rpx}.login__card>header h2{margin:5rpx 0 2rpx;font-size:32rpx}.login__card>header p{margin:0;color:var(--color-text-muted);font-size:19rpx}.login__mode-switch{display:grid;grid-template-columns:1fr 1fr;gap:6rpx;margin-top:22rpx;padding:5rpx;border:1rpx solid #dfd4c5;border-radius:12rpx;background:#f1e9de}.login__mode-switch button{height:62rpx;border-radius:8rpx;color:#837669;font-size:21rpx;transition:background .2s ease,color .2s ease,box-shadow .2s ease}.login__mode-switch button.active{background:#fffdf8;color:var(--color-primary);font-weight:700;box-shadow:0 4rpx 14rpx rgba(72,25,22,.1)}.login__phone-section{padding-top:24rpx}.login__input-group{margin-bottom:20rpx}.login__input-label{display:flex;align-items:center;gap:10rpx;margin-bottom:9rpx;color:var(--color-text-secondary);font-size:21rpx}.login__input-label b{color:#a88350;font:15rpx Georgia,serif}.login__input{box-sizing:border-box;width:100%;height:78rpx;padding:0 20rpx;border:1rpx solid transparent;border-radius:10rpx;background:#f6f0e7;font-size:25rpx;transition:border-color .2s ease,background .2s ease}.login__input:focus{border-color:#bd9a62;background:#fbf7f0}.login__consent{display:flex;align-items:center;gap:12rpx;width:100%;margin:-2rpx 0 18rpx;color:#776b60;text-align:left;font-size:18rpx}.login__check{display:grid;place-items:center;box-sizing:border-box;width:30rpx;height:30rpx;flex:none;border:1rpx solid #b7a995;border-radius:5rpx;background:#fff;color:#fff;font-size:18rpx}.login__consent.checked .login__check{border-color:var(--color-primary);background:var(--color-primary)}.login__submit{display:flex;align-items:center;justify-content:space-between;width:100%;height:80rpx;margin-top:8rpx;padding:0 24rpx;border-radius:10rpx;background:var(--color-primary);box-shadow:0 10rpx 24rpx rgba(127,33,29,.18)}.login__submit:disabled{opacity:.64}.login__submit-text{color:#fff8ec;font:700 25rpx var(--font-display);letter-spacing:2rpx}.login__submit i{color:#e3c77e;font:28rpx Georgia,serif}.login__yiban-btn{display:grid;grid-template-columns:38rpx 1fr auto;align-items:center;gap:12rpx;width:100%;margin-top:24rpx;padding:17rpx 18rpx;border:1rpx solid #ddd2c3;border-radius:10rpx;background:#f8f3eb;text-align:left}.login__yiban-icon{width:34rpx;height:34rpx}.login__yiban-text{color:#655b51;font-size:21rpx}.login__yiban-btn small{color:#a29587;font-size:16rpx}.login__yiban-btn.disabled{filter:grayscale(.6);opacity:.72}.login__agreement{display:flex;justify-content:center;flex-wrap:wrap;margin-top:22rpx;gap:4rpx}.login__agreement-text,.login__agreement-link{font-size:18rpx}.login__agreement-text{color:var(--color-text-muted)}.login__agreement-link{color:var(--color-primary)}
</style>
