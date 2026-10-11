<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Box,
  DataAnalysis,
  Document,
  User,
} from '@element-plus/icons-vue'
import { useUserStore } from '@/store/user'

defineProps({
  currentTitle: {
    type: String,
    default: '管理概览',
  },
})

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const menuItems = [
  { title: '管理概览', path: '/admin', icon: DataAnalysis },
  { title: '商品管理', path: '/admin/products', icon: Box },
  { title: '订单管理', path: '/admin/orders', icon: Document },
  { title: '用户管理', path: '/admin/users', icon: User },
]

const activePath = computed(() => route.path)
const displayName = computed(() => (
  userStore.userInfo?.nickname || userStore.userInfo?.username || '管理员'
))

function handleLogout() {
  userStore.logout()
  ElMessage.success('已退出管理后台')
  router.replace({ name: 'admin-login' })
}
</script>

<template>
  <div class="admin-shell">
    <aside class="sidebar">
      <router-link class="brand" to="/admin" aria-label="DigRecSys 管理后台首页">
        <span class="brand-mark">D</span>
        <span class="brand-copy">
          <strong>DigRecSys</strong>
          <small>管理后台</small>
        </span>
      </router-link>

      <nav class="side-nav" aria-label="管理导航">
        <router-link
          v-for="item in menuItems"
          :key="item.path"
          :to="item.path"
          class="nav-link"
          :class="{ 'is-active': activePath === item.path }"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.title }}</span>
        </router-link>
      </nav>

      <div class="sidebar-note">
        <span class="note-label">项目</span>
        <strong>数码商品交易系统</strong>
        <span>目录、订单与账号管理</span>
      </div>
    </aside>

    <div class="admin-workspace">
      <header class="topbar">
        <div class="heading-group">
          <span class="eyebrow">DIGRECSYS / ADMIN</span>
          <h1>{{ currentTitle }}</h1>
        </div>

        <el-dropdown trigger="click" @command="(command) => command === 'logout' ? handleLogout() : router.push('/admin/profile')">
          <button class="account-button" type="button">
            <el-avatar :src="userStore.getUserAvatar()" :size="36">
              {{ displayName.slice(0, 1) }}
            </el-avatar>
            <span class="account-name">{{ displayName }}</span>
            <span class="account-role">管理员</span>
          </button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="profile">个人资料</el-dropdown-item>
              <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </header>

      <nav class="mobile-nav" aria-label="管理导航">
        <router-link
          v-for="item in menuItems"
          :key="item.path"
          :to="item.path"
          :class="{ 'is-active': activePath === item.path }"
        >
          {{ item.title }}
        </router-link>
      </nav>

      <main class="page-content">
        <slot />
      </main>
    </div>
  </div>
</template>

<style scoped>
.admin-shell {
  display: flex;
  min-height: 100vh;
  background: var(--soft-cloud);
}

.sidebar {
  position: fixed;
  inset: 0 auto 0 0;
  z-index: 5;
  display: flex;
  width: 232px;
  flex-direction: column;
  border-right: 1px solid var(--hairline-soft);
  background: var(--canvas);
  padding: 24px 16px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px 8px 28px;
}

.brand-mark {
  display: grid;
  width: 36px;
  height: 36px;
  place-items: center;
  border-radius: 50%;
  background: var(--ink);
  color: white;
  font-size: 17px;
  font-weight: 700;
}

.brand-copy {
  display: grid;
  gap: 2px;
}

.brand-copy strong {
  font-size: 15px;
  font-weight: 600;
}

.brand-copy small,
.note-label {
  color: var(--mute);
  font-size: 11px;
}

.side-nav {
  display: grid;
  gap: 6px;
}

.nav-link {
  display: flex;
  min-height: 44px;
  align-items: center;
  gap: 12px;
  border-radius: 999px;
  color: var(--charcoal);
  padding: 0 14px;
  transition: background-color 120ms ease, color 120ms ease;
}

.nav-link .el-icon {
  font-size: 17px;
}

.nav-link:hover {
  background: var(--soft-cloud);
}

.nav-link.is-active {
  background: var(--ink);
  color: white;
}

.sidebar-note {
  display: grid;
  gap: 8px;
  margin-top: auto;
  border-top: 1px solid var(--hairline-soft);
  padding: 20px 8px 4px;
  color: var(--mute);
  font-size: 12px;
}

.sidebar-note strong {
  color: var(--ink);
  font-size: 13px;
  font-weight: 500;
}

.admin-workspace {
  width: calc(100% - 232px);
  min-width: 0;
  min-height: 100vh;
  margin-left: 232px;
}

.topbar {
  display: flex;
  min-height: 92px;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--hairline-soft);
  background: var(--canvas);
  padding: 16px 36px;
}

.heading-group {
  display: grid;
  gap: 5px;
}

.eyebrow {
  color: var(--mute);
  font-size: 10px;
  letter-spacing: 0.08em;
}

.heading-group h1 {
  margin: 0;
  font-size: 20px;
  font-weight: 500;
}

.account-button {
  display: flex;
  align-items: center;
  gap: 10px;
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: var(--ink);
  cursor: pointer;
  padding: 4px 8px;
}

.account-button:hover {
  background: var(--soft-cloud);
}

.account-name {
  font-size: 13px;
}

.account-role {
  color: var(--mute);
  font-size: 11px;
}

.page-content {
  max-width: 1600px;
  margin: 0 auto;
  padding: 32px 36px 56px;
}

.mobile-nav {
  display: none;
}

@media (max-width: 900px) {
  .sidebar {
    width: 196px;
  }

  .admin-workspace {
    width: calc(100% - 196px);
    margin-left: 196px;
  }

  .topbar {
    padding-right: 24px;
    padding-left: 24px;
  }

  .page-content {
    padding-right: 24px;
    padding-left: 24px;
  }
}

@media (max-width: 680px) {
  .admin-shell {
    display: block;
  }

  .sidebar {
    position: static;
    width: 100%;
    height: 62px;
    flex-direction: row;
    align-items: center;
    border-right: 0;
    border-bottom: 1px solid var(--hairline-soft);
    padding: 8px 16px;
  }

  .brand {
    padding: 0;
  }

  .brand-mark {
    width: 32px;
    height: 32px;
  }

  .side-nav,
  .sidebar-note {
    display: none;
  }

  .admin-workspace {
    width: 100%;
    min-height: calc(100vh - 62px);
    margin-left: 0;
  }

  .topbar {
    min-height: 74px;
    padding: 12px 16px;
  }

  .heading-group h1 {
    font-size: 18px;
  }

  .account-button {
    gap: 6px;
  }

  .account-role {
    display: none;
  }

  .mobile-nav {
    display: flex;
    gap: 4px;
    overflow-x: auto;
    border-bottom: 1px solid var(--hairline-soft);
    background: var(--canvas);
    padding: 8px 12px;
  }

  .mobile-nav a {
    flex: 0 0 auto;
    border-radius: 999px;
    color: var(--charcoal);
    padding: 8px 13px;
    white-space: nowrap;
  }

  .mobile-nav a.is-active {
    background: var(--ink);
    color: white;
  }

  .page-content {
    padding: 20px 14px 36px;
  }
}
</style>
