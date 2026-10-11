<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Box, Plus, Refresh, Search } from '@element-plus/icons-vue'
import AdminLayout from '@/components/AdminLayout.vue'
import request, { getApiErrorMessage } from '@/utils/requests'

const loading = ref(false)
const saving = ref(false)
const products = ref([])
const brands = ref([])
const categories = ref([])
const selectedProducts = ref([])
const total = ref(0)
const dialogVisible = ref(false)
const formRef = ref()
const isEditing = ref(false)

const query = reactive({ page: 1, page_size: 10, search: '' })
const emptyForm = () => ({
  prod_id: '',
  name: '',
  brand: null,
  category: null,
  origin: '',
  price: '0.00',
  stock: 0,
  img_url: '',
  all_params_text: '{}',
  is_active: true,
})
const form = reactive(emptyForm())

const rules = {
  name: [{ required: true, message: '请输入商品名称', trigger: 'blur' }],
  brand: [{ required: true, message: '请选择品牌', trigger: 'change' }],
  category: [{ required: true, message: '请选择分类', trigger: 'change' }],
  price: [{
    validator: (_rule, value, callback) => {
      if (/^\d+(\.\d{1,2})?$/.test(String(value)) && Number(value) >= 0) callback()
      else callback(new Error('请输入不小于 0 且最多两位小数的价格'))
    },
    trigger: 'blur',
  }],
}

async function fetchAll(endpoint) {
  const firstPage = await request.get(endpoint, { params: { page: 1 } })
  const rows = [...(firstPage.results || [])]
  const count = firstPage.count ?? rows.length
  let page = 2
  while (rows.length < count) {
    const nextPage = await request.get(endpoint, { params: { page } })
    const nextRows = nextPage.results || []
    if (!nextRows.length) break
    rows.push(...nextRows)
    page += 1
  }
  return rows
}

async function fetchReferenceData() {
  try {
    const [brandRows, categoryRows] = await Promise.all([
      fetchAll('/brands/'),
      fetchAll('/categories/'),
    ])
    brands.value = brandRows
    categories.value = categoryRows
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '品牌或分类读取失败'))
  }
}

async function fetchProducts() {
  loading.value = true
  try {
    const response = await request.get('/admin/products/', { params: query })
    products.value = response.results || []
    total.value = response.count || 0
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, '商品列表读取失败'))
  } finally {
    loading.value = false
  }
}

function searchProducts() {
  query.page = 1
  fetchProducts()
}

function handleSelectionChange(rows) {
  selectedProducts.value = rows
}

function openCreateDialog() {
  isEditing.value = false
  Object.assign(form, emptyForm())
  dialogVisible.value = true
}

function openEditDialog(product) {
  isEditing.value = true
  Object.assign(form, {
    prod_id: product.prod_id,
    name: product.name,
    brand: product.brand,
    category: product.category,
    origin: product.origin || '',
    price: String(product.price ?? '0.00'),
    stock: product.stock ?? 0,
    img_url: product.img_url || '',
    all_params_text: JSON.stringify(product.all_params || {}, null, 2),
    is_active: product.is_active,
  })
  dialogVisible.value = true
}

function parseAllParams() {
  let value
  try {
    value = JSON.parse(form.all_params_text || '{}')
  } catch {
    ElMessage.error('商品参数必须是有效的 JSON 对象')
    return null
  }
  if (!value || Array.isArray(value) || typeof value !== 'object'
    || Object.values(value).some((group) => !group || Array.isArray(group) || typeof group !== 'object')) {
    ElMessage.error('商品参数及其分组必须是 JSON 对象')
    return null
  }
  return value
}

async function submitProduct() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  const allParams = parseAllParams()
  if (!allParams) return

  const payload = {
    name: form.name.trim(),
    brand: form.brand,
    category: form.category,
    origin: form.origin.trim(),
    price: form.price,
    stock: form.stock,
    img_url: form.img_url.trim(),
    all_params: allParams,
    is_active: form.is_active,
  }
  if (form.prod_id) payload.prod_id = form.prod_id.trim()

  saving.value = true
  try {
    if (isEditing.value) {
      await request.put(`/admin/products/${encodeURIComponent(form.prod_id)}/`, payload)
      ElMessage.success('商品已更新')
    } else {
      await request.post('/admin/products/', payload)
      ElMessage.success('商品已创建')
    }
    dialogVisible.value = false
    await fetchProducts()
  } catch (error) {
    ElMessage.error(getApiErrorMessage(error, isEditing.value ? '商品更新失败' : '商品创建失败'))
  } finally {
    saving.value = false
  }
}

async function deleteProduct(product) {
  try {
    await ElMessageBox.confirm(
      `删除「${product.name}」会同时清理购物车中的该商品，历史订单快照会保留。`,
      '确认删除商品',
      { confirmButtonText: '删除商品', cancelButtonText: '返回', type: 'warning' },
    )
    await request.delete(`/admin/products/${encodeURIComponent(product.prod_id)}/`)
    ElMessage.success('商品已删除')
    await fetchProducts()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error(getApiErrorMessage(error, '商品删除失败'))
    }
  }
}

async function batchUpdate(isActive) {
  const pids = selectedProducts.value.map((product) => product.prod_id)
  if (!pids.length) return
  try {
    const actionText = isActive ? '上架' : '下架'
    await ElMessageBox.confirm(`确定${actionText}选中的 ${pids.length} 件商品吗？`, `批量${actionText}`, {
      confirmButtonText: `确认${actionText}`,
      cancelButtonText: '返回',
      type: 'warning',
    })
    const response = await request.post('/admin/products/batch-update/', { pids, is_active: isActive })
    ElMessage.success(response.detail || `已${actionText} ${response.count ?? pids.length} 件商品`)
    selectedProducts.value = []
    await fetchProducts()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error(getApiErrorMessage(error, '批量更新失败'))
    }
  }
}

async function batchDelete() {
  const pids = selectedProducts.value.map((product) => product.prod_id)
  if (!pids.length) return
  try {
    await ElMessageBox.confirm(
      `确定删除选中的 ${pids.length} 件商品吗？购物车记录会被清理，历史订单快照会保留。`,
      '批量删除商品',
      { confirmButtonText: '删除商品', cancelButtonText: '返回', type: 'warning' },
    )
    const response = await request.post('/admin/products/batch-delete/', { pids })
    ElMessage.success(response.detail || `已删除 ${response.count ?? pids.length} 件商品`)
    selectedProducts.value = []
    await fetchProducts()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error(getApiErrorMessage(error, '批量删除失败'))
    }
  }
}

function formatDate(value) {
  return value ? new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium' }).format(new Date(value)) : '—'
}

onMounted(() => {
  fetchProducts()
  fetchReferenceData()
})
</script>

<template>
  <AdminLayout current-title="商品管理">
    <section class="page-intro">
      <div>
        <h2>商品目录</h2>
        <p>维护商品信息、价格、库存和销售状态。</p>
      </div>
      <el-button type="primary" :icon="Plus" @click="openCreateDialog">添加商品</el-button>
    </section>

    <section class="toolbar">
      <el-input
        v-model="query.search"
        clearable
        placeholder="搜索名称、品牌、分类或商品编码"
        class="search-input"
        @keyup.enter="searchProducts"
        @clear="searchProducts"
      >
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <el-button @click="searchProducts">搜索</el-button>
      <el-button :icon="Refresh" aria-label="刷新商品列表" @click="fetchProducts" />
    </section>

    <section v-if="selectedProducts.length" class="bulk-toolbar">
      <span>已选择 {{ selectedProducts.length }} 件商品</span>
      <div>
        <el-button @click="batchUpdate(true)">批量上架</el-button>
        <el-button @click="batchUpdate(false)">批量下架</el-button>
        <el-button type="danger" plain @click="batchDelete">批量删除</el-button>
      </div>
    </section>

    <section class="table-frame" v-loading="loading">
      <el-table :data="products" empty-text="暂无商品" style="width: 100%" @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="48" />
        <el-table-column label="商品" min-width="260">
          <template #default="{ row }">
            <div class="product-cell">
              <el-image v-if="row.img_url" :src="row.img_url" fit="cover" class="product-image" />
              <div v-else class="product-image image-placeholder"><el-icon><Box /></el-icon></div>
              <div class="product-copy">
                <strong>{{ row.name }}</strong>
                <span>{{ row.prod_id }}</span>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="brand_name" label="品牌" min-width="100" />
        <el-table-column prop="category_name" label="分类" min-width="100" />
        <el-table-column label="价格" width="120" align="right">
          <template #default="{ row }">¥{{ row.price }}</template>
        </el-table-column>
        <el-table-column label="库存" width="100" align="right">
          <template #default="{ row }">{{ row.stock }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <span class="status-dot" :class="{ 'is-active': row.is_active }" />
            {{ row.is_active ? '在售' : '已下架' }}
          </template>
        </el-table-column>
        <el-table-column label="更新日期" min-width="130">
          <template #default="{ row }">{{ formatDate(row.updated_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="135" fixed="right">
          <template #default="{ row }">
            <el-button link @click="openEditDialog(row)">编辑</el-button>
            <el-button link type="danger" @click="deleteProduct(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <div class="pagination-row">
      <span>共 {{ total.toLocaleString('zh-CN') }} 件商品</span>
      <el-pagination
        v-model:current-page="query.page"
        :page-size="query.page_size"
        :total="total"
        layout="prev, pager, next"
        @current-change="fetchProducts"
      />
    </div>

    <el-dialog v-model="dialogVisible" :title="isEditing ? '编辑商品' : '添加商品'" width="680px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" class="product-form">
        <div class="form-grid">
          <el-form-item label="商品名称" prop="name">
            <el-input v-model="form.name" maxlength="200" placeholder="请输入商品名称" />
          </el-form-item>
          <el-form-item label="商品编码" prop="prod_id">
            <el-input v-model="form.prod_id" :disabled="isEditing" placeholder="留空则由系统生成" />
          </el-form-item>
          <el-form-item label="品牌" prop="brand">
            <el-select v-model="form.brand" placeholder="选择品牌" class="full-width">
              <el-option v-for="brand in brands" :key="brand.id" :label="brand.name" :value="brand.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="分类" prop="category">
            <el-select v-model="form.category" placeholder="选择分类" class="full-width">
              <el-option v-for="category in categories" :key="category.id" :label="category.name" :value="category.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="价格（元）" prop="price">
            <el-input v-model="form.price" inputmode="decimal" placeholder="0.00" />
          </el-form-item>
          <el-form-item label="库存" prop="stock">
            <el-input-number v-model="form.stock" :min="0" :step="1" step-strictly controls-position="right" class="full-width" />
          </el-form-item>
          <el-form-item label="产地" prop="origin">
            <el-input v-model="form.origin" maxlength="100" placeholder="选填" />
          </el-form-item>
          <el-form-item label="商品图片 URL" prop="img_url">
            <el-input v-model="form.img_url" maxlength="1000" placeholder="https://…" />
          </el-form-item>
        </div>
        <el-form-item label="动态参数（JSON 对象）" prop="all_params_text">
          <el-input v-model="form.all_params_text" type="textarea" :rows="6" spellcheck="false" />
        </el-form-item>
        <el-form-item label="销售状态">
          <el-switch v-model="form.is_active" active-text="在售" inactive-text="下架" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">返回</el-button>
        <el-button type="primary" :loading="saving" @click="submitProduct">保存商品</el-button>
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
  width: min(100%, 420px);
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
  flex-wrap: wrap;
  gap: 6px;
}

.table-frame {
  border: 1px solid var(--hairline-soft);
  background: var(--canvas);
}

.product-cell {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 12px;
}

.product-image {
  width: 48px;
  height: 48px;
  flex: 0 0 48px;
  background: var(--soft-cloud);
}

.image-placeholder {
  display: grid;
  place-items: center;
  color: var(--mute);
  font-size: 18px;
}

.product-copy {
  display: grid;
  min-width: 0;
  gap: 5px;
}

.product-copy strong {
  overflow: hidden;
  font-weight: 500;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.product-copy span {
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

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  column-gap: 18px;
}

.full-width {
  width: 100%;
}

@media (max-width: 720px) {
  .page-intro {
    align-items: flex-start;
  }

  .bulk-toolbar {
    align-items: flex-start;
    flex-direction: column;
  }

  .pagination-row {
    align-items: flex-start;
    flex-direction: column;
  }
}

@media (max-width: 520px) {
  .page-intro h2 {
    font-size: 21px;
  }

  .form-grid {
    grid-template-columns: 1fr;
  }

  .toolbar {
    flex-wrap: wrap;
  }

  .search-input {
    width: 100%;
  }
}
</style>
