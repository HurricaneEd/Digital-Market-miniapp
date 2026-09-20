const STATUS_LABELS = {
  unpaid: '待支付',
  paid: '已支付',
  shipped: '已发货',
  completed: '已完成',
  cancelled: '已取消',
};

function getOrderStatusLabel(status) {
  return STATUS_LABELS[status] || status || '未知状态';
}

module.exports = {
  getOrderStatusLabel,
};
