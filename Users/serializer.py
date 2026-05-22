from rest_framework import serializers

from .models import User, UserAction, Favorite
from Product.models import Category, Brand


class UserSerializer(serializers.ModelSerializer):
    """用户信息"""
    class Meta:
        model = User
        fields = [
            'id', 'username', 'avatar', 'phone', 'nickname', 'email',
            'is_staff','is_superuser', 'date_joined'
        ]
        read_only_fields = ['is_staff','is_superuser', 'date_joined']


# 辅助函数：获取产品分类/品牌名称
def get_product_category_name(product):
    if product and product.category_id:
        cat = Category.objects.filter(id=product.category_id).first()
        return cat.name if cat else None
    return None


def get_product_brand_name(product):
    if product and product.brand_id:
        brand = Brand.objects.filter(id=product.brand_id).first()
        return brand.name if brand else None
    return None


class UserActionSerializer(serializers.ModelSerializer):
    """用户行为记录序列化器"""
    product_name = serializers.SerializerMethodField()
    product_price = serializers.SerializerMethodField()
    product_image = serializers.SerializerMethodField()
    product_category = serializers.SerializerMethodField()
    product_rate = serializers.SerializerMethodField()
    product_sales = serializers.SerializerMethodField()

    def get_product_name(self, obj):
        return obj.product.name if obj.product else None

    def get_product_price(self, obj):
        return str(obj.product.price) if obj.product else None

    def get_product_image(self, obj):
        return obj.product.img_url if obj.product else None

    def get_product_category(self, obj):
        return get_product_category_name(obj.product)

    def get_product_rate(self, obj):
        return obj.product.rate if obj.product else None

    def get_product_sales(self, obj):
        return obj.product.comment_count if obj.product else None

    class Meta:
        model = UserAction
        fields = ['id', 'product', 'action_type', 'count', 'score', 'created_at',
                  'product_name', 'product_price', 'product_image',
                  'product_category', 'product_rate', 'product_sales']
        read_only_fields = ['user_id', 'score', 'created_at']


class FavoriteSerializer(serializers.ModelSerializer):
    """用户收藏序列化器"""
    product_name = serializers.SerializerMethodField()
    product_price = serializers.SerializerMethodField()
    product_image = serializers.SerializerMethodField()
    product_category = serializers.SerializerMethodField()
    product_rate = serializers.SerializerMethodField()
    product_sales = serializers.SerializerMethodField()

    def get_product_name(self, obj):
        return obj.product.name if obj.product else None

    def get_product_price(self, obj):
        return str(obj.product.price) if obj.product else None

    def get_product_image(self, obj):
        return obj.product.img_url if obj.product else None

    def get_product_category(self, obj):
        return get_product_category_name(obj.product)

    def get_product_rate(self, obj):
        return obj.product.rate if obj.product else None

    def get_product_sales(self, obj):
        return obj.product.comment_count if obj.product else None

    class Meta:
        model = Favorite
        fields = ['id', 'product', 'created_at',
                  'product_name', 'product_price', 'product_image',
                  'product_category', 'product_rate', 'product_sales']
        read_only_fields = ['user', 'created_at']


class AdminUserSerializer(serializers.ModelSerializer):
    """管理员用户管理序列化器"""
    class Meta:
        model = User
        fields = ['id', 'username', 'nickname', 'email', 'phone', 'avatar', 'is_staff', 'is_superuser', 'is_active', 'date_joined', 'last_login']
        read_only_fields = ['is_superuser', 'date_joined', 'last_login']
