from django.conf import settings
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models

from Product.models import Product


phone_validator = RegexValidator(
    regex=r'^1[3-9]\d{9}$',
    message='手机号格式不正确',
)


class Address(models.Model):
    """用户可维护和复用的收货地址。"""

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='addresses')
    receiver = models.CharField(max_length=50, verbose_name='收货人')
    phone = models.CharField(max_length=11, validators=[phone_validator], verbose_name='手机号')
    detail = models.CharField(max_length=255, verbose_name='详细地址')
    is_default = models.BooleanField(default=False, verbose_name='是否默认')

    class Meta:
        db_table = 'customer_addresses'
        verbose_name = '收货地址'
        verbose_name_plural = verbose_name
        indexes = [models.Index(fields=['user', '-id'])]


class Order(models.Model):
    """订单主表；收货信息存放在独立的订单地址快照中。"""

    id = models.BigAutoField(primary_key=True)
    class Status(models.TextChoices):
        UNPAID = 'unpaid', '待支付'
        PAID = 'paid', '已支付'
        SHIPPED = 'shipped', '已发货'
        COMPLETED = 'completed', '已完成'
        CANCELLED = 'cancelled', '已取消'

    class PaymentMethod(models.TextChoices):
        WECHAT = 'wechat', '微信支付'
        ALIPAY = 'alipay', '支付宝'

    order_sn = models.CharField(max_length=50, unique=True, verbose_name='订单号')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='orders')
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name='订单总价',
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UNPAID)
    payment_method = models.CharField(max_length=20, choices=PaymentMethod.choices, null=True, blank=True, verbose_name='支付方式')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'orders'
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(total_price__gte=0), name='ck_order_total_nonnegative'),
            models.CheckConstraint(
                condition=models.Q(status__in=['unpaid', 'paid', 'shipped', 'completed', 'cancelled']),
                name='ck_order_status_valid',
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(payment_method__isnull=True)
                    | models.Q(payment_method__in=['wechat', 'alipay'])
                ),
                name='ck_order_payment_method_valid',
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(status='unpaid', payment_method__isnull=True)
                    | models.Q(status='cancelled')
                    | models.Q(
                        status__in=['paid', 'shipped', 'completed'],
                        payment_method__isnull=False,
                    )
                ),
                name='ck_order_status_payment_consistent',
            ),
        ]


class ShippingAddressSnapshot(models.Model):
    """订单创建时的收货地址快照，避免用户修改地址影响历史订单。"""

    id = models.BigAutoField(primary_key=True)
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='shipping_address')
    receiver = models.CharField(max_length=50, verbose_name='收货人')
    phone = models.CharField(max_length=11, validators=[phone_validator], verbose_name='手机号')
    detail = models.CharField(max_length=255, verbose_name='详细地址')

    class Meta:
        db_table = 'order_shipping_address_snapshots'
        verbose_name = '订单收货地址快照'
        verbose_name_plural = verbose_name


class OrderItem(models.Model):
    """订单明细；price/count 是下单时的价格和数量事实。"""

    id = models.BigAutoField(primary_key=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, related_name='order_items')
    product_code = models.CharField(max_length=50, verbose_name='商品编码快照')
    product_name = models.CharField(max_length=200, verbose_name='商品名称快照')
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], verbose_name='下单价')
    count = models.PositiveIntegerField(default=1, verbose_name='购买数量')

    class Meta:
        db_table = 'order_items'
        constraints = [
            models.CheckConstraint(condition=models.Q(count__gt=0), name='ck_order_item_count_positive'),
            models.CheckConstraint(condition=models.Q(price__gte=0), name='ck_order_item_price_nonnegative'),
        ]


class CartItem(models.Model):
    """购物车中用户与商品的唯一关系。"""

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cart_items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='cart_items')
    count = models.PositiveIntegerField(default=1, verbose_name='购买数量')
    selected = models.BooleanField(default=True, verbose_name='是否勾选')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'shopping_cart_items'
        verbose_name = '购物车'
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(fields=['user', 'product'], name='uq_cart_user_product'),
            models.CheckConstraint(condition=models.Q(count__gt=0), name='ck_cart_item_count_positive'),
        ]
        indexes = [models.Index(fields=['user', '-updated_at'])]
