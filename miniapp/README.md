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
