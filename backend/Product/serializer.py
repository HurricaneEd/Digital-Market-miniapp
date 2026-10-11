import random
import string
from rest_framework import serializers

from .models import Brand, Category, Product, Review


class ProductSerializer(serializers.ModelSerializer):
    """商品读模型；固定核心字段与 all_params JSON 直接来自商品表。"""

    brand_name = serializers.CharField(source='brand.name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    rate = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'prod_id', 'brand', 'brand_name', 'category', 'category_name',
            'name', 'origin', 'price', 'stock', 'is_active', 'created_at', 'updated_at',
            'img_url', 'all_params', 'rate', 'comment_count',
        ]

    def get_rate(self, obj):
        ratings = [review.rating for review in obj.reviews.all() if review.rating is not None]
        return float(round(sum(ratings) / len(ratings), 2)) if ratings else 0

    def get_comment_count(self, obj):
        return obj.reviews.count()

    def validate_all_params(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError('all_params 必须是 JSON 对象。')
        if any(not isinstance(params, dict) for params in value.values()):
            raise serializers.ValidationError('all_params 的每个参数分组都必须是 JSON 对象。')
        return value


class AdminProductSerializer(ProductSerializer):
    """管理员商品写模型。"""

    class Meta(ProductSerializer.Meta):
        extra_kwargs = {
            'prod_id': {'required': False},
        }

    def create(self, validated_data):
        validated_data['prod_id'] = validated_data.get('prod_id') or self._new_product_id()
        return super().create(validated_data)

    @staticmethod
    def _new_product_id():
        return 'P' + ''.join(random.choices(string.digits, k=10))


class ProductBatchUpdateSerializer(serializers.Serializer):
    pids = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=False,
    )
    is_active = serializers.BooleanField()


class ProductBatchDeleteSerializer(serializers.Serializer):
    pids = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=False,
    )


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'parent', 'code', 'name']

    def validate_parent(self, parent):
        category_id = getattr(self.instance, 'pk', None)
        candidate = parent
        visited = set()
        while parent is not None:
            if parent.pk == category_id or parent.pk in visited:
                raise serializers.ValidationError('分类层级不能形成循环')
            visited.add(parent.pk)
            parent = parent.parent
        return candidate


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ['id', 'name']


class ReviewSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    rating = serializers.DecimalField(
        max_digits=2,
        decimal_places=1,
        allow_null=True,
        required=False,
        coerce_to_string=False,
    )

    class Meta:
        model = Review
        fields = [
            'id', 'product', 'product_name', 'user', 'author_name', 'content',
            'rating', 'reviewed_at',
        ]
        read_only_fields = ['user']
