# 推荐算法相关视图
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model

from Product.models import CleanProduct, Category
from Users.models import User
from .algorithms import (
    get_hot_items,
    user_cf_recommend,
    item_cf_recommend,
    cb_recommend,
    hybrid_recommend,
    calculate_item_heat
)
from Product.serializer import ProductSerializer

User = get_user_model()


# 辅助函数：转换商品数据格式
def transform_product(product, score=None, source=None):
    """转换为前端需要的格式"""
    data = ProductSerializer(product).data
    data['id'] = data['prod_id']
    if score is not None:
        data['score'] = round(score, 2)
    if source:
        data['source'] = source
    return data


class UnifiedRecommendView(APIView):
    """
    统一推荐接口 - 支持多种算法切换
    GET /api/recommend/?type=hot|cf|cb|hybrid|new&user_id=xxx&top_n=20
    """
    def get(self, request):
        # 获取用户ID（从认证或参数）
        user_id = request.query_params.get('user_id')
        if not user_id:
            # 尝试从认证用户获取
            if request.user.is_authenticated:
                user_id = request.user.id
            else:
                # 未登录用户使用热度推荐
                user_id = None

        # 算法类型
        algo_type = request.query_params.get('type', 'hybrid')
        top_n = int(request.query_params.get('top_n', 20))

        # 根据类型调用不同算法
        result = []
        source = ''

        if algo_type == 'hot':
            # 热度推荐
            category = request.query_params.get('category')
            items = get_hot_items(top_n=top_n, category_code=category)
            result = [transform_product(p, s, 'hot') for p, s in items]
            source = 'hot'

        elif algo_type == 'user_cf':
            # User-CF 协同过滤
            if not user_id:
                return Response({'code': 401, 'msg': '需要登录', 'data': []})
            items = user_cf_recommend(user_id=user_id, top_n=top_n)
            result = [transform_product(p, s, 'user_cf') for p, s in items]
            source = 'collaborative_filtering'

        elif algo_type == 'item_cf':
            # Item-CF 协同过滤
            if not user_id:
                return Response({'code': 401, 'msg': '需要登录', 'data': []})
            items = item_cf_recommend(user_id=user_id, top_n=top_n)
            result = [transform_product(p, s, 'item_cf') for p, s in items]
            source = 'item_based'

        elif algo_type == 'cb':
            # 内容推荐
            if not user_id:
                return Response({'code': 401, 'msg': '需要登录', 'data': []})
            items = cb_recommend(user_id=user_id, top_n=top_n)
            result = [transform_product(p, s, 'cb') for p, s in items]
            source = 'content_based'

        else:
            # 混合推荐（默认）
            if not user_id:
                # 新用户：热度推荐
                items = get_hot_items(top_n=top_n)
            else:
                items = hybrid_recommend(user_id=user_id, top_n=top_n)
            result = [transform_product(p, s, 'hybrid') for p, s in items]
            source = 'hybrid'

        return Response({
            'code': 200,
            'msg': '获取成功',
            'source': source,
            'data': result
        })


class HeatRecommendationView(APIView):
    """
    热度推荐接口
    GET /api/recommend/hot/?category=xxx&top_n=20
    """
    def get(self, request):
        category_code = request.query_params.get('category')
        top_n = int(request.query_params.get('top_n', 20))

        items = get_hot_items(top_n=top_n, category_code=category_code)

        result = []
        for product, heat_score in items:
            data = ProductSerializer(product).data
            data['heat_score'] = heat_score
            result.append(data)

        return Response({
            'code': 200,
            'msg': '热度推荐获取成功',
            'data': result
        })


class CollaborativeFilteringView(APIView):
    """
    协同过滤推荐接口
    GET /api/recommend/cf/?user_id=xxx&top_n=10
    """
    def get(self, request):
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response({
                'code': 400,
                'msg': '缺少user_id参数'
            }, status=status.HTTP_400_BAD_REQUEST)

        top_n = int(request.query_params.get('top_n', 10))

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({
                'code': 404,
                'msg': '用户不存在'
            }, status=status.HTTP_404_NOT_FOUND)

        items = user_cf_recommend(user_id=user_id, top_n=top_n)

        result = []
        for product, score in items:
            data = ProductSerializer(product).data
            data['recommend_score'] = score
            result.append(data)

        return Response({
            'code': 200,
            'msg': '协同过滤推荐获取成功',
            'data': result
        })


class ContentBasedView(APIView):
    """
    内容推荐接口
    GET /api/recommend/cb/?user_id=xxx&top_n=10
    """
    def get(self, request):
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response({
                'code': 400,
                'msg': '缺少user_id参数'
            }, status=status.HTTP_400_BAD_REQUEST)

        top_n = int(request.query_params.get('top_n', 10))

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({
                'code': 404,
                'msg': '用户不存在'
            }, status=status.HTTP_404_NOT_FOUND)

        items = cb_recommend(user_id=user_id, top_n=top_n)

        result = []
        for product, score in items:
            data = ProductSerializer(product).data
            data['content_score'] = score
            result.append(data)

        return Response({
            'code': 200,
            'msg': '内容推荐获取成功',
            'data': result
        })


class HybridRecommendationView(APIView):
    """
    混合推荐接口
    GET /api/recommend/hybrid/?user_id=xxx&top_n=10&weights=0.3,0.4,0.3
    """
    def get(self, request):
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response({
                'code': 400,
                'msg': '缺少user_id参数'
            }, status=status.HTTP_400_BAD_REQUEST)

        top_n = int(request.query_params.get('top_n', 10))

        # 解析权重参数 heats,cf,cb
        weights_str = request.query_params.get('weights', '0.3,0.4,0.3')
        try:
            w_heat, w_cf, w_cb = map(float, weights_str.split(','))
            weights = {'heat': w_heat, 'cf': w_cf, 'cb': w_cb}
        except:
            weights = {'heat': 0.3, 'cf': 0.4, 'cb': 0.3}

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({
                'code': 404,
                'msg': '用户不存在'
            }, status=status.HTTP_404_NOT_FOUND)

        items = hybrid_recommend(user_id=user_id, top_n=top_n, weights=weights)

        result = []
        for product, score in items:
            data = ProductSerializer(product).data
            data['hybrid_score'] = score
            result.append(data)

        return Response({
            'code': 200,
            'msg': '混合推荐获取成功',
            'data': result
        })


class ProductHeatDetailView(APIView):
    """
    获取单个商品的热度详情
    GET /api/recommend/heat/detail/?product_id=xxx
    """
    def get(self, request):
        product_id = request.query_params.get('product_id')
        if not product_id:
            return Response({
                'code': 400,
                'msg': '缺少product_id参数'
            }, status=status.HTTP_400_BAD_REQUEST)

        product = get_object_or_404(CleanProduct, pk=product_id)
        heat_score = calculate_item_heat(product)

        return Response({
            'code': 200,
            'msg': '热度详情获取成功',
            'data': {
                'product': ProductSerializer(product).data,
                'heat_score': heat_score
            }
        })


