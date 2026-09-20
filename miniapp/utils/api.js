const { request, uploadFile } = require('./request');

function buildQuery(params = {}) {
  const entries = Object.keys(params)
    .filter((key) => params[key] !== undefined && params[key] !== null && params[key] !== '')
    .map((key) => `${encodeURIComponent(key)}=${encodeURIComponent(params[key])}`);

  return entries.length ? `?${entries.join('&')}` : '';
}

function getProducts({ page = 1, search = '', category = '', ordering = '' } = {}) {
  return request({
    url: `/products/${buildQuery({ page, search, category, ordering })}`,
  });
}

function getProduct(prodId) {
  return request({
    url: `/products/${encodeURIComponent(prodId)}/`,
  });
}

function getCategories(page = 1) {
  return request({ url: `/categories/${buildQuery({ page })}` });
}

function register(data) {
  return request({ url: '/users/register/', method: 'POST', data });
}

function login(identifier, password) {
  return request({
    url: '/users/login/',
    method: 'POST',
    data: { identifier, password },
  });
}

function getMe() {
  return request({ url: '/users/me/' });
}

function getProfile() {
  return request({ url: '/users/profile/' });
}

function updateProfile(data) {
  return request({ url: '/users/profile/', method: 'PUT', data });
}

function changePassword(data) {
  return request({ url: '/users/change_password/', method: 'POST', data });
}

function uploadAvatar(filePath) {
  return uploadFile({
    url: '/users/upload_avatar/',
    filePath,
    name: 'avatar',
  });
}

function collectPages(getPage) {
  const items = [];

  function loadPage(page) {
    return getPage(page).then((payload) => {
      if (Array.isArray(payload)) {
        return items.concat(payload);
      }

      items.push(...(payload.results || []));
      return payload.next ? loadPage(page + 1) : items;
    });
  }

  return loadPage(1);
}

function getCart(page = 1) {
  return request({ url: `/cart/${buildQuery({ page })}` });
}

function getAllCart() {
  return collectPages(getCart);
}

function getAllCategories() {
  return collectPages(getCategories);
}

function addCart(productId, count = 1) {
  return request({
    url: '/cart/',
    method: 'POST',
    data: { product_id: productId, count, selected: true },
  });
}

function updateCartItem(cartItemId, data) {
  return request({
    url: `/cart/${encodeURIComponent(cartItemId)}/`,
    method: 'PATCH',
    data,
  });
}

function deleteCartItem(cartItemId) {
  return request({
    url: `/cart/${encodeURIComponent(cartItemId)}/`,
    method: 'DELETE',
  });
}

function getOrders(page = 1) {
  return request({ url: `/orders/${buildQuery({ page })}` });
}

function getAllOrders() {
  return collectPages(getOrders);
}

function getOrder(orderSn) {
  return request({ url: `/orders/${encodeURIComponent(orderSn)}/` });
}

function createOrder(addressId, cartItemIds) {
  return request({
    url: '/orders/',
    method: 'POST',
    data: { address_id: addressId, cart_item_ids: cartItemIds },
  });
}

function createDirectOrder(addressId, productId, count = 1) {
  return request({
    url: '/orders/',
    method: 'POST',
    data: { address_id: addressId, product_id: productId, count },
  });
}

function payOrder(orderSn, paymentMethod = 'wechat') {
  return request({
    url: `/orders/${encodeURIComponent(orderSn)}/pay/`,
    method: 'POST',
    data: { payment_method: paymentMethod },
  });
}

function cancelOrder(orderSn) {
  return request({
    url: `/orders/${encodeURIComponent(orderSn)}/cancel/`,
    method: 'POST',
  });
}

function confirmReceive(orderSn) {
  return request({
    url: `/orders/${encodeURIComponent(orderSn)}/confirm_receive/`,
    method: 'POST',
  });
}

function getAddresses(page = 1) {
  return request({ url: `/addresses/${buildQuery({ page })}` });
}

function getAllAddresses() {
  return collectPages(getAddresses);
}

function createAddress(data) {
  return request({ url: '/addresses/', method: 'POST', data });
}

module.exports = {
  addCart,
  cancelOrder,
  changePassword,
  confirmReceive,
  createAddress,
  createDirectOrder,
  createOrder,
  deleteCartItem,
  getAddresses,
  getAllAddresses,
  getCategories,
  getAllCart,
  getAllCategories,
  getAllOrders,
  getCart,
  getMe,
  getOrder,
  getOrders,
  getProduct,
  getProducts,
  getProfile,
  login,
  payOrder,
  register,
  updateCartItem,
  updateProfile,
  uploadAvatar,
};
