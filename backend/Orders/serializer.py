from rest_framework import serializers

from Orders.models import Address, OrderItem, Order, CartItem
from Product.models import Product


class AddressSerializer(serializers.ModelSerializer):
    receiver = serializers.CharField(max_length=50)
    phone = serializers.RegexField(
        regex=r'^1[3-9]\d{9}$',
        error_messages={'invalid': '手机号格式不正确'},
    )
    detail = serializers.CharField(max_length=255)

    class Meta:
        model = Address
        fields = ['id', 'receiver', 'phone', 'detail', 'is_default', 'user']
        read_only_fields = ['user']

class OrderItemSerializer(serializers.ModelSerializer):
    """订单详情：每个订单里的单件商品信息"""
    product_img = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'product_img', 'price', 'count']

    def get_product_img(self, obj):
        """获取商品图片URL，处理相对路径"""
        if not obj.product:
            return None
        img_url = obj.product.img_url
        if not img_url:
            return None
        # 如果已经是完整URL，直接返回
        if img_url.startswith('http://') or img_url.startswith('https://'):
            return img_url
        # 相对路径，添加域名
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(img_url)
        return img_url


class OrderSerializer(serializers.ModelSerializer):
    """订单主表：包含该订单下所有的商品"""
    items = OrderItemSerializer(many=True, read_only=True)
    address_info = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = '__all__'
        read_only_fields = [
            'order_sn', 'user', 'total_price', 'status', 'payment_method',
            'created_at', 'updated_at',
        ]

    def get_username(self, obj):
        """获取用户名"""
        return obj.user.username if obj.user else None

    def get_address_info(self, obj):
        # 兼容空地址情况
        if not hasattr(obj, 'shipping_address'):
            return None
        address = obj.shipping_address
        return f"{address.receiver} {address.phone} {address.detail}"

class CreateOrderSerializer(serializers.Serializer):
    """创建订单的参数验证"""
    address_id = serializers.IntegerField(min_value=1, help_text="收货地址ID")
    cart_item_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        help_text="购物车项ID列表",
        allow_empty=False,
        required=False,
    )
    product_id = serializers.CharField(
        max_length=50,
        help_text="立即购买的商品编号",
        required=False,
    )
    count = serializers.IntegerField(
        min_value=1,
        help_text="立即购买数量",
        required=False,
    )

    def validate(self, data):
        cart_item_ids = data.get('cart_item_ids')
        product_id = data.get('product_id')
        if bool(cart_item_ids) == bool(product_id):
            raise serializers.ValidationError(
                '购物车结算和立即购买必须且只能选择一种',
            )
        if cart_item_ids and len(cart_item_ids) != len(set(cart_item_ids)):
            raise serializers.ValidationError('购物车商品不能重复')
        if product_id:
            data.setdefault('count', 1)
        elif 'count' in data:
            raise serializers.ValidationError({'count': '购物车结算不需要购买数量'})
        return data


class PaymentSerializer(serializers.Serializer):
    payment_method = serializers.ChoiceField(
        choices=Order.PaymentMethod.choices,
        default=Order.PaymentMethod.WECHAT,
    )


class OrderBatchSerializer(serializers.Serializer):
    order_nos = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=False,
    )

class AdminOrderUpdateSerializer(serializers.ModelSerializer):
    """管理员修改订单：主要用于修改状态"""
    class Meta:
        model = Order
        fields = ['status']


class CartProductSerializer(serializers.ModelSerializer):
    """购物车中商品信息的简化版"""

    class Meta:
        model = Product
        fields = ['prod_id', 'name', 'price', 'img_url', 'stock', 'is_active']


class CartSerializer(serializers.ModelSerializer):
    """购物车序列化器"""
    product = CartProductSerializer(read_only=True)
    # 修改为支持字符串类型的 prod_id
    product_id = serializers.CharField(write_only=True, required=False)
    count = serializers.IntegerField(min_value=1, default=1)

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_id', 'count', 'selected', 'created_at', 'updated_at']
        read_only_fields = ['user', 'created_at', 'updated_at']

    def validate(self, attrs):
        # 获取 product_id (可能是字符串类型的 prod_id)
        product_id = attrs.get('product_id')
        if self.instance is None and not product_id:
            raise serializers.ValidationError({'product_id': '请选择商品'})
        if product_id:
            try:
                # 尝试通过 prod_id 查找商品
                product = Product.objects.get(prod_id=product_id)
                attrs['product'] = product
                # 移除 product_id，避免传递给 model
                attrs.pop('product_id')
            except Product.DoesNotExist:
                # 如果找不到，尝试通过整数 id 查找
                try:
                    product = Product.objects.get(pk=int(product_id))
                    attrs['product'] = product
                    attrs.pop('product_id')
                except (Product.DoesNotExist, ValueError):
                    raise serializers.ValidationError({'product_id': '商品不存在'})
        product = attrs.get('product') or (
            self.instance.product if self.instance is not None else None
        )
        validates_purchase = self.instance is None or product_id or 'count' in attrs
        if product and validates_purchase:
            if not product.is_active:
                raise serializers.ValidationError({'product_id': '商品已下架'})
            count = attrs.get('count', self.instance.count if self.instance else 1)
            if count > product.stock:
                raise serializers.ValidationError({
                    'count': f'购买数量不能超过库存（当前库存 {product.stock}）',
                })
        return attrs
