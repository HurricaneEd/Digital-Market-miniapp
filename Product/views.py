from rest_framework import viewsets, status, permissions, filters
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.db.models import Q

from Product.models import CleanProduct, CleanReview, Category, Brand
from Product.serializer import ProductSerializer, AdminProductSerializer, CategorySerializer, BrandSerializer, ReviewSerializer
from utils.ai_utils import call_tongyi_model
from Orders.models import Order
from Orders.serializer import OrderSerializer

# 导入推荐算法
import Recomm.algorithms as recommend_algorithms


# --- 1. 商品相关 (使用 ViewSet 聚合所有逻辑) ---
class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ReadOnlyModelViewSet 自动提供 list (列表) 和 retrieve (详情) 功能
    """
    queryset = CleanProduct.objects.all()
    serializer_class = ProductSerializer
    lookup_field = 'prod_id'

    def get_queryset(self):
        queryset = CleanProduct.objects.all().order_by("-updated_at")

        # 搜索关键字
        query = self.request.query_params.get('search',None)
        if query:
            keywords = query.split()
            q_objects = Q()
            for word in keywords:
                # 搜索商品名称
                q_objects |= Q(name__icontains=word)
                # 搜索品牌 - 通过 brand_id 关联 Brand 表
                from Product.models import Brand
                brand_ids = Brand.objects.filter(name__icontains=word).values_list('id', flat=True)
                q_objects |= Q(brand_id__in=brand_ids)
            queryset = queryset.filter(q_objects).distinct()

        # 分类筛选 - 支持 code 或 name
        category = self.request.query_params.get('category', None)
        if category and category != '全部':
            from Product.models import Category
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
                queryset = queryset.order_by('-comment_count')

        return queryset

    @action(detail=True, methods=['get'], url_path='similar')
    def similar_products(self, request, prod_id=None):
        """
        获取相似商品 - 基于内容推荐的相似商品推荐
        GET /api/products/{prod_id}/similar/
        """
        # 获取目标商品
        product = self.get_object()

        # 获取top_n参数
        top_n = int(request.query_params.get('top_n', 8))

        # 基于分类、品牌、价格区间的商品相似度计算
        from Product.models import CleanProduct

        # 获取所有同分类的商品（排除自己）
        same_category = list(CleanProduct.objects.filter(
            category_id=product.category_id,
            is_active=True
        ).exclude(prod_id=product.prod_id)[:100])

        # 同品牌的（排除已加入的和重复的）
        same_brand = list(CleanProduct.objects.filter(
            brand_id=product.brand_id,
            is_active=True
        ).exclude(prod_id=product.prod_id).exclude(
            category_id=product.category_id
        )[:50])

        # 合并候选
        candidates = same_category + same_brand
        seen_ids = set()
        unique_candidates = []
        for p in candidates:
            if p.prod_id not in seen_ids:
                seen_ids.add(p.prod_id)
                unique_candidates.append(p)

        # 计算相似度分数（分类权重0.5，品牌0.3，价格0.2）
        def calc_similarity(p):
            score = 0
            if p.category_id == product.category_id:
                score += 0.5
            if p.brand_id == product.brand_id:
                score += 0.3
            if product.price > 0:
                price_diff = abs(float(p.price) - float(product.price)) / float(product.price)
                if price_diff <= 0.1:
                    score += 0.2 * (1 - price_diff / 0.1)
            return score

        scored = [(p, calc_similarity(p)) for p in unique_candidates]
        scored.sort(key=lambda x: x[1], reverse=True)

        similar_products = [p for p, s in scored[:top_n] if s > 0]

        # 序列化返回 - 前端期望直接返回数组
        serializer = self.get_serializer(similar_products, many=True)
        return Response(serializer.data)


# --- 2. 智能问答 (保持 APIView，因为它不对应特定模型增删改查) ---
class SmartRecommendView(APIView):
    permission_classes = [IsAuthenticated]  # 建议问答需要登录

    def post(self, request):
        user_prompt = request.data.get('prompt', '')
        products = CleanProduct.objects.order_by('-rate')[:10]
        context = "; ".join([f"{p.name}({p.price}元)" for p in products])

        answer = call_tongyi_model(user_prompt, context)
        return Response({'answer': answer})


# --- 3. 后台管理分页配置 ---
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
    queryset = CleanProduct.objects.all().order_by('-updated_at')
    serializer_class = AdminProductSerializer

    # 权限控制：必须是 is_staff=True 的管理员
    permission_classes = [permissions.IsAdminUser]

    # 分页配置
    pagination_class = AdminProductPagination
    lookup_field = 'prod_id'
    # 搜索与排序配置
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'brand__name', 'category__name', 'prod_id']  # 支持按名称、品牌、分类、ID搜索
    ordering_fields = ['price', 'stock', 'updated_at', 'rate']  # 支持按价格、库存、时间排序

    # --- 批量更新状态 (上架/下架) ---
    @action(detail=False, methods=['post'], url_path='batch-update')
    def batch_update(self, request):
        pids = request.data.get('pids', [])
        is_active = request.data.get('is_active')

        if not pids:
            return Response({'detail': '未选择任何商品'}, status=status.HTTP_400_BAD_REQUEST)

        # 批量执行更新，使用 prod_id 而不是 pid
        updated_count = CleanProduct.objects.filter(prod_id__in=pids).update(is_active=is_active)
        return Response({'detail': f'成功更新 {updated_count} 个商品', 'count': updated_count})

    # --- 批量删除 ---
    @action(detail=False, methods=['post'], url_path='batch-delete')
    def batch_delete(self, request):
        pids = request.data.get('pids', [])
        if not pids:
            return Response({'detail': '未选择任何商品'}, status=status.HTTP_400_BAD_REQUEST)

        # 先获取要删除的商品
        products = CleanProduct.objects.filter(prod_id__in=pids)
        # 删除每个商品关联的数据
        for p in products:
            p.reviews.all().delete()
            from Users.models import Favorite, UserAction
            Favorite.objects.filter(product_id=p.prod_id).delete()
            UserAction.objects.filter(product_id=p.prod_id).delete()
            from Orders.models import CartItem, OrderItem
            CartItem.objects.filter(product=p).delete()
            OrderItem.objects.filter(product=p).delete()

        # 再删除商品
        deleted_count, _ = products.delete()
        return Response({'detail': f'成功删除 {deleted_count} 个商品', 'count': deleted_count})

    def perform_create(self, serializer):
        # 可以在这里增加额外的逻辑，比如记录是谁创建了商品
        serializer.save()

    def perform_destroy(self, instance):
        # 先删除关联的收藏和评论
        instance.reviews.all().delete()
        from Users.models import Favorite
        Favorite.objects.filter(product_id=instance.prod_id).delete()
        # 删除关联的用户行为记录
        from Users.models import UserAction
        UserAction.objects.filter(product_id=instance.prod_id).delete()
        # 删除关联的订单项
        instance.orderitem_set.all().delete()
        # 删除关联的购物车项
        instance.cartitem_set.all().delete()
        # 再删除商品
        instance.delete()


# --- 4. 分类管理 ---
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


# --- 5. 品牌管理 ---
class BrandViewSet(viewsets.ModelViewSet):
    """品牌管理接口"""
    queryset = Brand.objects.all().order_by('name')
    serializer_class = BrandSerializer
    lookup_field = 'id'
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name']


# --- 6. 评论管理 ---
class ReviewViewSet(viewsets.ModelViewSet):
    """评论管理接口"""
    queryset = CleanReview.objects.all()#.order_by('-formatted_date')
    serializer_class = ReviewSerializer
    lookup_field = 'id'
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['username', 'content', 'product__name']
    ordering_fields = ['rating', 'date']

    def get_queryset(self):
        queryset = CleanReview.objects.all()#.order_by('-formatted_date')

        # 按商品筛选 - 支持 prod_id
        product_id = self.request.query_params.get('product_id', None)
        if product_id:
            # prod_id 是字符串类型，直接用于过滤外键
            queryset = queryset.filter(product_id=product_id)

        # 按评分筛选
        rating = self.request.query_params.get('rating', None)
        if rating:
            queryset = queryset.filter(rating=int(rating))

        return queryset

    def perform_create(self, serializer):
        # 自动关联当前登录用户
        user = self.request.user if self.request.user.is_authenticated else None

        # 处理日期字段
        date_str = serializer.validated_data.get('date', None)
        if date_str:
            try:
                from datetime import datetime
                # 解析 ISO 格式日期
                date_str = date_str.replace('Z', '+00:00')
                parsed_date = datetime.fromisoformat(date_str)
                serializer.save(user=user, date=parsed_date)
            except:
                from datetime import datetime
                serializer.save(user=user, date=datetime.now())
        else:
            from datetime import datetime
            serializer.save(user=user, date=datetime.now())
