const {
  API_BASE_URL,
  TOKEN_STORAGE_KEY,
} = require('./config');

function buildUrl(path) {
  if (/^https?:\/\//i.test(path)) {
    return path;
  }

  const baseUrl = API_BASE_URL.replace(/\/$/, '');
  const normalizedPath = String(path || '').replace(/^\//, '');
  return normalizedPath ? `${baseUrl}/${normalizedPath}` : baseUrl;
}

function getErrorMessage(data, statusCode) {
  if (data && typeof data === 'object') {
    if (typeof data.detail === 'string') {
      return data.detail;
    }
    if (typeof data.error === 'string') {
      return data.error;
    }

    const messages = Object.keys(data).map((key) => {
      const value = Array.isArray(data[key]) ? data[key].join('、') : data[key];
      return `${key}: ${value}`;
    });
    if (messages.length) {
      return messages.join('；');
    }
  }

  return statusCode ? `请求失败（${statusCode}）` : '网络请求失败，请检查后端服务';
}

function request(options = {}) {
  const token = wx.getStorageSync(TOKEN_STORAGE_KEY);
  const header = Object.assign(
    { 'content-type': 'application/json' },
    options.header || {},
  );

  if (token) {
    header.Authorization = `Token ${token}`;
  }

  return new Promise((resolve, reject) => {
    wx.request({
      url: buildUrl(options.url),
      method: options.method || 'GET',
      data: options.data || {},
      header,
      timeout: options.timeout || 10000,
      success(response) {
        if (response.statusCode >= 200 && response.statusCode < 300) {
          resolve(response.data);
          return;
        }

        reject({
          statusCode: response.statusCode,
          message: getErrorMessage(response.data, response.statusCode),
          data: response.data,
        });
      },
      fail(error) {
        reject({
          statusCode: 0,
          message: '网络请求失败，请检查后端服务是否启动',
          error,
        });
      },
    });
  });
}

function parseUploadData(data) {
  if (typeof data !== 'string') {
    return data;
  }
  try {
    return JSON.parse(data);
  } catch (error) {
    return data;
  }
}

function uploadFile(options = {}) {
  const token = wx.getStorageSync(TOKEN_STORAGE_KEY);
  const header = Object.assign({}, options.header || {});
  if (token) {
    header.Authorization = `Token ${token}`;
  }

  return new Promise((resolve, reject) => {
    wx.uploadFile({
      url: buildUrl(options.url),
      filePath: options.filePath,
      name: options.name || 'file',
      formData: options.formData || {},
      header,
      timeout: options.timeout || 30000,
      success(response) {
        const data = parseUploadData(response.data);
        if (response.statusCode >= 200 && response.statusCode < 300) {
          resolve(data);
          return;
        }
        reject({
          statusCode: response.statusCode,
          message: getErrorMessage(data, response.statusCode),
          data,
        });
      },
      fail(error) {
        reject({
          statusCode: 0,
          message: '头像上传失败，请检查网络后重试',
          error,
        });
      },
    });
  });
}

module.exports = {
  buildUrl,
  request,
  uploadFile,
};
