const api = require('../../utils/api');
const {
  PROFILE_STORAGE_KEY,
  TOKEN_STORAGE_KEY,
} = require('../../utils/config');

function getValue(event) {
  return typeof event.detail === 'string' ? event.detail.trim() : '';
}

Page({
  data: {
    mode: 'login',
    identifier: '',
    password: '',
    username: '',
    phone: '',
    email: '',
    confirmPassword: '',
    submitting: false,
    error: '',
  },

  onLoad(options) {
    if (options && options.mode === 'register') {
      this.setData({ mode: 'register' });
    }
  },

  setField(event) {
    const field = event.currentTarget.dataset.field;
    this.setData({ [field]: getValue(event) });
  },

  switchMode() {
    this.setData({
      mode: this.data.mode === 'login' ? 'register' : 'login',
      error: '',
    });
  },

  submit() {
    if (this.data.submitting) {
      return;
    }

    const validationError = this.validate();
    if (validationError) {
      this.setData({ error: validationError });
      return;
    }

    this.setData({ submitting: true, error: '' });
    const action = this.data.mode === 'login'
      ? api.login(this.data.identifier, this.data.password)
      : api.register({
        username: this.data.username,
        phone: this.data.phone,
        email: this.data.email,
        password: this.data.password,
      });

    action
      .then((response) => this.finishLogin(response))
      .catch((error) => {
        this.setData({ error: error.message || '操作失败，请稍后重试' });
      })
      .finally(() => this.setData({ submitting: false }));
  },

  validate() {
    if (this.data.mode === 'login') {
      if (!this.data.identifier || !this.data.password) {
        return '请输入账号和密码';
      }
      return '';
    }

    if (!this.data.username || !this.data.phone || !this.data.email || !this.data.password) {
      return '请完整填写注册信息';
    }
    if (this.data.password !== this.data.confirmPassword) {
      return '两次输入的密码不一致';
    }
    return '';
  },

  finishLogin(response) {
    const token = response && response.token;
    if (!token) {
      throw new Error('登录响应缺少 Token');
    }

    wx.setStorageSync(TOKEN_STORAGE_KEY, token);
    const profile = response.user_profile || {
      username: response.username || this.data.username,
      avatar: response.avatar || '',
    };
    wx.setStorageSync(PROFILE_STORAGE_KEY, profile);

    const app = getApp();
    app.globalData.token = token;
    app.globalData.profile = profile;

    wx.showToast({ title: '登录成功', icon: 'success' });
    setTimeout(() => {
      const pages = getCurrentPages();
      if (pages.length > 1) {
        wx.navigateBack();
      } else {
        wx.switchTab({ url: '/pages/my/my' });
      }
    }, 500);
  },
});
