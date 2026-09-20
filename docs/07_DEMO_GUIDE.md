# DigRecSys 面试演示脚本

目标时长：7–9 分钟。演示前启动 Django、打开 Swagger 和微信开发者工具，并准备一个本地管理员账号。当前没有 Web 管理页面，因此后台部分展示真实的管理 API，不把 Swagger 描述成业务后台界面。

## 演示前准备

```powershell
python manage.py check
python manage.py migrate
python manage.py runserver 127.0.0.1:8000 --noreload
```

准备以下窗口：

1. `http://127.0.0.1:8000/swagger/`
2. 微信开发者工具中的 `miniapp`
3. IDE 中的 `docs/03_CHANGE_REQUEST.md`、`docs/04_CHANGE_TASK_LIST.md`、`docs/05_BUG_LOG.md` 和 `docs/06_REGRESSION_REPORT.md`
4. 一个已填写产地的本地演示商品；没有时可通过管理员商品 API 修改，避免现场临时改生产数据。

## 0:00–0:30 系统简介

讲述：

> 这是一个数码商品交易项目。微信小程序负责用户侧浏览和订单展示，Django REST Framework 提供用户、商品、购物车和订单接口，MySQL 保存交易数据；商品采集和审核入库与线上交易解耦。

展示根目录和 README 的架构图。

## 0:30–2:30 后端与管理 API

打开 Swagger，按以下顺序展示：

1. `/api/products/`：说明公共商品列表支持搜索、分类、价格、排序和每页 12 条分页。
2. `/api/products/{prod_id}/`：展示商品详情、`origin` 和 `all_params`。
3. `/api/admin/products/`：说明管理员接口支持 CRUD、每页 10 条、搜索和排序。
4. `/api/admin/users/`：展示用户搜索、启停筛选和分页接口定义。
5. `/api/admin/orders/`：展示订单搜索、状态筛选、详情、发货和批量操作。

边界说明：

> 当前管理能力是 REST API，没有独立 Web 管理页面。Swagger 用于演示接口契约和调用，不宣称它是成品后台页面。

如果时间允许，用登录接口取得本地管理员 Token，再调用一个只读管理列表。不要在屏幕或文档中保留 Token。

## 2:30–4:30 微信小程序

在开发者工具中依次展示：

1. 首页：搜索栏、分类 tabs、精选商品和吸顶效果。
2. 商品列表：输入关键字搜索，切换分类，滚动触发分页。
3. 商品详情：展示名称、价格、品牌、分类、产地、库存和动态参数。
4. 可选：登录后加入购物车，再打开个人中心和订单列表。

如果现场网络失败，说明 API 地址集中在 `miniapp/utils/config.js`，并展示中文错误提示和重试入口。

## 4:30–6:00 AI 辅助需求变更

依次打开：

1. `docs/03_CHANGE_REQUEST.md`：说明先核查 Product 没有同义字段，再定义 `origin` 的类型、空值和兼容策略。
2. `docs/04_CHANGE_TASK_LIST.md`：说明修改前先列数据库、Serializer、API、小程序和测试影响。
3. `Product/migrations/0004_product_origin.py`：展示为什么旧商品默认空字符串。
4. `Product/serializer.py` 和小程序详情 WXML：展示前后端字段名统一。

重点讲述：旧商品不编造产地，旧批次导入也不会覆盖管理员维护值。

## 6:00–7:15 真实 Bug 案例

打开 `docs/05_BUG_LOG.md`，按以下结构说明：

- 问题：公共商品 API 会返回 `is_active=False` 的下架商品。
- 复现：临时下架商品在公共列表中 `exposed=True`，详情返回 200。
- 根因：公共 `ProductViewSet.get_queryset()` 没有在售过滤。
- 修复：公共查询增加 `is_active=True`，管理员查询保持不变。
- 回归：公共列表不再返回，详情为 404，管理员详情仍为 200。

强调测试数据位于回滚事务，没有污染当前数据库。

## 7:15–8:15 测试与验收

打开：

- `docs/01_ACCEPTANCE_CHECKLIST.md`
- `docs/02_TEST_REPORT_BEFORE.md`
- `docs/06_REGRESSION_REPORT.md`

讲述实际数字：阶段 3 回归时 Product 7、Orders 6、Users 2、全量 15 项通过。小程序 GUI 没有在自动环境中执行的项目明确标记为 `NEEDS_MANUAL`。

## 8:15–9:00 收尾

总结三个工程点：

1. 商品目录、交易快照和采集数据边界明确。
2. 数据库约束、Serializer 校验和事务共同保护核心数据。
3. AI 只参与分析与实现，正确性由迁移、接口测试、回归和人工验收确认。

如果面试官继续追问，转入 [08_INTERVIEW_NOTES.md](./08_INTERVIEW_NOTES.md) 中与当前代码对应的问题。

