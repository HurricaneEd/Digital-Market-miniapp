# 阶段 3：Bug 日志

## BUG-001

**标题：** 公共商品 API 暴露已下架商品

**发现环境：**

- 日期：2026-09-09
- Django 5.2.11
- Django REST Framework 3.16.1
- 当前项目 MySQL 数据库
- 使用 DRF `APIClient` 在回滚事务中复现

**前置条件：**

- 数据库存在品牌和分类。
- 创建一个 `is_active=False` 的临时商品 `P-PHASE3-INACTIVE`。
- 临时数据位于事务中，复现完成后回滚。

**复现步骤：**

1. 创建名称为“阶段3下架商品”的下架商品。
2. 请求 `GET /api/products/?search=阶段3下架商品`。
3. 请求 `GET /api/products/P-PHASE3-INACTIVE/`。
4. 检查公共列表和公共详情是否暴露该商品。

**Expected Result：**

- 公共商品列表不返回下架商品。
- 下架商品的公共详情返回 HTTP 404。
- 管理员商品接口仍可查看和维护下架商品。

**Actual Result：**

- 修复前公共列表返回 HTTP 200，`count=1`，`exposed=True`。
- 修复前公共详情返回 HTTP 200。

**错误信息：**

没有服务器异常；问题表现为响应内容违反商城上下架规则。新增回归测试修复前失败信息为：

```text
AssertionError: 'P-INACTIVE' unexpectedly found in ['P-INACTIVE', 'P-ACTIVE']
```

**影响范围：**

- 未登录用户可以通过公共列表和详情查看已下架商品。
- 小程序虽然在客户端过滤 `is_active=false`，但服务端分页仍可能把下架商品计入分页，造成页面数量不准确或空页。
- 管理员接口不应受公共可见性修复影响。

**初步分析：**

公共 `ProductViewSet.get_queryset()` 从全部商品开始查询，没有应用在售条件。

**根因：**

公共查询集缺少 `is_active=True` 过滤，商品上下架状态仅由部分客户端自行处理。

**修复方案：**

- 在公共 `ProductViewSet.get_queryset()` 起始查询中增加 `filter(is_active=True)`。
- 不修改 `AdminProductViewSet`，确保管理员仍可管理下架商品。
- 增加自动化测试，覆盖公共列表、公共详情和管理员详情三个关联场景。

**修改文件：**

- `Product/views.py`
- `Product/tests.py`

**验证方法：**

1. 执行 `python manage.py test Product.tests.ProductVisibilityTests`。
2. 执行 Product 应用测试和全量测试。
3. 在回滚事务中再次创建下架商品并请求公共列表和详情。

**回归结果：**

- 公共列表 HTTP 200，`count=0`，`exposed=False`。
- 公共详情 HTTP 404。
- 管理员详情 HTTP 200。
- Product 7 项测试通过。
- 全量 15 项测试通过。

该问题已完成复现、修复和关联回归。

