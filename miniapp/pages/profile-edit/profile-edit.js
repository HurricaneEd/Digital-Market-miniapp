const api = require('../../utils/api');
const {
  PROFILE_STORAGE_KEY,
  TOKEN_STORAGE_KEY,
} = require('../../utils/config');

function fieldValue(event) {
  return typeof event.detail === 'string' ? event.detail : '';
}

Page({
  data: {
    loading: true,
    loadError: '',
    username: '',
    email: '',
    phone: '',
    oldPassword: '',
    newPassword: '',
    confirmPassword: '',
    profileError: '',
    passwordError: '',
    savingProfile: false,
    savingPassword: false,
  },

  onLoad() {
    if (!wx.getStorageSync(TOKEN_STORAGE_KEY)) {
      this.goToLogin();
      return;
    }
    this.loadProfile();
  },

  onPullDownRefresh() {
    this.loadProfile().finally(() => wx.stopPullDownRefresh());
  },

  loadProfile() {
    this.setData({ loading: true, loadError: '' });
    return api.getProfile()
      .then((profile) => {
        this.setData({
          username: profile.username || '',
          email: profile.email || '',
          phone: profile.phone || '',
          loading: false,
        });
      })
      .catch((error) => {
        if (error.statusCode === 401) {
          this.clearSessionAndLogin();
          return;
        }
        this.setData({
          loading: false,
          loadError: error.message || '用户信息加载失败',
        });
      });
  },

  setProfileField(event) {
    const field = event.currentTarget.dataset.field;
    this.setData({ [field]: fieldValue(event), profileError: '' });
  },

  setPasswordField(event) {
    const field = event.currentTarget.dataset.field;
    this.setData({ [field]: fieldValue(event), passwordError: '' });
  },

  saveProfile() {
    if (this.data.savingProfile) {
      return;
    }

    const username = this.data.username.trim();
    const email = this.data.email.trim();
    const phone = this.data.phone.trim();
    const validationError = this.validateProfile(username, email, phone);
    if (validationError) {
      this.setData({ profileError: validationError });
      return;
    }

    this.setData({ savingProfile: true, profileError: '' });
    api.updateProfile({ username, email, phone })
      .then((response) => {
        const cachedProfile = wx.getStorageSync(PROFILE_STORAGE_KEY) || {};
        const profile = Object.assign({}, cachedProfile, {
          username: response.username || '',
          nickname: response.nickname || '',
          email: response.email || '',
          phone: response.phone || '',
          avatar: response.avatar || cachedProfile.avatar || '',
        });
        wx.setStorageSync(PROFILE_STORAGE_KEY, profile);
        getApp().globalData.profile = profile;
        this.setData({
          username: profile.username,
          email: profile.email,
          phone: profile.phone,
        });
        wx.showToast({ title: '用户信息已更新', icon: 'success' });
      })
      .catch((error) => {
        if (error.statusCode === 401) {
          this.clearSessionAndLogin();
          return;
        }
        this.setData({ profileError: error.message || '用户信息更新失败' });
      })
      .finally(() => this.setData({ savingProfile: false }));
  },

  savePassword() {
    if (this.data.savingPassword) {
      return;
    }

    const validationError = this.validatePassword();
    if (validationError) {
      this.setData({ passwordError: validationError });
      return;
    }

    this.setData({ savingPassword: true, passwordError: '' });
    api.changePassword({
      old_password: this.data.oldPassword,
      new_password: this.data.newPassword,
      confirm_password: this.data.confirmPassword,
    })
      .then(() => {
        this.setData({
          oldPassword: '',
          newPassword: '',
          confirmPassword: '',
        });
        wx.showToast({ title: '密码修改成功', icon: 'success' });
      })
      .catch((error) => {
        if (error.statusCode === 401) {
          this.clearSessionAndLogin();
          return;
        }
        this.setData({ passwordError: error.message || '密码修改失败' });
      })
      .finally(() => this.setData({ savingPassword: false }));
  },

  validateProfile(username, email, phone) {
    if (!username) {
      return '用户名不能为空';
    }
    if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      return '邮箱格式不正确';
    }
    if (phone && !/^1[3-9]\d{9}$/.test(phone)) {
      return '手机号格式不正确';
    }
    return '';
  },

  validatePassword() {
    if (!this.data.oldPassword || !this.data.newPassword || !this.data.confirmPassword) {
      return '请完整填写密码信息';
    }
    if (this.data.newPassword.length < 6) {
      return '新密码不能少于 6 位';
    }
    if (this.data.newPassword !== this.data.confirmPassword) {
      return '两次输入的新密码不一致';
    }
    return '';
  },

  retryLoad() {
    this.loadProfile();
  },

  goToLogin() {
    wx.showToast({ title: '请先登录', icon: 'none' });
    setTimeout(() => wx.redirectTo({ url: '/pages/login/login' }), 400);
  },

  clearSessionAndLogin() {
    wx.removeStorageSync(TOKEN_STORAGE_KEY);
    wx.removeStorageSync(PROFILE_STORAGE_KEY);
    getApp().globalData.token = '';
    getApp().globalData.profile = null;
    this.goToLogin();
  },
});
