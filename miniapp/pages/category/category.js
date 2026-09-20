const api = require('../../utils/api');
const { formatProduct } = require('../../utils/product');

function buildCategoryList(source) {
  return source.length
    ? [{ id: 'all', code: '', name: '全部商品' }].concat(source)
    : [];
}

Page({
  data: {
    categories: [],
    activeCategory: 0,
    selectedCategoryName: '全部商品',
    products: [],
    total: 0,
    page: 1,
    hasMore: true,
    loadingCategories: true,
    loadingProducts: false,
    loadingMore: false,
    refreshing: false,
    categoryError: '',
    productError: '',
  },

  onLoad() {
    this.loadCategories();
  },

  loadCategories(showLoading = true) {
    const selected = this.data.categories[this.data.activeCategory];
    const selectedCode = selected ? selected.code : '';
    this.setData({
      loadingCategories: showLoading,
      categoryError: '',
    });

    return api.getAllCategories()
      .then((source) => {
        const categories = buildCategoryList(source);
        if (!categories.length) {
          this.setData({
            categories: [],
            products: [],
            total: 0,
            loadingCategories: false,
          });
          return;
        }
        const matchedIndex = categories.findIndex((category) => category.code === selectedCode);
        const activeCategory = matchedIndex >= 0 ? matchedIndex : 0;
        this.setData({
          categories,
          activeCategory,
          selectedCategoryName: categories[activeCategory].name,
          loadingCategories: false,
        });
        return this.loadProducts(true);
      })
      .catch((error) => {
        this.setData({
          loadingCategories: false,
          categoryError: error.message || '分类加载失败，请稍后重试',
        });
      });
  },

  loadProducts(reset) {
    if (!reset && (this.data.loadingProducts || this.data.loadingMore || !this.data.hasMore)) {
      return Promise.resolve();
    }

    const selected = this.data.categories[this.data.activeCategory];
    if (!selected) {
      return Promise.resolve();
    }

    const requestId = reset
      ? (this.productRequestId || 0) + 1
      : this.productRequestId;
    if (reset) {
      this.productRequestId = requestId;
    }
    const page = reset ? 1 : this.data.page;
    this.setData({
      loadingProducts: reset,
      loadingMore: !reset,
      productError: '',
      hasMore: reset ? true : this.data.hasMore,
    });

    return api.getProducts({
      page,
      category: selected.code,
      ordering: 'newest',
    })
      .then((payload) => {
        if (requestId !== this.productRequestId) {
          return;
        }
        const incoming = (Array.isArray(payload) ? payload : (payload.results || []))
          .filter((product) => product.is_active !== false)
          .map(formatProduct);
        this.setData({
          products: reset ? incoming : this.data.products.concat(incoming),
          total: Array.isArray(payload) ? incoming.length : (payload.count || 0),
          page: page + 1,
          hasMore: Boolean(payload && payload.next),
          loadingProducts: false,
          loadingMore: false,
        });
      })
      .catch((error) => {
        if (requestId !== this.productRequestId) {
          return;
        }
        this.setData({
          loadingProducts: false,
          loadingMore: false,
          productError: error.message || '商品加载失败，请稍后重试',
        });
      });
  },

  onCategoryChange(event) {
    const activeCategory = Number(event.detail);
    if (!Number.isInteger(activeCategory) || activeCategory === this.data.activeCategory) {
      return;
    }
    const selected = this.data.categories[activeCategory];
    if (!selected) {
      return;
    }
    this.setData({
      activeCategory,
      selectedCategoryName: selected.name,
      products: [],
      total: 0,
    }, () => this.loadProducts(true));
  },

  onProductScrollToLower() {
    this.loadProducts(false);
  },

  onRefresh() {
    if (this.data.refreshing) {
      return;
    }
    this.setData({ refreshing: true });
    this.loadCategories(false).finally(() => this.setData({ refreshing: false }));
  },

  onPullDownRefresh() {
    this.loadCategories(false).finally(() => wx.stopPullDownRefresh());
  },

  retryCategories() {
    this.loadCategories();
  },

  retryProducts() {
    this.loadProducts(!this.data.products.length);
  },

  openProduct(event) {
    const prodId = event.currentTarget.dataset.prodId;
    wx.navigateTo({
      url: `/pages/product-detail/product-detail?prod_id=${encodeURIComponent(prodId)}`,
    });
  },
});
