const api = require('../../utils/api');
const {
  BUY_NOW_STORAGE_KEY,
  TOKEN_STORAGE_KEY,
} = require('../../utils/config');
const { formatProduct, groupParams } = require('../../utils/product');

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

Page({
  data: {
    prodId: '',
    product: null,
    parameterGroups: [],
    loading: true,
    addingCart: false,
    cartInfo: '',
    error: '',
  },

  onLoad(options) {
    const prodId = decodeQuery(options.prod_id);
    this.setData({ prodId });
    if (!prodId) {
      this.setData({ loading: false, error: '缺少商品编号' });
      return;
    }
    this.loadProduct();
  },

  onShow() {
    this.refreshCartCount();
  },

  onPullDownRefresh() {
    this.loadProduct().finally(() => wx.stopPullDownRefresh());
  },

  loadProduct() {
    this.setData({ loading: true, error: '' });
    return api.getProduct(this.data.prodId)
      .then((product) => {
        this.setData({
          product: formatProduct(product),
          parameterGroups: groupParams(product.all_params),
          loading: false,
        });
      })
      .catch((error) => {
        this.setData({
          loading: false,
          error: error.message || '商品详情加载失败，请稍后重试',
        });
      });
  },

  refreshCartCount() {
    if (!wx.getStorageSync(TOKEN_STORAGE_KEY)) {
      this.setData({ cartInfo: '' });
      return Promise.resolve();
    }

    return api.getAllCart()
      .then((items) => {
        const count = items.reduce((total, item) => total + Number(item.count || 0), 0);
        this.setData({ cartInfo: count > 0 ? String(count) : '' });
      })
      .catch(() => this.setData({ cartInfo: '' }));
  },

  requireLogin(content) {
    if (wx.getStorageSync(TOKEN_STORAGE_KEY)) {
      return true;
    }
    wx.showModal({
      title: '需要登录',
      content,
      confirmText: '去登录',
      success: (result) => {
        if (result.confirm) {
          wx.navigateTo({ url: '/pages/login/login' });
        }
      },
    });
    return false;
  },

  addToCart() {
    if (this.data.addingCart || !this.data.product || this.data.product.stock <= 0) {
      return;
    }

    if (!this.requireLogin('登录后才能加入购物车')) {
      return;
    }

    this.setData({ addingCart: true });
    api.addCart(this.data.product.prod_id)
      .then(() => {
        wx.showToast({ title: '已加入购物车', icon: 'success' });
        return this.refreshCartCount();
      })
      .catch((error) => {
        wx.showToast({ title: error.message || '加入购物车失败', icon: 'none' });
      })
      .finally(() => this.setData({ addingCart: false }));
  },

  openCart() {
    wx.switchTab({ url: '/pages/cart/cart' });
  },

  openShop() {
    wx.switchTab({ url: '/pages/index/index' });
  },

  buyNow() {
    const product = this.data.product;
    if (!product || !product.is_active || product.stock < 1) {
      wx.showToast({ title: '商品已下架或库存不足', icon: 'none' });
      return;
    }
    if (!this.requireLogin('登录后才能立即购买')) {
      return;
    }

    wx.setStorageSync(BUY_NOW_STORAGE_KEY, {
      productId: product.prod_id,
      count: 1,
    });
    wx.navigateTo({ url: '/pages/order-confirm/order-confirm?source=direct' });
  },

  retry() {
    this.loadProduct();
  },

  onShareAppMessage() {
    return {
      title: this.data.product ? this.data.product.name : '数智世界商品',
      path: `/pages/product-detail/product-detail?prod_id=${encodeURIComponent(this.data.prodId)}`,
    };
  },
});
