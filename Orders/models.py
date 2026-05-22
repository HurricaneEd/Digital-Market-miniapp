from django.db import models

from Users.models import User
from Product.models import CleanProduct


class Address(models.Model):
    """收货地址"""
    id = models.BigAutoField(primary_key=True)  # 显式主键，bigint类型
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    receiver = models.CharField(max_length=50, verbose_name="收货人")
    phone = models.CharField(max_length=11, verbose_name="手机号")
    detail = models.CharField(max_length=255, verbose_name="详细地址")
    is_default = models.BooleanField(default=False, verbose_name="是否默认")

    class Meta:
        db_table = 'order_address'
        verbose_name = '收货地址'


class Order(models.Model):
    """订单表"""
    id = models.BigAutoField(primary_key=True)  # 显式主键，bigint类型
    ORDER_STATUS = (('unpaid', '待支付'), ('paid', '已支付'), ('shipped', '已发货'), ('completed', '已完成'), ('cancelled', '已取消'))
    PAYMENT_METHODS = (('wechat', '微信支付'), ('alipay', '支付宝'))
    order_sn = models.CharField(max_length=50, unique=True, verbose_name="订单号")
    user = models.ForeignKey(User, on_delete=models.PROTECT)
    address = models.ForeignKey(Address, on_delete=models.PROTECT, null=True, blank=True, verbose_name="收货地址")
    total_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="订单总价")
    status = models.CharField(max_length=20, choices=ORDER_STATUS, default='unpaid')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, null=True, blank=True, verbose_name="支付方式")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'orders'


class OrderItem(models.Model):
    """订单详情"""
    id = models.BigAutoField(primary_key=True)  # 显式主键，bigint类型
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name='items')
    product = models.ForeignKey(CleanProduct, on_delete=models.PROTECT)
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="下单价")
    count = models.IntegerField(default=1)



class CartItem(models.Model):
    """购物车模型"""
    id = models.BigAutoField(primary_key=True)  # 显式主键，bigint类型
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='cart_items')
    product = models.ForeignKey(CleanProduct, on_delete=models.PROTECT)
    count = models.PositiveIntegerField(default=1, verbose_name="购买数量")
    selected = models.BooleanField(default=True, verbose_name="是否勾选")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'shopping_cart'
        unique_together = ('user', 'product')
        verbose_name = '购物车'