const api = require('../../utils/api');
const {
  CHECKOUT_CART_IDS_STORAGE_KEY,
  TOKEN_STORAGE_KEY,
} = require('../../utils/config');
const { formatPrice, normalizeImageUrl } = require('../../utils/product');

function priceToCents(value) {
  const amount = Number(value);
  return Number.isFinite(amount) ? Math.round(amount * 100) : 0;
}

function formatCartItem(item) {
  const product = item.product || {};
  const count = Math.max(1, Number(item.count) || 1);
  const priceCents = priceToCents(product.price);
  const stock = Math.max(0, Number(product.stock) || 0);
  const isActive = product.is_active !== false;

  return Object.assign({}, item, {
    count,
    selected: Boolean(item.selected),
    updating: false,
    priceCents,
    stockIssue: !isActive || count > stock || stock === 0,
    displaySubtotal: formatPrice((priceCents * count) / 100),
    product: Object.assign({}, product, {
      displayPrice: formatPrice(product.price),
      imageUrl: normalizeImageUrl(product.img_url),
      is_active: isActive,
      stock,
    }),
    maxCount: Math.max(1, stock),
  });
}

function summarize(items) {
  const selectedItems = items.filter((item) => item.selected);
  const purchasableItems = items.filter((item) => !item.stockIssue);
  const hasStockIssue = selectedItems.some((item) => item.stockIssue);
  return {
    allSelected: purchasableItems.length > 0
      && purchasableItems.every((item) => item.selected),
    cartCount: items.reduce((total, item) => total + item.count, 0),
    selectedCount: selectedItems.reduce((total, item) => total + item.count, 0),
    selectedTotalCents: selectedItems.reduce(
      (total, item) => total + item.priceCents * item.count,
      0,
    ),
    canCheckout: selectedItems.length > 0 && !hasStockIssue,
  };
}

Page({
  data: {
    items: [],
    loading: true,
    needLogin: false,
    bulkUpdating: false,
    error: '',
    allSelected: false,
    cartCount: 0,
    selectedCount: 0,
    selectedTotalCents: 0,
    canCheckout: false,
  },

  onShow() {
    if (!wx.getStorageSync(TOKEN_STORAGE_KEY)) {
      this.applyItems([]);
      this.setData({ loading: false, needLogin: true, error: '' });
      return;
    }

    this.setData({ needLogin: false });
    this.loadCart();
  },

  onPullDownRefresh() {
    const task = wx.getStorageSync(TOKEN_STORAGE_KEY)
      ? this.loadCart(false)
      : Promise.resolve();
    task.finally(() => wx.stopPullDownRefresh());
  },

  loadCart(showLoading = true) {
    if (showLoading) {
      this.setData({ loading: true });
    }
    this.setData({ error: '' });

    return api.getAllCart()
      .then((items) => {
        this.applyItems(items.map(formatCartItem));
        this.setData({ loading: false, needLogin: false });
      })
      .catch((error) => {
        if (error.statusCode === 401 || error.statusCode === 403) {
          this.applyItems([]);
          this.setData({ loading: false, needLogin: true, error: '' });
          return;
        }
        this.setData({
          loading: false,
          error: error.message || '购物车加载失败，请稍后重试',
        });
      });
  },

  applyItems(items) {
    this.setData(Object.assign({ items }, summarize(items)));
  },

  setItemUpdating(cartItemId, updating) {
    const items = this.data.items.map((item) => (
      item.id === cartItemId ? Object.assign({}, item, { updating }) : item
    ));
    this.applyItems(items);
  },

  updateItem(cartItemId, data) {
    const currentItem = this.data.items.find((item) => item.id === cartItemId);
    if (!currentItem || currentItem.updating) {
      return Promise.resolve();
    }

    this.setItemUpdating(cartItemId, true);
    return api.updateCartItem(cartItemId, data)
      .then((updatedItem) => {
        const items = this.data.items.map((item) => (
          item.id === cartItemId ? formatCartItem(updatedItem) : item
        ));
        this.applyItems(items);
      })
      .catch((error) => {
        this.setItemUpdating(cartItemId, false);
        wx.showToast({ title: error.message || '购物车更新失败', icon: 'none' });
      });
  },

  onSelectedChange(event) {
    const cartItemId = Number(event.currentTarget.dataset.cartItemId);
    const selected = Boolean(event.detail);
    const item = this.data.items.find((candidate) => candidate.id === cartItemId);
    if (selected && item && item.stockIssue) {
      wx.showToast({ title: '请先将数量调整到库存范围内', icon: 'none' });
      return;
    }
    this.updateItem(cartItemId, { selected });
  },

  onQuantityChange(event) {
    const cartItemId = Number(event.currentTarget.dataset.cartItemId);
    const count = Number(event.detail);
    const currentItem = this.data.items.find((item) => item.id === cartItemId);
    if (!currentItem || !Number.isInteger(count) || count < 1 || count === currentItem.count) {
      return;
    }
    this.updateItem(cartItemId, { count });
  },

  onQuantityOverlimit(event) {
    if (event.detail === 'plus') {
      wx.showToast({ title: '已达到当前库存上限', icon: 'none' });
    }
  },

  adjustToStock(event) {
    const cartItemId = Number(event.currentTarget.dataset.cartItemId);
    const item = this.data.items.find((candidate) => candidate.id === cartItemId);
    if (!item || item.product.stock < 1) {
      return;
    }
    this.updateItem(cartItemId, { count: item.product.stock });
  },

  onSelectAll(event) {
    if (this.data.bulkUpdating || !this.data.items.length) {
      return;
    }

    const selected = Boolean(event.detail);
    const changedItems = this.data.items
      .map((item) => Object.assign({}, item, {
        targetSelected: item.stockIssue ? false : selected,
      }))
      .filter((item) => item.selected !== item.targetSelected);
    if (!changedItems.length) {
      return;
    }

    this.setData({ bulkUpdating: true });
    Promise.all(changedItems.map((item) => (
      api.updateCartItem(item.id, { selected: item.targetSelected })
        .then((updatedItem) => ({ updatedItem }))
        .catch((error) => ({ error }))
    )))
      .then((results) => {
        const failedResult = results.find((result) => result.error);
        if (failedResult) {
          wx.showToast({
            title: failedResult.error.message || '全选状态更新失败',
            icon: 'none',
          });
          return this.loadCart(false);
        }

        const updates = {};
        results.forEach(({ updatedItem: item }) => {
          updates[item.id] = formatCartItem(item);
        });
        this.applyItems(this.data.items.map((item) => updates[item.id] || item));
      })
      .finally(() => this.setData({ bulkUpdating: false }));
  },

  deleteItem(event) {
    const cartItemId = Number(event.currentTarget.dataset.cartItemId);
    const item = this.data.items.find((candidate) => candidate.id === cartItemId);
    if (!item || item.updating) {
      return;
    }

    wx.showModal({
      title: '删除商品',
      content: `确定从购物车删除“${item.product.name}”吗？`,
      confirmColor: '#ee0a24',
      success: (result) => {
        if (!result.confirm) {
          return;
        }
        this.setItemUpdating(cartItemId, true);
        api.deleteCartItem(cartItemId)
          .then(() => {
            this.applyItems(this.data.items.filter((candidate) => candidate.id !== cartItemId));
            wx.showToast({ title: '已删除', icon: 'success' });
          })
          .catch((error) => {
            this.setItemUpdating(cartItemId, false);
            wx.showToast({ title: error.message || '删除失败', icon: 'none' });
          });
      },
    });
  },

  openProduct(event) {
    const prodId = event.currentTarget.dataset.prodId;
    if (!prodId) {
      return;
    }
    wx.navigateTo({
      url: `/pages/product-detail/product-detail?prod_id=${encodeURIComponent(prodId)}`,
    });
  },

  goLogin() {
    wx.navigateTo({ url: '/pages/login/login' });
  },

  retry() {
    this.loadCart();
  },

  checkout() {
    if (!this.data.canCheckout) {
      return;
    }
    const cartItemIds = this.data.items
      .filter((item) => item.selected && !item.stockIssue)
      .map((item) => item.id);
    wx.setStorageSync(CHECKOUT_CART_IDS_STORAGE_KEY, cartItemIds);
    wx.navigateTo({ url: '/pages/order-confirm/order-confirm' });
  },
});
