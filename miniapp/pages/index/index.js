const api = require('../../utils/api');
const { formatProduct } = require('../../utils/product');

function getSearchValue(event) {
  if (typeof event.detail === 'string') {
    return event.detail.trim();
  }
  return event.detail && event.detail.value ? event.detail.value.trim() : '';
}

Page({
  data: {
    statusBarHeight: 0,
    navHeight: 64,
    menuButtonHeight: 32,
    menuButtonRightGap: 16,
    active: 0,
    category: '',
    sectionTitle: '最新商品',
    searchKeyword: '',
    categories: [],
    products: [],
    page: 1,
    hasMore: true,
    loading: true,
    loadingMore: false,
    error: '',
  },

  onLoad() {
    this.initNavigation();
    this.loadCategories().then(() => this.loadProducts(true));
  },

  initNavigation() {
    const windowInfo = wx.getWindowInfo ? wx.getWindowInfo() : wx.getSystemInfoSync();
    const statusBarHeight = windowInfo.statusBarHeight || 0;
    const windowWidth = windowInfo.windowWidth || windowInfo.screenWidth || 375;
    const fallbackMenuButton = {
      top: statusBarHeight + 8,
      bottom: statusBarHeight + 40,
      height: 32,
      left: windowWidth - 96,
    };
    const menuButton = wx.getMenuButtonBoundingClientRect
      ? wx.getMenuButtonBoundingClientRect()
      : fallbackMenuButton;
    const menuButtonHeight = menuButton.height || fallbackMenuButton.height;
    const navHeight = menuButton.bottom + Math.max(menuButton.top - statusBarHeight, 0);
    const menuButtonRightGap = Math.max(windowWidth - menuButton.left + 8, 16);
    this.setData({
      statusBarHeight,
      navHeight: navHeight || statusBarHeight + menuButtonHeight + 16,
      menuButtonHeight,
      menuButtonRightGap,
    });
  },

  onPullDownRefresh() {
    this.loadCategories()
      .then(() => this.loadProducts(true))
      .finally(() => wx.stopPullDownRefresh());
  },

  loadCategories() {
    return api.getAllCategories()
      .then((payload) => {
        const source = Array.isArray(payload) ? payload : (payload.results || []);
        const categories = source.slice();
        const matchedIndex = categories.findIndex(
          (category) => category.code === this.data.category,
        );
        const active = matchedIndex >= 0 ? matchedIndex + 1 : 0;
        const selectedCategory = active > 0 ? categories[active - 1] : null;
        this.setData({
          categories,
          active,
          category: selectedCategory ? selectedCategory.code : '',
          sectionTitle: this.getSectionTitle(selectedCategory),
        });
      })
      .catch(() => {
        this.setData({
          categories: [],
          active: 0,
          category: '',
          sectionTitle: this.getSectionTitle(null),
        });
      });
  },

  loadProducts(reset) {
    if (!reset && (this.data.loading || this.data.loadingMore || !this.data.hasMore)) {
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
      loading: reset,
      loadingMore: !reset,
      hasMore: reset ? true : this.data.hasMore,
      error: '',
    });
    return api.getProducts({
      page,
      search: this.data.searchKeyword,
      ordering: 'newest',
      category: this.data.category,
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
          page: page + 1,
          hasMore: Boolean(payload && payload.next),
          loading: false,
          loadingMore: false,
        });
      })
      .catch((error) => {
        if (requestId !== this.productRequestId) {
          return;
        }
        this.setData({
          loading: false,
          loadingMore: false,
          error: error.message || '商品加载失败，请稍后重试',
        });
      });
  },

  onSearchChange(event) {
    this.setData({ searchKeyword: getSearchValue(event) });
  },

  onSearch(event) {
    const keyword = getSearchValue(event) || this.data.searchKeyword;
    this.setData({
      searchKeyword: keyword,
      sectionTitle: this.getSectionTitle(this.getSelectedCategory(), keyword),
    }, () => this.loadProducts(true));
  },

  onSearchClear() {
    this.setData({
      searchKeyword: '',
      sectionTitle: this.getSectionTitle(this.getSelectedCategory(), ''),
    }, () => this.loadProducts(true));
  },

  onChange(event) {
    const detail = event.detail || {};
    const active = typeof detail.index === 'number' ? detail.index : parseInt(detail.index, 10) || 0;
    const selectedCategory = active > 0 ? this.data.categories[active - 1] : null;
    this.setData({
      active,
      category: selectedCategory ? selectedCategory.code : '',
      sectionTitle: this.getSectionTitle(selectedCategory),
    }, () => this.loadProducts(true));
  },

  openProduct(event) {
    const prodId = event.currentTarget.dataset.prodId;
    wx.navigateTo({
      url: `/pages/product-detail/product-detail?prod_id=${encodeURIComponent(prodId)}`,
    });
  },

  retryProducts() {
    this.loadProducts(!this.data.products.length);
  },

  onReachBottom() {
    this.loadProducts(false);
  },

  getSelectedCategory() {
    return this.data.active > 0 ? this.data.categories[this.data.active - 1] : null;
  },

  getSectionTitle(category, keyword = this.data.searchKeyword) {
    if (keyword) {
      return `“${keyword}”的搜索结果`;
    }
    return category ? category.name : '最新商品';
  },
});
