<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Box, DataAnalysis, Document, User } from '@element-plus/icons-vue'
import AdminLayout from '@/components/AdminLayout.vue'
import request, { getApiErrorMessage } from '@/utils/requests'
import { useUserStore } from '@/store/user'

const userStore = useUserStore()
const loading = ref(false)
const errorMessage = ref('')
const totals = ref({ users: 0, products: 0, orders: 0, paidOrders: 0 })
const recentOrders = ref([])

const statistics = computed(() => [
  { label: '用户总数', value: totals.value.users, icon: User },
  { label: '商品总数', value: totals.value.products, icon: Box },
  { label: '订单总数', value: totals.value.orders, icon: Document },
  { label: '待发货订单', value: totals.value.paidOrders, icon: DataAnalysis },
])

const statusLabels = {
  unpaid: '待支付',
  paid: '待发货',
  shipped: '已发货',
  completed: '已完成',
  cancelled: '已取消',
}

function formatDate(value) {
  if (!value) return '—'
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

async function fetchOverview() {
  loading.value = true
  errorMessage.value = ''
  try {
    const [users, products, orders, paidOrders] = await Promise.all([
      request.get('/admin/users/', { params: { page: 1, page_size: 1 } }),
      request.get('/admin/products/', { params: { page: 1, page_size: 1 } }),
      request.get('/admin/orders/', { params: { page: 1 } }),
      request.get('/admin/orders/', { params: { page: 1, status: 'paid' } }),
    ])

    totals.value = {
      users: users.count ?? users.results?.length ?? 0,
      products: products.count ?? products.results?.length ?? 0,
      orders: orders.count ?? orders.results?.length ?? 0,
      paidOrders: paidOrders.count ?? paidOrders.results?.length ?? 0,
    }
    recentOrders.value = (orders.results || []).slice(0, 6)
  } catch (error) {
    errorMessage.value = getApiErrorMessage(error, '暂时无法读取后台数据')
    ElMessage.error(errorMessage.value)
  } finally {
    loading.value = false
  }
}

onMounted(fetchOverview)
</script>

<template>
  <AdminLayout current-title="管理概览">
    <section class="overview-intro">
      <div>
        <span class="eyebrow">STORE OPERATIONS</span>
        <h2>你好，{{ userStore.userInfo?.nickname || userStore.userInfo?.username || '管理员' }}</h2>
        <p>查看目录和交易的当前状态。</p>
      </div>
      <el-button :loading="loading" @click="fetchOverview">刷新数据</el-button>
    </section>

    <el-alert
      v-if="errorMessage"
      :title="errorMessage"
      type="error"
      :closable="false"
      class="overview-alert"
    />

    <section class="stats-grid" aria-label="运营统计" v-loading="loading">
      <article v-for="stat in statistics" :key="stat.label" class="stat-item">
        <div class="stat-head">
          <span>{{ stat.label }}</span>
          <el-icon><component :is="stat.icon" /></el-icon>
        </div>
        <strong>{{ stat.value.toLocaleString('zh-CN') }}</strong>
      </article>
    </section>

    <section class="dashboard-columns">
      <div class="section-heading">
        <div>
          <h3>最近订单</h3>
          <p>按创建时间倒序排列</p>
        </div>
        <router-link class="text-link" to="/admin/orders">查看全部</router-link>
      </div>

      <div class="table-frame" v-loading="loading">
        <el-table :data="recentOrders" empty-text="暂无订单" style="width: 100%">
          <el-table-column prop="order_sn" label="订单号" min-width="170" />
          <el-table-column prop="username" label="用户" min-width="120" />
          <el-table-column label="金额" width="130" align="right">
            <template #default="{ row }">¥{{ row.total_price }}</template>
          </el-table-column>
          <el-table-column label="状态" width="110">
            <template #default="{ row }">{{ statusLabels[row.status] || row.status }}</template>
          </el-table-column>
          <el-table-column label="创建时间" min-width="170">
            <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
          </el-table-column>
        </el-table>
      </div>
    </section>

    <section class="quick-links">
      <router-link to="/admin/products">
        <span>目录维护</span>
        <strong>管理商品、价格和库存</strong>
      </router-link>
      <router-link to="/admin/users">
        <span>账号管理</span>
        <strong>查看用户状态和资料</strong>
      </router-link>
    </section>
  </AdminLayout>
</template>

<style scoped>
.overview-intro,
.section-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
}

.overview-intro {
  margin-bottom: 28px;
}

.eyebrow {
  color: var(--mute);
  font-size: 10px;
  letter-spacing: 0.08em;
}

h2,
h3,
p {
  margin: 0;
}

.overview-intro h2 {
  margin-top: 8px;
  font-size: 26px;
  font-weight: 500;
}

.overview-intro p,
.section-heading p {
  margin-top: 7px;
  color: var(--mute);
}

.overview-alert {
  margin-bottom: 20px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  border: 1px solid var(--hairline-soft);
  background: var(--canvas);
}

.stat-item {
  min-height: 130px;
  padding: 20px 22px;
}

.stat-item + .stat-item {
  border-left: 1px solid var(--hairline-soft);
}

.stat-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: var(--mute);
  font-size: 13px;
}

.stat-head .el-icon {
  color: var(--ink);
  font-size: 18px;
}

.stat-item strong {
  display: block;
  margin-top: 20px;
  font-size: 30px;
  font-weight: 500;
  line-height: 1;
}

.dashboard-columns {
  margin-top: 40px;
}

.section-heading {
  margin-bottom: 16px;
}

.section-heading h3 {
  font-size: 18px;
  font-weight: 500;
}

.section-heading p {
  font-size: 12px;
}

.text-link {
  border-bottom: 1px solid currentColor;
  font-weight: 500;
  padding-bottom: 2px;
}

.table-frame {
  border: 1px solid var(--hairline-soft);
  background: var(--canvas);
}

.quick-links {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 24px;
}

.quick-links a {
  display: grid;
  gap: 9px;
  border: 1px solid var(--hairline-soft);
  background: var(--canvas);
  padding: 18px 20px;
  transition: border-color 120ms ease;
}

.quick-links a:hover {
  border-color: var(--ink);
}

.quick-links span {
  color: var(--mute);
  font-size: 12px;
}

.quick-links strong {
  font-size: 14px;
  font-weight: 500;
}

@media (max-width: 760px) {
  .stats-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .stat-item:nth-child(3) {
    border-left: 0;
    border-top: 1px solid var(--hairline-soft);
  }

  .stat-item:nth-child(4) {
    border-top: 1px solid var(--hairline-soft);
  }
}

@media (max-width: 520px) {
  .overview-intro {
    align-items: flex-start;
    flex-direction: column;
  }

  .overview-intro h2 {
    font-size: 22px;
  }

  .stat-item {
    min-height: 112px;
    padding: 16px;
  }

  .stat-item strong {
    font-size: 26px;
  }

  .quick-links {
    grid-template-columns: 1fr;
  }
}
</style>
