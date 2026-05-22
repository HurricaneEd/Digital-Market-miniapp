from rest_framework import serializers

from Product.models import CleanProduct, CleanReview, Category, Brand


class ProductSerializer(serializers.ModelSerializer):
    """商品序列化器：将 brand_id/category_id 转换为名称"""
    brand_name = serializers.SerializerMethodField()
    category_name = serializers.SerializerMethodField()

    def get_brand_name(self, obj):
        if obj.brand_id:
            brand = Brand.objects.filter(id=obj.brand_id).first()
            return brand.name if brand else None
        return None

    def get_category_name(self, obj):
        if obj.category_id:
            category = Category.objects.filter(id=obj.category_id).first()
            return category.name if category else None
        return None

    class Meta:
        model = CleanProduct
        fields = '__all__'


class AdminProductSerializer(serializers.ModelSerializer):
    """管理员编辑商品"""
    brand_name = serializers.SerializerMethodField()
    category_name = serializers.SerializerMethodField()
    # 添加 category 字段用于输出（映射自 category_id）
    category = serializers.SerializerMethodField()
    # 将 img_url 改为 CharField 避免 URL 验证问题
    img_url = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    # JSONField 也需要处理
    sub_images = serializers.JSONField(required=False, allow_null=True)
    all_params = serializers.JSONField(required=False, allow_null=True)
    # 时间和计算字段设置为只读
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    rate = serializers.FloatField(read_only=True)
    comment_count = serializers.IntegerField(read_only=True)
    sales = serializers.IntegerField(read_only=True)

    def get_brand_name(self, obj):
        if obj.brand_id:
            brand = Brand.objects.filter(id=obj.brand_id).first()
            return brand.name if brand else None
        return None

    def get_category_name(self, obj):
        if obj.category_id:
            category = Category.objects.filter(id=obj.category_id).first()
            return category.name if category else None
        return None

    def get_category(self, obj):
        return obj.category_id

    def to_internal_value(self, data):
        # 需要将前端传入的 category 映射为 category_id
        # 同时处理 brand 字段映射为 brand_id
        # 同时处理 prod_id 字段
        ret = {}
        for key, value in data.items():
            if key == 'category':
                ret['category_id'] = value
            elif key == 'brand':
                ret['brand_id'] = value
            elif key == 'prod_id':
                ret['prod_id'] = value
            else:
                ret[key] = value
        return ret

    def create(self, validated_data):
        from django.utils import timezone
        import random
        import string
        # 为必填字段设置默认值
        if 'created_at' not in validated_data or validated_data.get('created_at') is None:
            validated_data['created_at'] = timezone.now()
        if 'updated_at' not in validated_data or validated_data.get('updated_at') is None:
            validated_data['updated_at'] = timezone.now()
        # 确保 brand_id 有默认值
        if 'brand_id' not in validated_data or validated_data.get('brand_id') is None:
            validated_data['brand_id'] = 0
        # 确保 category_id 有默认值
        if 'category_id' not in validated_data or validated_data.get('category_id') is None:
            validated_data['category_id'] = 0
        # 自动生成 prod_id
        if 'prod_id' not in validated_data or not validated_data.get('prod_id'):
            validated_data['prod_id'] = 'P' + ''.join(random.choices(string.digits, k=10))
        # 移除只读字段（以防万一）
        validated_data.pop('rate', None)
        validated_data.pop('comment_count', None)
        validated_data.pop('sales', None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        from django.utils import timezone
        # 为 updated_at 设置默认值
        validated_data['updated_at'] = timezone.now()
        # 移除只读字段
        validated_data.pop('created_at', None)
        validated_data.pop('rate', None)
        validated_data.pop('comment_count', None)
        validated_data.pop('sales', None)
        return super().update(instance, validated_data)

    class Meta:
        model = CleanProduct
        fields = '__all__'
        extra_kwargs = {
            'created_at': {'read_only': True},
            'updated_at': {'read_only': True},
            'rate': {'read_only': True},
            'comment_count': {'read_only': True},
            'sales': {'read_only': True},
        }


class CategorySerializer(serializers.ModelSerializer):
    """分类序列化器"""
    class Meta:
        model = Category
        fields = ['id', 'code', 'name']


class BrandSerializer(serializers.ModelSerializer):
    """品牌序列化器"""
    class Meta:
        model = Brand
        fields = ['id', 'name', 'logo']


class ReviewSerializer(serializers.ModelSerializer):
    """评论序列化器"""
    product_name = serializers.SerializerMethodField()

    def get_product_name(self, obj):
        return obj.product.name if obj.product else None

    class Meta:
        model = CleanReview
        fields = '__all__'