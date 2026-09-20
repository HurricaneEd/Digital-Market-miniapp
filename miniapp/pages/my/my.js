const api = require('../../utils/api');
const {
  PROFILE_STORAGE_KEY,
  TOKEN_STORAGE_KEY,
} = require('../../utils/config');
const { normalizeImageUrl } = require('../../utils/product');

Page({
  data: {
    loggedIn: false,
    profile: null,
    profileInitial: '',
    avatarUrl: '',
    avatarUploading: false,
    avatarMaxSize: 5 * 1024 * 1024,
    loading: false,
    error: '',
  },

  onShow() {
    this.loadProfile();
  },

  loadProfile() {
    const token = wx.getStorageSync(TOKEN_STORAGE_KEY);
    if (!token) {
      this.setData({ loggedIn: false, profile: null, profileInitial: '', avatarUrl: '', avatarUploading: false, loading: false });
      return;
    }

    const cachedProfile = wx.getStorageSync(PROFILE_STORAGE_KEY) || null;
    this.setData({
      loggedIn: true,
      profile: cachedProfile,
      profileInitial: this.getProfileInitial(cachedProfile),
      avatarUrl: normalizeImageUrl(cachedProfile && cachedProfile.avatar),
      loading: true,
      error: '',
    });
    api.getMe()
      .then((profile) => {
        const profileWithAvatar = Object.assign({}, profile, {
          avatarUrl: normalizeImageUrl(profile.avatar),
        });
        wx.setStorageSync(PROFILE_STORAGE_KEY, profile);
        getApp().globalData.profile = profile;
        this.setData({
          profile: profileWithAvatar,
          profileInitial: this.getProfileInitial(profile),
          avatarUrl: profileWithAvatar.avatarUrl,
          loading: false,
        });
      })
      .catch((error) => {
        if (error.statusCode === 401) {
          this.clearSession();
          return;
        }
        this.setData({ loading: false, error: error.message || '用户信息加载失败' });
      });
  },

  afterReadAvatar(event) {
    if (this.data.avatarUploading) {
      return;
    }
    const selected = event.detail && event.detail.file;
    const file = Array.isArray(selected) ? selected[0] : selected;
    const filePath = file && (file.url || file.path || file.tempFilePath);
    if (!filePath) {
      wx.showToast({ title: '未能读取所选图片', icon: 'none' });
      return;
    }

    const previousAvatarUrl = this.data.avatarUrl;
    this.setData({ avatarUploading: true, avatarUrl: filePath });
    api.uploadAvatar(filePath)
      .then((response) => {
        const avatar = response && (response.avatar_url || response.avatar);
        if (!avatar) {
          throw new Error('上传响应缺少头像地址');
        }
        const profile = Object.assign({}, this.data.profile || {}, { avatar });
        wx.setStorageSync(PROFILE_STORAGE_KEY, profile);
        getApp().globalData.profile = profile;
        this.setData({
          profile,
          avatarUrl: normalizeImageUrl(avatar),
        });
        wx.showToast({ title: '头像已更新', icon: 'success' });
      })
      .catch((error) => {
        this.setData({ avatarUrl: previousAvatarUrl });
        wx.showToast({ title: error.message || '头像上传失败', icon: 'none' });
      })
      .finally(() => this.setData({ avatarUploading: false }));
  },

  onAvatarOversize() {
    wx.showToast({ title: '头像不能超过 5MB', icon: 'none' });
  },

  goLogin() {
    wx.navigateTo({ url: '/pages/login/login' });
  },

  goOrders() {
    if (!this.data.loggedIn) {
      this.goLogin();
      return;
    }
    wx.navigateTo({ url: '/pages/orders/orders' });
  },

  goProfileEdit() {
    if (!this.data.loggedIn) {
      this.goLogin();
      return;
    }
    wx.navigateTo({ url: '/pages/profile-edit/profile-edit' });
  },

  logout() {
    wx.showModal({
      title: '退出登录',
      content: '退出后仍可浏览商品，确定退出吗？',
      success: (result) => {
        if (result.confirm) {
          this.clearSession();
        }
      },
    });
  },

  clearSession() {
    wx.removeStorageSync(TOKEN_STORAGE_KEY);
    wx.removeStorageSync(PROFILE_STORAGE_KEY);
    getApp().globalData.token = '';
    getApp().globalData.profile = null;
    this.setData({ loggedIn: false, profile: null, profileInitial: '', avatarUrl: '', avatarUploading: false, loading: false, error: '' });
  },

  getProfileInitial(profile) {
    const name = profile && (profile.nickname || profile.username);
    return name ? name.slice(0, 1) : 'U';
  },
});
