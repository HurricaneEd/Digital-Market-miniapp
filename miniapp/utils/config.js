// 开发环境 API 配置。真机或生产环境需要替换为可访问的 HTTPS 域名。
const API_BASE_URL = 'http://127.0.0.1:8000/api';
const MEDIA_BASE_URL = API_BASE_URL.replace(/\/api\/?$/, '');

const TOKEN_STORAGE_KEY = 'digrecsys_token';
const PROFILE_STORAGE_KEY = 'digrecsys_profile';
const CHECKOUT_CART_IDS_STORAGE_KEY = 'digrecsys_checkout_cart_ids';
const BUY_NOW_STORAGE_KEY = 'digrecsys_buy_now';

module.exports = {
  API_BASE_URL,
  BUY_NOW_STORAGE_KEY,
  CHECKOUT_CART_IDS_STORAGE_KEY,
  MEDIA_BASE_URL,
  TOKEN_STORAGE_KEY,
  PROFILE_STORAGE_KEY,
};
