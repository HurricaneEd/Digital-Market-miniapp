# 阶段 2：首次测试报告

## 1. 测试信息

- 执行日期：2026-09-09
- 项目目录：`D:\PycharmProjects\DigRecSys`
- 小程序目录：`D:\PycharmProjects\DigRecSys\miniapp`
- 后端：Django/DRF，使用当前项目配置的 MySQL 数据库
- 小程序：微信原生小程序，Vant Weapp 组件代码已存在于 `miniprogram_npm/`
- 统计口径：按 `docs/acceptance_cases.csv` 的用例行统计，不按单个命令内部断言数量重复计数。

## 2. 结果统计

| 指标 | 数量 |
| --- | ---: |
| 测试用例总数 | 26 |
| PASS | 13 |
| FAIL | 0 |
| BLOCKED | 0 |
| NEEDS_MANUAL | 10 |
| NOT_IMPLEMENTED | 3 |

`NOT_IMPLEMENTED` 不计入四类执行结果统计，但计入本次验收范围总数。

## 3. 实际执行命令与结果

### 后端检查

```text
python manage.py check
System check identified no issues (0 silenced).

python manage.py makemigrations --check --dry-run
No changes detected
```

### 应用测试

```text
python manage.py test Product
Ran 4 tests ... OK

python manage.py test Orders
Ran 6 tests ... OK

python manage.py test Users
Ran 2 tests ... OK

python manage.py test
Ran 12 tests ... OK
```

### 只读接口验收

在真实当前数据库上使用 DRF `APIClient` 执行：

- `GET /api/products/`：HTTP 200，分页总数 48。
- `GET /api/products/?search=<实际商品名前缀>`：HTTP 200。
- `GET /api/products/?category=<实际分类编码>`：HTTP 200。
- `GET /api/products/?page=2`：HTTP 200，分页总数 48。
- `GET /api/products/1214176/`：HTTP 200。
- `GET /api/categories/`：HTTP 200。
- 未认证 `GET /api/users/me/`：HTTP 401。
- 未认证 `GET /api/orders/`：HTTP 401。

注册/登录接口使用事务内临时账号执行：注册 HTTP 201、登录 HTTP 200、`me` HTTP 200、`profile` HTTP 200，事务已回滚，未留下临时用户。

### 小程序静态检查

- 13 个业务 JavaScript 文件通过 `node --check`。
- 12 个业务 JSON 文件通过 JSON 解析。
- 7 个页面均具备 JS、JSON、WXML、WXSS 文件。
- 32 个页面 Vant 组件引用均能找到对应组件文件。

## 4. 实际发现的问题与限制

1. 微信开发者工具和真机交互尚未在当前环境执行，因此首页打开、搜索、分类切换、详情跳转、错误提示、空状态和吸顶效果均为 `NEEDS_MANUAL`，不能视为界面验收通过。
2. 当前项目没有可操作的后台商品、用户、订单管理页面；对应管理 API 路由存在，但后台页面相关用例标记为 `NOT_IMPLEMENTED`。
3. 小程序当前使用账号密码和 DRF Token，不是微信 `wx.login` 身份体系。
4. 后端支付接口是模拟状态变更，不是真实微信支付。
5. 小程序真机访问后端不能使用 `127.0.0.1`，需要局域网地址或已配置的 HTTPS 合法域名。

## 5. 回归结论

本次自动化回归未发现 FAIL 或 BLOCKED。当前商城后端核心接口和小程序源文件结构通过自动检查；小程序视觉、交互和网络异常场景仍需按验收清单在微信开发者工具中人工执行。

