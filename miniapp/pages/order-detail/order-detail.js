const api = require('../../utils/api');
const { formatPrice, normalizeImageUrl } = require('../../utils/product');
const { getOrderStatusLabel } = require('../../utils/order');

function decodeQuery(value) {
  if (!value) {
    return '';
  }
  try {
    return decodeURIComponent(value);
  } catch (error) {
    return value;
  }
}

function formatItem(item) {
  return Object.assign({}, item, {
    imageUrl: normalizeImageUrl(item.product_img),
    displayPrice: formatPrice(item.price),
  });
}

function formatOrder(order) {
  return Object.assign({}, order, {
    displayTotalPrice: formatPrice(order.total_price),
    statusLabel: getOrderStatusLabel(order.status),
    displayItems: (order.items || []).map(formatItem),
    canPay: order.status === 'unpaid',
    canCancel: order.status === 'unpaid' || order.status === 'paid',
    canConfirmReceive: order.status === 'shipped',
  });
}

Page({
  data: {
    orderSn: '',
    order: null,
    loading: true,
    actionLoading: false,
    actionType: '',
    error: '',
  },

  onLoad(options) {
    const orderSn = decodeQuery(options.order_sn);
    this.setData({ orderSn });
    if (!orderSn) {
      this.setData({ loading: false, error: '缺少订单号' });
      return;
    }
    this.loadOrder();
  },

  onPullDownRefresh() {
    this.loadOrder().finally(() => wx.stopPullDownRefresh());
  },

  loadOrder() {
    this.setData({ loading: true, error: '' });
    return api.getOrder(this.data.orderSn)
      .then((order) => {
        this.setData({
          order: formatOrder(order),
          loading: false,
        });
      })
      .catch((error) => {
        this.setData({ loading: false, error: error.message || '订单详情加载失败' });
      });
  },

  runOrderAction(actionType, action, successMessage) {
    if (this.data.actionLoading) {
      return;
    }
    this.setData({ actionLoading: true, actionType });
    action()
      .then(() => {
        wx.showToast({ title: successMessage, icon: 'success' });
        return this.loadOrder();
      })
      .catch((error) => {
        wx.showToast({ title: error.message || '订单操作失败', icon: 'none' });
      })
      .finally(() => this.setData({ actionLoading: false, actionType: '' }));
  },

  cancelOrder() {
    wx.showModal({
      title: '取消订单',
      content: '取消后库存将恢复，确定取消该订单吗？',
      confirmColor: '#ee0a24',
      success: (result) => {
        if (result.confirm) {
          this.runOrderAction(
            'cancel',
            () => api.cancelOrder(this.data.orderSn),
            '订单已取消',
          );
        }
      },
    });
  },

  payOrder() {
    wx.showModal({
      title: '模拟支付',
      content: '当前仅调用后端模拟支付接口，不会发起真实微信支付。是否继续？',
      confirmText: '继续',
      success: (result) => {
        if (result.confirm) {
          this.runOrderAction(
            'pay',
            () => api.payOrder(this.data.orderSn, 'wechat'),
            '模拟支付成功',
          );
        }
      },
    });
  },

  confirmReceive() {
    wx.showModal({
      title: '确认收货',
      content: '确认已经收到商品吗？',
      success: (result) => {
        if (result.confirm) {
          this.runOrderAction(
            'confirm',
            () => api.confirmReceive(this.data.orderSn),
            '已确认收货',
          );
        }
      },
    });
  },

  retry() {
    this.loadOrder();
  },
});
