<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Camera } from '@element-plus/icons-vue'
import AdminLayout from '@/components/AdminLayout.vue'
import request, { getApiErrorMessage } from '@/utils/requests'
import { useUserStore } from '@/store/user'

const userStore = useUserStore()
const loading = ref(false)
const saving = ref(false)
const avatarLoading = ref(false)
const formRef = ref()
const form = reactive({ username: '', nickname: '', email: '', phone: '' })

const rules = {
  email: [{ type: 'email', message: '邮箱格式不正确', trigger: 'blur' }],
  phone: [{ pattern: /^$|^1[3-9]\d{9}$/, message: '手机号格式不正确', trigger: 'blur' }],
}

async function fetchProfile() {
  loading.value = true
  try {
    const profile = await request.get('/users/profile/')
    form.username = profile.username || ''
    form.nickname = profile.nickname || ''
    form.email = profile.email || ''
    form.phone = profile.phone || ''
    userStore.updateUserInfo(profile)
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '个人资料读取失败'))
  } finally {
    loading.value = false
  }
}

async function saveProfile() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    const profile = await request.put('/users/profile/', {
      nickname: form.nickname.trim(),
      email: form.email.trim(),
      phone: form.phone.trim(),
    })
    userStore.updateUserInfo(profile)
    ElMessage.success('个人资料已保存')
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '个人资料保存失败'))
  } finally {
    saving.value = false
  }
}

async function uploadAvatar(options) {
  const payload = new FormData()
  payload.append('avatar', options.file)
  avatarLoading.value = true
  try {
    const response = await request.post('/users/upload_avatar/', payload)
    userStore.updateUserInfo({ avatar: response.avatar_url || response.avatar })
    ElMessage.success('头像已更新')
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '头像上传失败'))
  } finally {
    avatarLoading.value = false
  }
}

onMounted(fetchProfile)
</script>

<template>
  <AdminLayout current-title="个人资料">
    <section class="page-intro">
      <div>
        <h2>个人资料</h2>
        <p>维护当前管理员的联系信息。</p>
      </div>
    </section>

    <section class="profile-panel" v-loading="loading">
      <div class="avatar-column">
        <el-avatar :size="88" :src="userStore.getUserAvatar()">
          {{ (form.nickname || form.username || 'D').slice(0, 1) }}
        </el-avatar>
        <el-upload
          accept="image/jpeg,image/png,image/gif,image/webp"
          :show-file-list="false"
          :http-request="uploadAvatar"
        >
          <el-button :icon="Camera" :loading="avatarLoading">更换头像</el-button>
        </el-upload>
        <span class="avatar-hint">支持 JPG、PNG、GIF 或 WebP，最大 5MB</span>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" class="profile-form">
        <el-form-item label="用户名">
          <el-input v-model="form.username" disabled />
        </el-form-item>
        <el-form-item label="昵称" prop="nickname">
          <el-input v-model="form.nickname" maxlength="50" placeholder="选填" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" type="email" placeholder="选填" />
        </el-form-item>
        <el-form-item label="手机号" prop="phone">
          <el-input v-model="form.phone" inputmode="tel" maxlength="11" placeholder="选填" />
        </el-form-item>
        <div class="profile-actions">
          <el-button type="primary" :loading="saving" @click="saveProfile">保存资料</el-button>
        </div>
      </el-form>
    </section>
  </AdminLayout>
</template>

<style scoped>
.page-intro {
  margin-bottom: 24px;
}

.page-intro h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 500;
}

.page-intro p {
  margin: 8px 0 0;
  color: var(--mute);
}

.profile-panel {
  display: grid;
  grid-template-columns: 210px minmax(0, 1fr);
  gap: 40px;
  border: 1px solid var(--hairline-soft);
  background: var(--canvas);
  padding: 30px;
}

.avatar-column {
  display: flex;
  align-items: center;
  flex-direction: column;
  gap: 14px;
  padding-top: 8px;
}

.avatar-hint {
  max-width: 180px;
  color: var(--mute);
  font-size: 11px;
  line-height: 1.6;
  text-align: center;
}

.profile-form {
  width: min(100%, 520px);
}

.profile-actions {
  margin-top: 12px;
}

@media (max-width: 680px) {
  .profile-panel {
    grid-template-columns: 1fr;
    gap: 24px;
    padding: 20px;
  }

  .page-intro h2 {
    font-size: 21px;
  }
}
</style>
