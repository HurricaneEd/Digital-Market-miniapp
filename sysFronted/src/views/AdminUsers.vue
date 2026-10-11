<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Search } from '@element-plus/icons-vue'
import AdminLayout from '@/components/AdminLayout.vue'
import request, { getApiErrorMessage } from '@/utils/requests'
import { useUserStore } from '@/store/user'

const userStore = useUserStore()
const loading = ref(false)
const saving = ref(false)
const users = ref([])
const total = ref(0)
const dialogVisible = ref(false)
const formRef = ref()
const query = reactive({ page: 1, page_size: 10, search: '', is_active: '' })
const form = reactive({
  id: null,
  username: '',
  nickname: '',
  email: '',
  phone: '',
  password: '',
  is_active: true,
})

const rules = {
  email: [{ type: 'email', message: '邮箱格式不正确', trigger: 'blur' }],
  phone: [{
    pattern: /^$|^1[3-9]\d{9}$/,
    message: '手机号格式不正确',
    trigger: 'blur',
  }],
  password: [{ min: 6, message: '新密码至少 6 位', trigger: 'blur' }],
}

async function fetchUsers() {
  loading.value = true
  try {
    const params = { page: query.page, page_size: query.page_size }
    if (query.search.trim()) params.search = query.search.trim()
    if (query.is_active !== '') params.is_active = query.is_active
    const response = await request.get('/admin/users/', { params })
    users.value = response.results || []
    total.value = response.count || 0
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '用户列表读取失败'))
  } finally {
    loading.value = false
  }
}

function searchUsers() {
  query.page = 1
  fetchUsers()
}

function openEditDialog(user) {
  Object.assign(form, {
    id: user.id,
    username: user.username,
    nickname: user.nickname || '',
    email: user.email || '',
    phone: user.phone || '',
    password: '',
    is_active: user.is_active,
  })
  dialogVisible.value = true
}

async function submitUser() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  const payload = {
    nickname: form.nickname.trim(),
    email: form.email.trim() || null,
    phone: form.phone.trim() || null,
    is_active: form.is_active,
  }
  if (form.password) payload.password = form.password

  saving.value = true
  try {
    await request.patch(`/admin/users/${form.id}/`, payload)
    ElMessage.success('用户资料已更新')
    dialogVisible.value = false
    await fetchUsers()
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '用户资料更新失败'))
  } finally {
    saving.value = false
  }
}

async function deleteUser(user) {
  try {
    await ElMessageBox.confirm(
      `确定删除用户「${user.username}」吗？存在历史订单的用户不能删除。`,
      '删除用户',
      { confirmButtonText: '删除用户', cancelButtonText: '返回', type: 'warning' },
    )
    await request.delete(`/admin/users/${user.id}/`)
    ElMessage.success('用户已删除')
    await fetchUsers()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error(getApiErrorMessage(error, '用户删除失败'))
    }
  }
}

function formatDate(value) {
  if (!value) return '从未登录'
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

onMounted(fetchUsers)
</script>

<template>
  <AdminLayout current-title="用户管理">
    <section class="page-intro">
      <div>
        <h2>用户账号</h2>
        <p>查看账号资料、启用状态和最近登录时间。</p>
      </div>
      <el-button :icon="Refresh" :loading="loading" @click="fetchUsers">刷新</el-button>
    </section>

    <section class="toolbar">
      <el-input
        v-model="query.search"
        clearable
        placeholder="搜索用户名、邮箱或手机号"
        class="search-input"
        @keyup.enter="searchUsers"
        @clear="searchUsers"
      >
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <el-select v-model="query.is_active" clearable placeholder="全部状态" class="status-select" @change="searchUsers">
        <el-option label="正常" :value="true" />
        <el-option label="已停用" :value="false" />
      </el-select>
      <el-button @click="searchUsers">搜索</el-button>
    </section>

    <section class="table-frame" v-loading="loading">
      <el-table :data="users" empty-text="暂无用户" style="width: 100%">
        <el-table-column label="账号" min-width="190">
          <template #default="{ row }">
            <div class="user-cell">
              <el-avatar :size="34" :src="userStore.getAvatarUrl(row.avatar)">{{ (row.nickname || row.username || '?').slice(0, 1) }}</el-avatar>
              <div>
                <strong>{{ row.username }}</strong>
                <span v-if="row.nickname">{{ row.nickname }}</span>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="email" label="邮箱" min-width="180">
          <template #default="{ row }">{{ row.email || '—' }}</template>
        </el-table-column>
        <el-table-column prop="phone" label="手机号" min-width="130">
          <template #default="{ row }">{{ row.phone || '—' }}</template>
        </el-table-column>
        <el-table-column label="角色" width="110">
          <template #default="{ row }">{{ row.is_superuser ? '超级管理员' : row.is_staff ? '管理员' : '用户' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <span class="status-dot" :class="{ 'is-active': row.is_active }" />
            {{ row.is_active ? '正常' : '已停用' }}
          </template>
        </el-table-column>
        <el-table-column label="注册时间" min-width="160">
          <template #default="{ row }">{{ formatDate(row.date_joined) }}</template>
        </el-table-column>
        <el-table-column label="最近登录" min-width="160">
          <template #default="{ row }">{{ formatDate(row.last_login) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button link @click="openEditDialog(row)">编辑</el-button>
            <el-button v-if="!row.is_superuser" link type="danger" @click="deleteUser(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <div class="pagination-row">
      <span>共 {{ total.toLocaleString('zh-CN') }} 位用户</span>
      <el-pagination
        v-model:current-page="query.page"
        :page-size="query.page_size"
        :total="total"
        layout="prev, pager, next"
        @current-change="fetchUsers"
      />
    </div>

    <el-dialog v-model="dialogVisible" title="编辑用户" width="520px">
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
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
        <el-form-item label="重置密码" prop="password">
          <el-input v-model="form.password" type="password" show-password autocomplete="new-password" placeholder="留空则不修改，至少 6 位" />
        </el-form-item>
        <el-form-item label="账号状态">
          <el-switch v-model="form.is_active" active-text="正常" inactive-text="停用" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">返回</el-button>
        <el-button type="primary" :loading="saving" @click="submitUser">保存修改</el-button>
      </template>
    </el-dialog>
  </AdminLayout>
</template>

<style scoped>
.page-intro,
.pagination-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

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

.toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.search-input {
  width: min(100%, 410px);
}

.status-select {
  width: 150px;
}

.table-frame {
  border: 1px solid var(--hairline-soft);
  background: var(--canvas);
}

.user-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.user-cell > div {
  display: grid;
  gap: 4px;
}

.user-cell strong {
  font-size: 13px;
  font-weight: 500;
}

.user-cell span {
  color: var(--mute);
  font-size: 11px;
}

.status-dot {
  display: inline-block;
  width: 7px;
  height: 7px;
  margin-right: 6px;
  border-radius: 50%;
  background: var(--hairline);
  vertical-align: 1px;
}

.status-dot.is-active {
  background: var(--success);
}

.pagination-row {
  margin-top: 16px;
  color: var(--mute);
  font-size: 12px;
}

@media (max-width: 720px) {
  .page-intro,
  .pagination-row {
    align-items: flex-start;
    flex-direction: column;
  }
}

@media (max-width: 520px) {
  .page-intro h2 {
    font-size: 21px;
  }

  .toolbar {
    flex-wrap: wrap;
  }

  .search-input {
    width: 100%;
  }

  .status-select {
    flex: 1;
  }
}
</style>
