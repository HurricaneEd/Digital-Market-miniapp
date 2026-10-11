<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowRight, Lock, User } from '@element-plus/icons-vue'
import request, { getApiErrorMessage } from '@/utils/requests'
import { useUserStore } from '@/store/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const loading = ref(false)
const formRef = ref()
const form = reactive({ identifier: '', password: '' })

const rules = {
  identifier: [{ required: true, message: '请输入账号、手机号或邮箱', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function handleLogin() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    const result = await request.post('/users/login/', form)
    const profile = result.user_profile || {}
    if (!profile.is_staff) {
      ElMessage.error('当前账号没有管理后台访问权限')
      return
    }

    userStore.login({ token: result.token, user_profile: profile })
    const redirect = typeof route.query.redirect === 'string'
      && route.query.redirect.startsWith('/admin')
      && route.query.redirect !== '/admin/login'
      ? route.query.redirect
      : '/admin'
    await router.replace(redirect)
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '登录失败，请检查账号和密码'))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="login-page">
    <section class="login-panel">
      <div class="login-brand">
        <span class="brand-mark">D</span>
        <div>
          <strong>DigRecSys</strong>
          <span>管理后台</span>
        </div>
      </div>

      <div class="login-heading">
        <span class="eyebrow">ADMINISTRATION</span>
        <h1>管理员登录</h1>
        <p>使用已开通后台权限的账号继续。</p>
      </div>

      <el-alert
        v-if="route.query.reason === 'expired'"
        title="登录状态已失效，请重新登录。"
        type="warning"
        :closable="false"
        class="login-alert"
      />
      <el-alert
        v-else-if="route.query.reason === 'forbidden'"
        title="该账号没有后台访问权限。"
        type="warning"
        :closable="false"
        class="login-alert"
      />

      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="handleLogin">
        <el-form-item label="账号" prop="identifier">
          <el-input
            v-model="form.identifier"
            autocomplete="username"
            placeholder="用户名、手机号或邮箱"
            size="large"
            :prefix-icon="User"
          />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            autocomplete="current-password"
            placeholder="请输入密码"
            size="large"
            :prefix-icon="Lock"
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        <el-button class="login-submit" type="primary" native-type="submit" size="large" :loading="loading">
          进入管理后台
          <el-icon class="submit-icon"><ArrowRight /></el-icon>
        </el-button>
      </el-form>

      <p class="login-footnote">后台权限由系统管理员分配。</p>
    </section>
  </main>
</template>

<style scoped>
.login-page {
  display: grid;
  min-height: 100vh;
  place-items: center;
  background: var(--soft-cloud);
  padding: 24px;
}

.login-panel {
  width: min(100%, 440px);
  border: 1px solid var(--hairline-soft);
  background: var(--canvas);
  padding: 38px 40px 30px;
}

.login-brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-mark {
  display: grid;
  width: 38px;
  height: 38px;
  place-items: center;
  border-radius: 50%;
  background: var(--ink);
  color: white;
  font-size: 17px;
  font-weight: 700;
}

.login-brand div {
  display: grid;
  gap: 2px;
}

.login-brand strong {
  font-size: 15px;
  font-weight: 600;
}

.login-brand span:not(.brand-mark),
.login-heading p,
.login-footnote {
  color: var(--mute);
  font-size: 12px;
}

.login-heading {
  margin: 44px 0 28px;
}

.eyebrow {
  color: var(--mute);
  font-size: 10px;
  letter-spacing: 0.08em;
}

.login-heading h1 {
  margin: 10px 0 8px;
  font-size: 28px;
  font-weight: 500;
}

.login-heading p {
  margin: 0;
  font-size: 14px;
}

.login-alert {
  margin: -8px 0 22px;
}

.login-submit {
  width: 100%;
  min-height: 48px;
  margin-top: 8px;
  padding: 0 22px;
}

.submit-icon {
  margin-left: 8px;
}

.login-footnote {
  margin: 24px 0 0;
  text-align: center;
}

@media (max-width: 480px) {
  .login-panel {
    padding: 30px 22px 26px;
  }

  .login-heading {
    margin-top: 36px;
  }
}
</style>
