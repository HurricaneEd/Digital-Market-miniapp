<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Search } from '@element-plus/icons-vue'
import AdminLayout from '@/components/AdminLayout.vue'
import request, { getApiErrorMessage } from '@/utils/requests'

const loading = ref(false)
const orders = ref([])
const total = ref(0)
const selectedOrders = ref([])
const detailVisible = ref(false)
const currentOrder = ref(null)
const query = reactive({ page: 1, search: '', status: '' })

const pageSize = 12
const statusOptions = [
  { value: 'unpaid', label: '待支付' },
  { value: 'paid', label: '待发货' },
  { value: 'shipped', label: '已发货' },
  { value: 'completed', label: '已完成' },
  { value: 'cancelled', label: '已取消' },
]
const statusLabels = Object.fromEntries(statusOptions.map((item) => [item.value, item.label]))
const paymentLabels = { wechat: '微信支付', alipay: '支付宝' }
const shipEligible = computed(() => selectedOrders.value.filter((order) => order.status === 'paid'))
const cancelEligible = computed(() => selectedOrders.value.filter(
  (order) => ['unpaid', 'paid'].includes(order.status),
))

async function fetchOrders() {
  loading.value = true
  try {
    const params = { page: query.page }
    if (query.search.trim()) params.search = query.search.trim()
    if (query.status) params.status = query.status
    const response = await request.get('/admin/orders/', { params })
    orders.value = response.results || []
    total.value = response.count || 0
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '订单列表读取失败'))
  } finally {
    loading.value = false
  }
}

function searchOrders() {
  query.page = 1
  fetchOrders()
}

function showDetails(order) {
  currentOrder.value = order
  detailVisible.value = true
}

function formatDate(value) {
  if (!value) return '—'
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

async function shipOrder(order) {
  try {
    await ElMessageBox.confirm(`订单 ${order.order_sn} 将标记为已发货。`, '确认发货', {
      confirmButtonText: '确认发货',
      cancelButtonText: '返回',
      type: 'info',
    })
    await request.post(`/admin/orders/${encodeURIComponent(order.order_sn)}/ship/`)
    ElMessage.success('订单已发货')
    await fetchOrders()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error(getApiErrorMessage(error, '发货失败'))
    }
  }
}

async function cancelOrder(order) {
  try {
    await ElMessageBox.confirm(`确认取消订单 ${order.order_sn} 吗？`, '取消订单', {
      confirmButtonText: '确认取消',
      cancelButtonText: '返回',
      type: 'warning',
    })
    await request.post(`/admin/orders/${encodeURIComponent(order.order_sn)}/cancel/`)
    ElMessage.success('订单已取消')
    await fetchOrders()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error(getApiErrorMessage(error, '取消订单失败'))
    }
  }
}

async function runBatchAction(action) {
  const eligible = action === 'ship' ? shipEligible.value : cancelEligible.value
  if (!eligible.length) {
    ElMessage.warning(action === 'ship' ? '所选订单中没有待发货订单' : '所选订单当前都不能取消')
    return
  }

  const actionText = action === 'ship' ? '发货' : '取消'
  try {
    await ElMessageBox.confirm(`将${actionText} ${eligible.length} 个符合条件的订单，是否继续？`, `批量${actionText}`, {
      confirmButtonText: `确认${actionText}`,
      cancelButtonText: '返回',
      type: 'warning',
    })
    const order_nos = eligible.map((order) => order.order_sn)
    const path = action === 'ship' ? 'batch-ship' : 'batch-cancel'
    const response = await request.post(`/admin/orders/${path}/`, { order_nos })
    ElMessage.success(response.status || `已${actionText} ${eligible.length} 个订单`)
    selectedOrders.value = []
    await fetchOrders()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error(getApiErrorMessage(error, `批量${actionText}失败`))
    }
  }
}

onMounted(fetchOrders)
</script>

<template>
  <AdminLayout current-title="订单管理">
    <section class="page-intro">
      <div>
        <h2>订单列表</h2>
        <p>查看交易快照，并处理待发货或可取消的订单。</p>
      </div>
      <el-button :icon="Refresh" :loading="loading" @click="fetchOrders">刷新</el-button>
    </section>

    <section class="toolbar">
      <el-input
        v-model="query.search"
        clearable
        placeholder="搜索订单号或用户名"
        class="search-input"
        @keyup.enter="searchOrders"
        @clear="searchOrders"
      >
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <el-select v-model="query.status" clearable placeholder="全部状态" class="status-select" @change="searchOrders">
        <el-option v-for="status in statusOptions" :key="status.value" :label="status.label" :value="status.value" />
      </el-select>
      <el-button @click="searchOrders">搜索</el-button>
    </section>

    <section v-if="selectedOrders.length" class="bulk-toolbar">
      <span>已选择 {{ selectedOrders.length }} 个订单</span>
      <div>
        <el-button :disabled="!shipEligible.length" @click="runBatchAction('ship')">
          批量发货{{ shipEligible.length ? `（${shipEligible.length}）` : '' }}
        </el-button>
        <el-button type="danger" plain :disabled="!cancelEligible.length" @click="runBatchAction('cancel')">
          批量取消{{ cancelEligible.length ? `（${cancelEligible.length}）` : '' }}
        </el-button>
      </div>
    </section>

    <section class="table-frame" v-loading="loading">
      <el-table :data="orders" empty-text="暂无订单" style="width: 100%" @selection-change="selectedOrders = $event">
        <el-table-column type="selection" width="48" />
        <el-table-column prop="order_sn" label="订单号" min-width="180" />
        <el-table-column prop="username" label="用户" min-width="110" />
        <el-table-column label="金额" width="120" align="right">
          <template #default="{ row }">¥{{ row.total_price }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">{{ statusLabels[row.status] || row.status }}</template>
        </el-table-column>
        <el-table-column label="支付方式" width="110">
          <template #default="{ row }">{{ paymentLabels[row.payment_method] || '—' }}</template>
        </el-table-column>
        <el-table-column label="创建时间" min-width="170">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="205" fixed="right">
          <template #default="{ row }">
            <el-button link @click="showDetails(row)">详情</el-button>
            <el-button v-if="row.status === 'paid'" link @click="shipOrder(row)">发货</el-button>
            <el-button v-if="['unpaid', 'paid'].includes(row.status)" link type="danger" @click="cancelOrder(row)">取消</el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <div class="pagination-row">
      <span>共 {{ total.toLocaleString('zh-CN') }} 个订单</span>
      <el-pagination
        v-model:current-page="query.page"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next"
        @current-change="fetchOrders"
      />
    </div>

    <el-dialog v-model="detailVisible" title="订单详情" width="680px">
      <template v-if="currentOrder">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="订单号">{{ currentOrder.order_sn }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ statusLabels[currentOrder.status] || currentOrder.status }}</el-descriptions-item>
          <el-descriptions-item label="用户名">{{ currentOrder.username || '—' }}</el-descriptions-item>
          <el-descriptions-item label="支付方式">{{ paymentLabels[currentOrder.payment_method] || '—' }}</el-descriptions-item>
          <el-descriptions-item label="订单金额">¥{{ currentOrder.total_price }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatDate(currentOrder.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="收货信息" :span="2">{{ currentOrder.address_info || '—' }}</el-descriptions-item>
        </el-descriptions>

        <h3 class="items-heading">商品明细</h3>
        <div class="items-list">
          <div v-for="item in currentOrder.items || []" :key="item.id" class="order-item">
            <el-image v-if="item.product_img" :src="item.product_img" fit="cover" class="item-image" />
            <div v-else class="item-image item-image-empty">—</div>
            <div class="item-name">
              <strong>{{ item.product_name }}</strong>
              <span>数量 {{ item.count }}</span>
            </div>
            <strong class="item-price">¥{{ item.price }}</strong>
          </div>
          <p v-if="!currentOrder.items?.length" class="empty-items">没有商品明细</p>
        </div>
      </template>
    </el-dialog>
  </AdminLayout>
</template>

<style scoped>
.page-intro,
.pagination-row,
.bulk-toolbar {
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

.toolbar,
.bulk-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.search-input {
  width: min(100%, 380px);
}

.status-select {
  width: 150px;
}

.bulk-toolbar {
  justify-content: space-between;
  border: 1px solid var(--hairline-soft);
  background: var(--canvas);
  padding: 10px 14px;
  color: var(--mute);
}

.bulk-toolbar > div {
  display: flex;
  gap: 6px;
}

.table-frame {
  border: 1px solid var(--hairline-soft);
  background: var(--canvas);
}

.pagination-row {
  margin-top: 16px;
  color: var(--mute);
  font-size: 12px;
}

.items-heading {
  margin: 24px 0 12px;
  font-size: 15px;
  font-weight: 500;
}

.items-list {
  border-top: 1px solid var(--hairline-soft);
}

.order-item {
  display: flex;
  min-height: 70px;
  align-items: center;
  gap: 12px;
  border-bottom: 1px solid var(--hairline-soft);
  padding: 10px 2px;
}

.item-image {
  width: 48px;
  height: 48px;
  flex: 0 0 48px;
  background: var(--soft-cloud);
}

.item-image-empty {
  display: grid;
  place-items: center;
  color: var(--mute);
}

.item-name {
  display: grid;
  flex: 1;
  gap: 5px;
}

.item-name strong,
.item-price {
  font-size: 13px;
  font-weight: 500;
}

.item-name span,
.empty-items {
  color: var(--mute);
  font-size: 12px;
}

.empty-items {
  padding: 16px 0;
}

@media (max-width: 720px) {
  .page-intro,
  .pagination-row {
    align-items: flex-start;
    flex-direction: column;
  }

  .bulk-toolbar {
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
