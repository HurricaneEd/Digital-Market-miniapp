# DigRecSys 微信小程序

## 使用技术

- 微信原生小程序：WXML、WXSS、JavaScript、微信小程序 API。
- Vant Weapp 1.11.7：页面组件来自 `miniprogram_npm/`。
- 后端复用当前 Django/DRF API，不在小程序中复制商品、订单等业务逻辑。

## 目录结构

```text
miniapp/
├── app.js / app.json / app.wxss     小程序全局配置
├── pages/
│   ├── index/                       首页、搜索、分类筛选和触底分页
│   ├── category/                    分类导航和分类商品分页
│   ├── product-detail/              商品详情和商品参数
│   ├── login/                       账号密码登录和注册
│   ├── cart/                        购物车列表和商品操作
│   ├── my/                          个人中心
│   ├── profile-edit/                用户信息和密码修改
│   ├── orders/                      订单列表
│   ├── order-confirm/               订单确认和收货地址选择
│   └── order-detail/                订单详情和状态操作
├── utils/
│   ├── config.js                    API 地址、存储键
│   ├── request.js                   wx.request 基础封装
│   ├── api.js                       后端接口封装
│   ├── product.js                   商品和图片格式化
│   └── order.js                     订单状态展示
└── miniprogram_npm/                 Vant Weapp 构建产物
```

## 运行方式

1. 启动后端：

   ```powershell
   python manage.py runserver 127.0.0.1:8000 --noreload
   ```

2. 使用微信开发者工具导入目录：

   ```text
   D:\PycharmProjects\DigRecSys\miniapp
   ```

3. 检查项目配置中的 AppID 和开发环境设置。
4. 如果修改了 Vant 依赖，使用微信开发者工具重新构建 npm；不要直接编辑 `miniprogram_npm/`。
5. 在首页执行搜索、分类切换、触底分页、详情和登录等手工验收，并检查分类页左右区域滚动。

本地 API 地址集中在 `utils/config.js` 的 `API_BASE_URL`。当前值适用于本机开发者工具访问本机后端；真机不能使用 `127.0.0.1`，需要改为局域网可访问地址或已备案的 HTTPS 域名，并在微信公众平台配置 request 合法域名。

## 当前已完成

- 首页：与微信胶囊对齐的吸顶搜索栏和分类 tabs；搜索与分类筛选原地更新商品，页面触底继续分页加载。
- 分类页：使用 Vant Sidebar 切换全部商品或具体分类，展示真实商品数量，并支持独立滚动、下拉刷新、触底分页、空状态和失败重试。
- 商品详情：名称、主图、价格、品牌、分类、产地、库存、评分、评论数和 `all_params` 商品参数；旧商品产地为空时显示“未填写”。
- 账号：复用后端账号密码注册/登录，保存 DRF Token；个人中心支持上传头像，并可修改用户名、邮箱、手机号和密码。
- 购物车：商品详情页可加入购物车并显示商品总件数；购物车页支持完整列表、全选/单选、库存上限、数量修改、SwipeCell 滑动删除、金额汇总和选中结算。
- 商品操作栏：详情页使用 Vant GoodsAction；客服和店铺提供入口，立即购买只显示未开放提示，不调用订单接口。
- 订单：确认页支持选择已有地址或新增地址并提交选中购物车商品；列表和详情展示订单状态、金额、商品明细和收货地址快照，详情支持取消、模拟支付和确认收货。
- 请求层：统一 API 地址、Token 请求头、错误转换和图片地址处理。

## 当前未完成或需要人工验证

- 尚未在微信开发者工具中完成页面编译、跳转、网络异常、空数据和真机验收：`NEEDS_MANUAL_VERIFICATION`。
- 当前认证是项目已有的账号密码 + DRF Token，不是微信身份登录。`wx.login`、`code2Session`、openid/unionid 绑定属于 `NEEDS_FUTURE_AUTH_IMPLEMENTATION`。
- 后端的支付接口目前是模拟状态变更，未接入真实微信支付；小程序明确显示“模拟支付”，不会发起微信支付。
- 收货地址编辑/删除尚未做成独立页面；立即购买暂不调用订单接口。
- 首页触底分页、分类页双栏滚动、订单确认、库存上限提示、滑动删除、头像上传、用户信息和密码修改、地址新增及订单状态操作仍需在微信开发者工具中人工验收。
