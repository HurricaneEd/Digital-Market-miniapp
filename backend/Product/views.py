from rest_framework import viewsets, status, permissions, filters
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from django.db import transaction
from django.db.models import Count, Q

from Product.models import Product, Review, Category, Brand
from Product.serializer import (
    AdminProductSerializer,
    BrandSerializer,
    CategorySerializer,
    ProductBatchDeleteSerializer,
    ProductBatchUpdateSerializer,
    ProductSerializer,
    ReviewSerializer,
)


# --- 1. 商品相关 (使用 ViewSet 聚合所有逻辑) ---
class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ReadOnlyModelViewSet 自动提供 list (列表) 和 retrieve (详情) 功能
    """
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    lookup_field = 'prod_id'

    def get_queryset(self):
        queryset = Product.objects.filter(is_active=True).select_related('brand', 'category').prefetch_related('reviews').order_by("-updated_at")

        # 搜索关键字
        query = self.request.query_params.get('search',None)
        if query:
            keywords = query.split()
            q_objects = Q()
            for word in keywords:
                # 搜索商品名称
                q_objects |= Q(name__icontains=word)
                # 搜索品牌 - 通过 brand_id 关联 Brand 表
                brand_ids = Brand.objects.filter(name__icontains=word).values_list('id', flat=True)
                q_objects |= Q(brand__id__in=brand_ids)
            queryset = queryset.filter(q_objects).distinct()

        # 分类筛选 - 支持 code 或 name
        category = self.request.query_params.get('category', None)
        if category and category != '全部':
            category_obj = Category.objects.filter(
                Q(code=category) | Q(name=category)
            ).first()
            if category_obj:
                queryset = queryset.filter(category_id=category_obj.id)

        # 价格筛选
        min_price = self.request.query_params.get('min_price', None)
        max_price = self.request.query_params.get('max_price', None)
        if min_price:
            queryset = queryset.filter(price__gte=float(min_price))
        if max_price:
            queryset = queryset.filter(price__lte=float(max_price))

        # 排序
        ordering = self.request.query_params.get('ordering', None)
        if ordering:
            if ordering == 'price_asc':
                queryset = queryset.order_by('price')
            elif ordering == 'price_desc':
                queryset = queryset.order_by('-price')
            elif ordering == 'newest':
                queryset = queryset.order_by('-updated_at')
            elif ordering == 'sales':
                queryset = queryset.annotate(review_total=Count('reviews')).order_by('-review_total')

        return queryset

# --- 2. 后台管理分页配置 ---
class AdminProductPagination(PageNumberPagination):
    """后台专用分页：每页显示 10 条，方便管理员处理"""
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class AdminProductViewSet(viewsets.ModelViewSet):
    """
    管理员商品管理接口
    支持：获取列表、查看详情、新增、全量更新、局部修改、删除
    """
    queryset = Product.objects.select_related('brand', 'category').prefetch_related('reviews').order_by('-updated_at')
    serializer_class = AdminProductSerializer

    # 权限控制：必须是 is_staff=True 的管理员
    permission_classes = [permissions.IsAdminUser]

    # 分页配置
    pagination_class = AdminProductPagination
    lookup_field = 'prod_id'
    # 搜索与排序配置
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'brand__name', 'category__name', 'prod_id']  # 支持按名称、品牌、分类、ID搜索
    ordering_fields = ['price', 'stock', 'updated_at']  # 支持按价格、库存、时间排序

    def get_serializer_class(self):
        action = getattr(self, 'action', None)
        serializers_by_action = {
            'batch_update': ProductBatchUpdateSerializer,
            'batch_delete': ProductBatchDeleteSerializer,
        }
        return serializers_by_action.get(action, self.serializer_class)

    # --- 批量更新状态 (上架/下架) ---
    @action(detail=False, methods=['post'], url_path='batch-update')
    def batch_update(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pids = serializer.validated_data['pids']
        is_active = serializer.validated_data['is_active']

        # 批量执行更新，使用 prod_id 而不是 pid
        updated_count = Product.objects.filter(prod_id__in=pids).update(is_active=is_active)
        return Response({'detail': f'成功更新 {updated_count} 个商品', 'count': updated_count})

    # --- 批量删除 ---
    @action(detail=False, methods=['post'], url_path='batch-delete')
    @transaction.atomic
    def batch_delete(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pids = serializer.validated_data['pids']

        # 先获取要删除的商品
        products = Product.objects.filter(prod_id__in=pids)
        # 购物车使用 PROTECT，需要先清理；订单项会保留快照并将商品置空。
        for p in products:
            from Orders.models import CartItem
            CartItem.objects.filter(product=p).delete()

        # 再删除商品
        deleted_count, _ = products.delete()
        return Response({'detail': f'成功删除 {deleted_count} 个商品', 'count': deleted_count})

    def perform_create(self, serializer):
        # 可以在这里增加额外的逻辑，比如记录是谁创建了商品
        serializer.save()

    @transaction.atomic
    def perform_destroy(self, instance):
        # 保留历史订单项；删除商品时其 product 外键会自动 SET_NULL。
        instance.cart_items.all().delete()
        instance.delete()


# --- 3. 分类管理 ---
class CategoryViewSet(viewsets.ModelViewSet):
    """分类管理接口"""
    queryset = Category.objects.all().order_by('id')
    serializer_class = CategorySerializer
    lookup_field = 'id'
    # 允许任何人访问
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'code']
    ordering_fields = ['id', 'name']


# --- 4. 品牌管理 ---
class BrandViewSet(viewsets.ModelViewSet):
    """品牌管理接口"""
    queryset = Brand.objects.all().order_by('name')
    serializer_class = BrandSerializer
    lookup_field = 'id'
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name']


# --- 5. 评论管理 ---
class ReviewViewSet(viewsets.ModelViewSet):
    """评论管理接口"""
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    lookup_field = 'id'
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['author_name', 'content', 'product__name']
    ordering_fields = ['rating', 'reviewed_at']

    def get_queryset(self):
        queryset = Review.objects.all()

        # 按商品筛选 - 支持 prod_id
        product_id = self.request.query_params.get('product_id', None)
        if product_id:
            # prod_id 是字符串类型，直接用于过滤外键
            queryset = queryset.filter(product__prod_id=product_id)

        # 按评分筛选
        rating = self.request.query_params.get('rating', None)
        if rating:
            queryset = queryset.filter(rating=int(rating))

        return queryset

    def perform_create(self, serializer):
        # 自动关联当前登录用户
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(user=user)
