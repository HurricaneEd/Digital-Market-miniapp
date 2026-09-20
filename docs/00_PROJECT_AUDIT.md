# DigRecSys 项目仓库审计

## 审计信息

- 审计日期：2026-09-08
- 审计范围：当前工作区中的 Django/DRF 后端、MySQL 配置、商品采集/入库工具、微信原生小程序
- 本阶段限制：只做审计和验证，不开发微信小程序新功能，不修改业务代码
- 事实来源：当前代码、迁移、测试、实际命令输出和本地 HTTP 冒烟请求

## 一、审计结论

当前项目是一个 Django + Django REST Framework 的数码商品交易后端，并包含一个已经移动到 `miniapp/` 的微信原生小程序客户端。

当前已确认：

- 后端可以在本机启动。
- MySQL 数据库连接可用；迁移状态完整，所有现有迁移显示为已应用。
- 商品、分类、用户认证、购物车、收货地址、订单、评论和后台管理 API 已注册。
- 商品列表、分类列表和 Swagger 文档已通过本地 HTTP 冒烟请求。
- 小程序目前只实际请求商品列表接口；没有实现完整的登录、商品详情、购物车、地址和订单页面。
- 当前没有发现 Web 管理端前端源码，仓库中已有的是后台 API 和 Django Admin/API 文档能力。

当前未确认：

- 微信开发者工具中的页面编译、页面跳转和真实交互，因为本次环境未执行微信开发者工具 GUI 验收，必须标记为 `NEEDS_MANUAL_VERIFICATION`。
- 真机访问，因为小程序当前使用 `127.0.0.1`，真机上的含义不是后端电脑地址。
- 生产部署能力；当前配置仍是开发配置。

## 二、技术栈

### 后端

| 项目 | 当前实际情况 |
| --- | --- |
| 语言 | Python 3.11.9 |
| Web 框架 | Django 5.2.11 |
| API 框架 | Django REST Framework 3.16.1 |
| ORM | Django ORM |
| 数据库 | MySQL，配置在 `DigRecSys/settings.py`，数据库名为 `digrecsys1`，本机 3306 端口 |
| 用户模型 | `Users.User`，继承 Django `AbstractUser` |
| API 认证 | DRF TokenAuthentication；请求头格式为 `Authorization: Token <token>` |
| API 文档 | drf-yasg，提供 `/swagger/` 和 `/redoc/` |
| 跨域 | `corsheaders`，当前配置允许所有来源 |
| 媒体文件 | `MEDIA_URL=/media/`，目录为 `media/` |

仓库没有 `requirements.txt` 或 `pyproject.toml`。后端依赖目前只能从运行环境、导入语句和 Django 配置推断，尚未形成可复现的后端依赖安装清单。

### 微信小程序

- 技术：微信原生小程序 WXML、WXSS、JavaScript。
- UI 组件：Vant Weapp 1.11.7。
- 项目目录：`miniapp/`。
- 页面：`pages/index/index`、`pages/my/my`。
- 依赖构建目录：`miniapp/miniprogram_npm/`，由微信开发者工具构建生成，本次没有修改其中的第三方代码。

### 采集与入库

- `crawl/crawl_data.py`：使用 `requests` 和 `lxml` 采集商品列表及参数，输出原始 Excel/JSON 快照。
- `database/import_products.py`：校验清洗结果，并以 `prod_id` 为依据导入或更新 `Product`、`Brand`、`Category`。
- 爬虫不请求评论接口，入库脚本不导入评论。

### 未发现的运行模块

- 当前代码中没有有效的 Web 前端工程。
- 当前代码中没有已注册的推荐模块运行入口。
- 未将规划文档中的功能视为已实现功能。

## 三、目录与模块

```text
DigRecSys/
├── DigRecSys/       Django 全局配置、根路由、ASGI/WSGI
├── Users/           用户模型、注册登录、个人资料、后台用户 API
├── Product/         商品、品牌、分类、评论及 API
├── Orders/          收货地址、购物车、订单、订单明细及 API
├── crawl/           商品采集脚本
├── database/        商品清洗结果导入工具
├── data/            商品采集原始数据目录（如存在批次数据）
├── media/           用户头像等媒体文件
├── miniapp/         微信原生小程序客户端
├── docs/            项目设计与审计文档
├── CONTEXT.md       领域术语和数据边界
├── Restruct.md      改造规划，不代表功能已经实现
└── manage.py        Django 管理入口
```

## 四、核心数据模型

### 用户与目录

- `Users.User`：基于 `AbstractUser`，增加 `avatar`、`phone`、`nickname`，邮箱和手机号可选且唯一。
- `Product.Brand`：品牌名称唯一。
- `Product.Category`：分类代码和名称，`parent` 支持父子分类，并在模型层阻止分类循环。
- `Product.Product`：商品唯一使用该模型，包含 `prod_id`、品牌、分类、名称、价格、主图、`all_params`、库存、上下架状态和时间字段。
- `Product.Review`：商品评论，可关联用户；保留作者名、内容、评分和情感字段。

### 交易

- `Orders.Address`：用户可维护的收货地址。
- `Orders.CartItem`：用户与商品的购物车关系；同一用户和商品由唯一约束保证只有一条购物车记录。
- `Orders.Order`：用户订单，状态为待支付、已支付、已发货、已完成或已取消。
- `Orders.OrderItem`：订单明细，保存下单时商品编码、商品名称、价格和数量快照。
- `Orders.ShippingAddressSnapshot`：订单创建时的收货地址快照，避免后续修改用户地址影响历史订单。

关系如下：

```text
User ──< Address
  ├──< CartItem >── Product ──> Brand
  │                         └──> Category
  ├──< Order ──< OrderItem >── Product
  │      └── ShippingAddressSnapshot
  └──< Review >────────────── Product
```

订单创建会锁定购物车和商品，检查上下架状态及库存，使用 `Decimal` 计算总价，扣减库存并生成订单明细快照。取消未完成订单会在事务中恢复库存。

## 五、API 清单

根路由在 `DigRecSys/urls.py` 中将三个应用统一挂载到 `/api/`。默认分页大小为 12；后台商品和用户列表使用各自的分页配置。

### 5.1 小程序可复用的公共目录 API

| 方法 | 路径 | 参数/返回 | 鉴权 | 当前判断 |
| --- | --- | --- | --- | --- |
| GET | `/api/products/` | 分页商品列表；支持 `search`、`category`、`min_price`、`max_price`、`ordering`、`page` | 否 | 后端可直接复用；当前小程序已调用 |
| GET | `/api/products/{prod_id}/` | 商品详情，主键查找字段是字符串 `prod_id` | 否 | 后端可复用；小程序尚未调用 |
| GET | `/api/categories/` | 分页分类列表；支持 `search`、`ordering` | 否 | 可复用；当前接口还开放了写操作，不应直接作为普通客户端写接口 |
| GET | `/api/categories/{id}/` | 分类详情 | 否 | 可复用 |
| GET | `/api/brands/` | 分页品牌列表；支持 `search`、`ordering` | 否 | 可复用 |
| GET | `/api/brands/{id}/` | 品牌详情 | 否 | 可复用 |
| GET | `/api/reviews/?product_id={prod_id}` | 按商品查询评论，也支持 `rating`、搜索和排序 | 否 | 可读取；评论写操作当前也允许匿名访问，需后续重新核定权限 |

商品列表返回 `id`、`prod_id`、品牌/分类名称、名称、价格、库存、上下架状态、主图、动态参数、评分和评论数。当前公共商品查询没有在 `ProductViewSet` 中显式过滤 `is_active`，这是小程序显示下架商品的风险点。

### 5.2 用户与认证 API

| 方法 | 路径 | 参数/返回 | 鉴权 | 当前判断 |
| --- | --- | --- | --- | --- |
| POST | `/api/users/register/` | `username`、`phone`、`email`、`password`；返回 Token 和用户摘要 | 否 | 可复用，但不是微信 `wx.login` |
| POST | `/api/users/login/` | `identifier`、`password`；identifier 支持用户名、手机号或邮箱；返回 Token 和用户资料 | 否 | 可复用，但不是微信 `code2Session` 登录 |
| GET | `/api/users/me/` | 当前用户摘要 | Token | 可复用 |
| GET/PUT | `/api/users/profile/` | 读取或更新昵称、邮箱、手机号、头像等资料 | Token | 可复用 |
| POST | `/api/users/upload_avatar/` | multipart 文件字段 `avatar` | Token | 可复用 |
| POST | `/api/users/change_password/` | `old_password`、`new_password`、`confirm_password` | Token | 可复用 |

当前没有微信 `wx.login`、`code2Session`、`openid/unionid` 绑定接口。小程序如果使用现有登录，只能走账号密码登录并保存 DRF Token。

### 5.3 交易 API

| 方法 | 路径 | 参数/返回 | 鉴权 | 当前判断 |
| --- | --- | --- | --- | --- |
| GET/POST | `/api/cart/` | 查询或添加购物车；添加时使用 `product_id`、`count`、`selected` | Token | 后端可复用；小程序尚未调用 |
| GET/PUT/PATCH/DELETE | `/api/cart/{id}/` | 修改或删除购物车项 | Token | 后端可复用 |
| GET/POST | `/api/addresses/` | 查询或创建地址；字段为 `receiver`、`phone`、`detail`、`is_default` | Token | 后端可复用 |
| GET/PUT/PATCH/DELETE | `/api/addresses/{id}/` | 地址详情、修改和删除 | Token | 后端可复用 |
| POST | `/api/addresses/{id}/set_default/` | 设置默认地址 | Token | 后端可复用 |
| GET | `/api/orders/` | 当前用户订单列表 | Token | 后端可复用 |
| POST | `/api/orders/` | `address_id`、`cart_item_ids`；创建订单并扣库存 | Token | 后端可复用 |
| GET | `/api/orders/{order_sn}/` | 订单详情、明细和地址快照 | Token | 后端可复用 |
| POST | `/api/orders/{order_sn}/pay/` | `payment_method` 为 `wechat` 或 `alipay` | Token | 仅模拟支付，不是真实微信支付 |
| POST | `/api/orders/{order_sn}/cancel/` | 取消未完成订单并恢复库存 | Token | 后端可复用 |
| POST | `/api/orders/{order_sn}/confirm_receive/` | 已发货订单确认收货 | Token | 后端可复用 |

### 5.4 后台管理 API

后台接口要求管理员权限：

- `/api/admin/users/`：用户列表、详情、创建、修改和删除；支持 `search`、`ordering`、`is_active` 筛选。
- `/api/admin/products/`：商品列表、详情、新增、修改、删除；支持搜索、排序，以及 `POST /batch-update/` 和 `POST /batch-delete/`。
- `/api/admin/orders/`：订单列表和详情；支持 `search`、`status`，以及发货、取消、批量发货和批量取消动作。

这些接口供后台管理使用，不应作为小程序普通用户接口。

### 5.5 文档和管理入口

- `/admin/`：Django Admin。
- `/swagger/`：Swagger UI。
- `/swagger.json`：Swagger JSON 入口。
- `/redoc/`：ReDoc。
- `/media/`：开发环境媒体文件。

## 六、小程序现状与接入可行性

### 当前已实现

- `miniapp/app.json` 注册首页和“我的”页。
- 首页使用 Vant Weapp 组件。
- 首页通过 `wx.request` 请求 `/api/products/`。
- 首页兼容 DRF 分页响应中的 `results`、`next`，并实现首屏加载、触底加载和基本错误提示。
- `miniprogram_npm/` 中已有 Vant 构建产物。

### 当前未实现或未验证

- 搜索输入只更新页面状态，没有把关键词作为 `search` 参数重新请求。
- 分类 Tab 目前只有第一个 Tab 使用商品数据，其他 Tab 是占位内容。
- 没有商品详情页面。
- “我的”页面目前是占位页面。
- 没有 Token 保存、登录、个人资料、购物车、地址和订单页面。
- 没有微信登录和真实微信支付。
- API 地址硬编码为 `http://127.0.0.1:8000/api/products/`；真机不能直接使用该地址，正式小程序还需要合法 HTTPS 域名和域名校验配置。
- 未在微信开发者工具中实际编译和操作，页面验收状态为 `NEEDS_MANUAL_VERIFICATION`。

### 推荐接入方案

继续复用现有 Django API，不复制第二套业务后端，按以下顺序完善：

1. 在小程序源代码中集中管理 API base URL、Token 和请求错误处理。
2. 先完成商品列表、搜索、分类筛选、商品详情和空数据/网络错误处理。
3. 再接入账号密码登录和 Token 持久化；如果需要微信身份登录，新增独立的微信登录换取接口，不伪造 `wx.login`。
4. 最后接入购物车、地址、订单查询和支付流程；支付前明确当前接口只是模拟支付。
5. 每一步在微信开发者工具中执行手工验收，并把未执行的项目标记为 `NEEDS_MANUAL_VERIFICATION`。

## 七、启动方式与实际验证

### 当前配置

- 后端启动入口：`manage.py`。
- 开发启动命令：

  ```powershell
  python manage.py runserver 127.0.0.1:8000 --noreload
  ```

- 默认开发端口：8000。
- 数据库：本机 MySQL 3306，数据库名 `digrecsys1`。
- 小程序导入目录：`D:\PycharmProjects\DigRecSys\miniapp`。
- 小程序依赖：`miniapp/package.json` 声明 `@vant/weapp` 1.11.7。

### 实际执行结果

| 命令/操作 | 结果 |
| --- | --- |
| `python --version` | PASS，Python 3.11.9 |
| Django/DRF 版本检查 | PASS，Django 5.2.11、DRF 3.16.1 |
| `python manage.py check` | PASS，无系统检查问题 |
| `python manage.py makemigrations --check --dry-run` | PASS，No changes detected |
| `python manage.py showmigrations` | PASS，项目和 Django 内置迁移均显示已应用 |
| `python manage.py test Users` | PASS，2 个测试通过 |
| `python manage.py test Product` | PASS，2 个测试通过 |
| `python manage.py test Orders` | PASS，6 个测试通过 |
| `python manage.py test` | PASS，共 10 个测试通过 |
| 启动 `runserver` | PASS，开发服务器在 `127.0.0.1:8000` 启动 |
| GET `/swagger/` | PASS，HTTP 200 |
| GET `/api/products/` | PASS，HTTP 200；本次响应包含 48 个商品记录，返回 DRF 分页结构 |
| GET `/api/categories/` | PASS，HTTP 200；本次响应包含 1 个分类记录 |
| 微信开发者工具 GUI 验收 | `NEEDS_MANUAL_VERIFICATION`，本次未执行 |

测试会创建并销毁 Django 测试数据库；本次没有执行正式迁移、删库、清库或迁移回退操作。

## 八、主要工程风险

1. **开发配置和敏感信息治理风险**：当前设置仍启用 `DEBUG=True`、允许所有 Host 和跨域，且配置文件及采集脚本中存在硬编码的密钥/数据库凭据/会话信息。审计文档不复制这些敏感值，生产部署前必须改用环境变量并轮换已有凭据。
2. **小程序尚未形成完整客户端闭环**：当前只有商品列表的一个请求，登录、详情、购物车、地址、订单和支付页面尚未实现；`127.0.0.1` 也不适用于真机访问，且微信开发者工具 GUI 尚未验收。
3. **可复现构建与接口覆盖不足**：后端缺少依赖清单；现有自动化测试主要覆盖数据完整性和订单库存关键路径，尚未覆盖完整的 API 契约、权限矩阵和小程序交互。

## 九、工作区状态说明

审计开始前工作区不是干净状态，存在已有的修改、删除和未跟踪文件，包括模型、迁移、路由、测试、文档和 `miniapp/`。本阶段没有清理、回退或覆盖这些变更；本次新增文件仅为本审计报告。

## 十、Phase 0 结论与下一阶段

Phase 0 审计完成。当前最适合进入 Phase 1 的工作是：基于现有 API 完善小程序的商品列表/搜索/分类/详情，并先建立集中请求配置；登录应明确采用现有 Token 登录还是新增微信身份登录。

进入 Phase 1 前仍需保留两个事实边界：

- 后端 API 已存在不等于小程序客户端已经接入。
- 未在微信开发者工具中执行的页面和交互不能写成 PASS，必须保留 `NEEDS_MANUAL_VERIFICATION`。
