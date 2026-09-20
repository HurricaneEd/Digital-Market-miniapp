const {
  PROFILE_STORAGE_KEY,
  TOKEN_STORAGE_KEY,
} = require('./utils/config');

App({
  globalData: {
    token: '',
    profile: null,
  },

  onLaunch() {
    this.globalData.token = wx.getStorageSync(TOKEN_STORAGE_KEY) || '';
    this.globalData.profile = wx.getStorageSync(PROFILE_STORAGE_KEY) || null;
  },
});
