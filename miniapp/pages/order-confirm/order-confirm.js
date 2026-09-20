const api = require('../../utils/api');
const {
  BUY_NOW_STORAGE_KEY,
  CHECKOUT_CART_IDS_STORAGE_KEY,
  TOKEN_STORAGE_KEY,
} = require('../../utils/config');
const { formatPrice, normalizeImageUrl } = require('../../utils/product');

function priceToCents(value) {
  const amount = Number(value);
  return Number.isFinite(amount) ? Math.round(amount * 100) : 0;
}

function formatCheckoutItem(item) {
  const product = item.product || {};
  const count = Number(item.count || 0);
  const stock = Number(product.stock || 0);
  const priceCents = priceToCents(product.price);
  return Object.assign({}, item, {
    count,
    stockIssue: product.is_active === false || stock < count,
    displaySubtotal: formatPrice((priceCents * count) / 100),
    priceCents,
    product: Object.assign({}, product, {
      displayPrice: formatPrice(product.price),
      imageUrl: normalizeImageUrl(product.img_url),
      stock,
    }),
  });
}

Page({
  data: {
    checkoutMode: 'cart',
    directPurchase: null,
    cartItemIds: [],
    items: [],
    addresses: [],
    selectedAddressId: 0,
    totalCents: 0,
    loading: true,
    submitting: false,
    savingAddress: false,
    showAddressForm: false,
    hasStockIssue: false,
    error: '',
    addressForm: {
      receiver: '',
      phone: '',
      detail: '',
      is_default: false,
    },
  },

  onLoad(options = {}) {
    if (!wx.getStorageSync(TOKEN_STORAGE_KEY)) {
      this.setData({ loading: false, error: '请先登录后提交订单' });
      return;
    }

    if (options.source === 'direct') {
      const directPurchase = wx.getStorageSync(BUY_NOW_STORAGE_KEY);
      const count = Number(directPurchase && directPurchase.count);
      if (!directPurchase || !directPurchase.productId || count < 1) {
        this.setData({ loading: false, error: '没有有效的立即购买商品' });
        return;
      }
      this.setData({
        checkoutMode: 'direct',
        directPurchase: {
          productId: String(directPurchase.productId),
          count,
        },
      });
      this.loadCheckout();
      return;
    }

    const cartItemIds = wx.getStorageSync(CHECKOUT_CART_IDS_STORAGE_KEY);
    if (!Array.isArray(cartItemIds) || !cartItemIds.length) {
      this.setData({ loading: false, error: '没有待结算的购物车商品' });
      return;
    }
    const normalizedIds = cartItemIds.map(Number).filter(Boolean);
    if (!normalizedIds.length) {
      this.setData({ loading: false, error: '没有有效的待结算商品' });
      return;
    }
    this.setData({ cartItemIds: normalizedIds });
    this.loadCheckout();
  },

  onPullDownRefresh() {
    this.loadCheckout().finally(() => wx.stopPullDownRefresh());
  },

  loadCheckout() {
    const isDirect = this.data.checkoutMode === 'direct';
    if (isDirect && !this.data.directPurchase) {
      this.setData({ loading: false, error: '没有有效的立即购买商品' });
      return Promise.resolve();
    }
    if (!isDirect && !this.data.cartItemIds.length) {
      this.setData({ loading: false, error: '没有待结算的购物车商品' });
      return Promise.resolve();
    }
    this.setData({ loading: true, error: '' });
    const productRequest = isDirect
      ? api.getProduct(this.data.directPurchase.productId)
      : api.getAllCart();
    return Promise.all([productRequest, api.getAllAddresses()])
      .then(([checkoutSource, addresses]) => {
        let items;
        if (isDirect) {
          const directPurchase = this.data.directPurchase;
          items = [formatCheckoutItem({
            id: `direct-${directPurchase.productId}`,
            product: checkoutSource,
            count: directPurchase.count,
          })];
        } else {
          const idSet = new Set(this.data.cartItemIds);
          items = checkoutSource
            .filter((item) => idSet.has(Number(item.id)))
            .map(formatCheckoutItem);
          if (items.length !== idSet.size) {
            throw new Error('部分购物车商品已变化，请返回购物车重新选择');
          }
        }

        const selectedAddress = addresses.find(
          (address) => address.id === this.data.selectedAddressId,
        );
        const defaultAddress = selectedAddress
          || addresses.find((address) => address.is_default)
          || addresses[0]
          || null;
        this.setData({
          items,
          addresses,
          selectedAddressId: defaultAddress ? defaultAddress.id : 0,
          totalCents: items.reduce(
            (total, item) => total + item.priceCents * item.count,
            0,
          ),
          hasStockIssue: items.some((item) => item.stockIssue),
          showAddressForm: addresses.length === 0,
          loading: false,
        });
      })
      .catch((error) => {
        this.setData({
          loading: false,
          error: error.message || '订单确认信息加载失败',
        });
      });
  },

  selectAddress(event) {
    this.setData({ selectedAddressId: Number(event.currentTarget.dataset.addressId) });
  },

  toggleAddressForm() {
    this.setData({ showAddressForm: !this.data.showAddressForm });
  },

  setAddressField(event) {
    const field = event.currentTarget.dataset.field;
    this.setData({ [`addressForm.${field}`]: String(event.detail || '') });
  },

  onDefaultChange(event) {
    this.setData({ 'addressForm.is_default': Boolean(event.detail) });
  },

  saveAddress() {
    if (this.data.savingAddress) {
      return;
    }
    const form = Object.assign({}, this.data.addressForm, {
      receiver: this.data.addressForm.receiver.trim(),
      phone: this.data.addressForm.phone.trim(),
      detail: this.data.addressForm.detail.trim(),
    });
    if (!form.receiver || !form.phone || !form.detail) {
      wx.showToast({ title: '请完整填写收货信息', icon: 'none' });
      return;
    }
    if (!/^1[3-9]\d{9}$/.test(form.phone)) {
      wx.showToast({ title: '手机号格式不正确', icon: 'none' });
      return;
    }

    this.setData({ savingAddress: true });
    api.createAddress(form)
      .then((address) => {
        const addresses = this.data.addresses
          .map((item) => Object.assign({}, item, {
            is_default: address.is_default ? false : item.is_default,
          }))
          .concat(address);
        this.setData({
          addresses,
          selectedAddressId: address.id,
          showAddressForm: false,
          addressForm: {
            receiver: '',
            phone: '',
            detail: '',
            is_default: false,
          },
        });
        wx.showToast({ title: '地址已保存', icon: 'success' });
      })
      .catch((error) => {
        wx.showToast({ title: error.message || '地址保存失败', icon: 'none' });
      })
      .finally(() => this.setData({ savingAddress: false }));
  },

  submitOrder() {
    if (
      this.data.submitting
      || !this.data.selectedAddressId
      || !this.data.items.length
      || this.data.hasStockIssue
    ) {
      return;
    }

    this.setData({ submitting: true });
    const createRequest = this.data.checkoutMode === 'direct'
      ? api.createDirectOrder(
        this.data.selectedAddressId,
        this.data.directPurchase.productId,
        this.data.directPurchase.count,
      )
      : api.createOrder(this.data.selectedAddressId, this.data.cartItemIds);
    createRequest
      .then((order) => {
        const storageKey = this.data.checkoutMode === 'direct'
          ? BUY_NOW_STORAGE_KEY
          : CHECKOUT_CART_IDS_STORAGE_KEY;
        wx.removeStorageSync(storageKey);
        wx.showToast({ title: '订单提交成功', icon: 'success' });
        setTimeout(() => {
          wx.redirectTo({
            url: `/pages/order-detail/order-detail?order_sn=${encodeURIComponent(order.order_sn)}`,
          });
        }, 500);
      })
      .catch((error) => {
        wx.showToast({ title: error.message || '订单提交失败', icon: 'none' });
        this.setData({ submitting: false });
        return this.loadCheckout();
      });
  },

  retry() {
    this.loadCheckout();
  },
});
