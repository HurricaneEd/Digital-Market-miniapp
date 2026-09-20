const { MEDIA_BASE_URL } = require('./config');

function formatPrice(value) {
  if (value === undefined || value === null || value === '') {
    return '0.00';
  }

  const numericValue = Number(value);
  return Number.isNaN(numericValue) ? String(value) : numericValue.toFixed(2);
}

function normalizeImageUrl(imageUrl) {
  if (!imageUrl) {
    return '';
  }
  if (/^https?:\/\//i.test(imageUrl)) {
    return imageUrl;
  }

  const suffix = imageUrl.charAt(0) === '/' ? imageUrl : `/${imageUrl}`;
  return `${MEDIA_BASE_URL}${suffix}`;
}

function formatProduct(product) {
  return Object.assign({}, product, {
    displayPrice: formatPrice(product.price),
    imageUrl: normalizeImageUrl(product.img_url),
    stockLabel: product.stock > 0 ? `库存 ${product.stock}` : '暂时无货',
  });
}

function formatParamValue(value) {
  if (Array.isArray(value)) {
    return value.join('、');
  }
  if (value && typeof value === 'object') {
    return JSON.stringify(value);
  }
  return value === undefined || value === null ? '' : String(value);
}

function groupParams(allParams) {
  if (!allParams || typeof allParams !== 'object' || Array.isArray(allParams)) {
    return [];
  }

  return Object.keys(allParams).map((groupName) => {
    const group = allParams[groupName];
    const entries = group && typeof group === 'object' && !Array.isArray(group)
      ? Object.keys(group).map((key) => ({ key, value: formatParamValue(group[key]) }))
      : [{ key: '参数', value: formatParamValue(group) }];

    return { name: groupName, entries };
  });
}

module.exports = {
  formatPrice,
  formatProduct,
  groupParams,
  normalizeImageUrl,
};
