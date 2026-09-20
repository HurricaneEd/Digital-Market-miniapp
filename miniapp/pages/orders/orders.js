const api = require('../../utils/api');
const { TOKEN_STORAGE_KEY } = require('../../utils/config');
const { formatPrice, normalizeImageUrl } = require('../../utils/product');
const { getOrderStatusLabel } = require('../../utils/order');

function formatOrder(order) {
  const items = (order.items || []).map((item) => Object.assign({}, item, {
    imageUrl: normalizeImageUrl(item.product_img),
    displayPrice: formatPrice(item.price),
  }));
  return Object.assign({}, order, {
    displayTotalPrice: formatPrice(order.total_price),
    statusLabel: getOrderStatusLabel(order.status),
    firstItem: items[0] || null,
    itemCount: items.reduce((total, item) => total + Number(item.count || 0), 0),
  });
}

Page({
  data: {
    orders: [],
    loading: true,
    error: '',
  },

  onShow() {
    if (!wx.getStorageSync(TOKEN_STORAGE_KEY)) {
      this.setData({ loading: false, error: '请先登录后查看订单' });
      return;
    }
    this.loadOrders();
  },

  onPullDownRefresh() {
    this.loadOrders().finally(() => wx.stopPullDownRefresh());
  },

  loadOrders() {
    this.setData({ loading: true, error: '' });
    return api.getAllOrders()
      .then((payload) => {
        const orders = payload.map(formatOrder);
        this.setData({ orders, loading: false });
      })
      .catch((error) => {
        this.setData({ loading: false, error: error.message || '订单加载失败，请稍后重试' });
      });
  },

  goLogin() {
    wx.navigateTo({ url: '/pages/login/login' });
  },

  openOrder(event) {
    const orderSn = event.currentTarget.dataset.orderSn;
    wx.navigateTo({
      url: `/pages/order-detail/order-detail?order_sn=${encodeURIComponent(orderSn)}`,
    });
  },
});
