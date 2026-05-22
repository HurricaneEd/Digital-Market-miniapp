from rest_framework import serializers

from Orders.models import Address, OrderItem, Order, CartItem
from Product.models import CleanProduct


class AddressSerializer(serializers.ModelSerializer):
    receiver = serializers.CharField(max_length=50)
    phone = serializers.CharField(max_length=11)
    detail = serializers.CharField(max_length=255)

    class Meta:
        model = Address
        fields = ['id', 'receiver', 'phone', 'detail', 'is_default', 'user']
        read_only_fields = ['user']

class OrderItemSerializer(serializers.ModelSerializer):
    """订单详情：每个订单里的单件商品信息"""
    product_name = serializers.CharField(source='product.name')
    product_img = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'product_img', 'price', 'count']

    def get_product_img(self, obj):
        """获取商品图片URL，处理相对路径"""
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

    def get_username(self, obj):
        """获取用户名"""
        return obj.user.username if obj.user else None

    def get_address_info(self, obj):
        # 兼容空地址情况
        if not obj.address:
            return None
        return f"{obj.address.receiver} {obj.address.phone} {obj.address.detail}"

class CreateOrderSerializer(serializers.Serializer):
    """创建订单的参数验证"""
    address_id = serializers.IntegerField(help_text="收货地址ID")
    cart_item_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="购物车项ID列表",
        required=False
    )
    # 如果是直接购买（不通过购物车），可以使用以下字段
    direct_product_id = serializers.CharField(required=False, help_text="直接购买的商品ID")
    direct_count = serializers.IntegerField(required=False, default=1, help_text="直接购买的数量")

    def validate(self, data):
        if not data.get('cart_item_ids') and not data.get('direct_product_id'):
            raise serializers.ValidationError("必须提供购物车项或直接购买商品信息")
        return data

class AdminOrderUpdateSerializer(serializers.ModelSerializer):
    """管理员修改订单：主要用于修改状态"""
    class Meta:
        model = Order
        fields = ['status']


class CartProductSerializer(serializers.ModelSerializer):
    """购物车中商品信息的简化版"""
    class Meta:
        model = CleanProduct
        fields = ['prod_id', 'name', 'price', 'img_url']


class CartSerializer(serializers.ModelSerializer):
    """购物车序列化器"""
    product = CartProductSerializer(read_only=True)
    # 修改为支持字符串类型的 prod_id
    product_id = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_id', 'count', 'selected', 'created_at', 'updated_at']
        read_only_fields = ['user', 'created_at', 'updated_at']

    def validate(self, attrs):
        # 获取 product_id (可能是字符串类型的 prod_id)
        product_id = attrs.get('product_id')
        if product_id:
            try:
                # 尝试通过 prod_id 查找商品
                product = CleanProduct.objects.get(prod_id=product_id)
                attrs['product'] = product
                # 移除 product_id，避免传递给 model
                attrs.pop('product_id')
            except CleanProduct.DoesNotExist:
                # 如果找不到，尝试通过整数 id 查找
                try:
                    product = CleanProduct.objects.get(pk=int(product_id))
                    attrs['product'] = product
                    attrs.pop('product_id')
                except (CleanProduct.DoesNotExist, ValueError):
                    raise serializers.ValidationError({'product_id': '商品不存在'})
        return attrs