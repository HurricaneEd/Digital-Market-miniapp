# 阶段 3：商品产地开发清单

## 1. 涉及文件

| 文件 | 修改内容 |
| --- | --- |
| `Product/models.py` | 为 `Product` 增加可选 `origin` 字段 |
| `Product/migrations/0004_product_origin.py` | 新增字段迁移，旧数据填充空字符串 |
| `Product/serializer.py` | 在商品 API 契约中加入 `origin` |
| `Product/tests.py` | 增加默认值、详情、新增、编辑和长度校验测试 |
| `miniapp/pages/product-detail/product-detail.wxml` | 商品详情展示产地及空值文案 |
| `docs/database-redesign.md` | 同步商品固定核心字段事实 |
| `docs/05_BUG_LOG.md` | 记录本轮真实发现的问题或明确无新问题 |
| `docs/06_REGRESSION_REPORT.md` | 记录迁移、接口和关联回归结果 |

## 2. 实施步骤

1. 先建立需求分析和本清单。
2. 修改 ORM 模型并新增迁移。
3. 修改 Serializer，使公共和管理 API 契约一致。
4. 修改小程序商品详情，显示 `origin || '未填写'`。
5. 增加自动化测试，覆盖旧数据、创建、编辑、详情和非法长度。
6. 执行迁移检查、应用测试、全量测试和小程序静态检查。
7. 记录真实 Bug 和回归结果。

## 3. 数据库迁移

- 新增迁移编号：沿用当前 Product 最新迁移 `0003`，创建 `0004_product_origin`。
- 字段定义：`CharField(max_length=100, blank=True, default='')`。
- 不重写 `0001`、`0002`、`0003`。
- 迁移前后核对商品总数和旧商品产地默认值。

## 4. 风险与处理

| 风险 | 处理方式 |
| --- | --- |
| 旧商品没有产地 | 默认空字符串，小程序显示“未填写” |
| API 字段遗漏 | Serializer 显式声明并使用接口测试验证 |
| 管理 API 写入失败 | 覆盖 POST、PATCH 和超长值测试 |
| 旧导入覆盖人工产地 | 本轮不让旧导入器写 `origin` |
| 小程序字段为空导致空白 | 使用明确回退文案 |
| 迁移破坏已有数据 | 迁移前后核对商品数量，执行迁移一致性检查 |

## 5. 向后兼容

- `origin` 可选且有默认值。
- 不修改现有字段、路由、查询参数和响应结构中的旧字段。
- 不改变订单快照、库存、价格和评论逻辑。
- 旧小程序或其他客户端忽略新增字段即可继续使用。

## 6. 测试点

- 模型新商品不传 `origin` 时保存为空字符串。
- 公共商品详情响应包含 `origin`。
- 管理员新增商品时可保存产地。
- 管理员 PATCH 商品时可修改产地并回显。
- `origin` 超过 100 个字符时返回 HTTP 400，数据库不变。
- `python manage.py check`。
- `python manage.py makemigrations --check --dry-run`。
- `python manage.py test Product`。
- `python manage.py test Orders`、`python manage.py test Users` 和全量测试。
- 小程序 JS/JSON/WXML 静态检查。
- 微信开发者工具中商品详情视觉展示标记为 `NEEDS_MANUAL`。

