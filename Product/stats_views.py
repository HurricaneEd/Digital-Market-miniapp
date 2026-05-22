"""
数据统计 API
用于仪表盘可视化图表
"""
import os
from datetime import timedelta
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models import Count, Avg, Sum, Q
from django.db.models.functions import TruncDate

from Product.models import CleanProduct, Category, CleanReview
from Orders.models import Order, OrderItem
from Users.models import User


@api_view(['GET'])
def dashboard_stats(request):
    """获取仪表盘统计数据"""
    today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    thirty_days_ago = today - timedelta(days=30)

    # 1. 基础统计
    stats = {
        'total_products': CleanProduct.objects.count(),
        'total_users': User.objects.filter(is_active=True).count(),
        'total_orders': Order.objects.count(),
        'total_sales': float(Order.objects.filter(status__in=['paid', 'shipped', 'completed']).aggregate(Sum('total_price'))['total_price__sum'] or 0),
    }

    # 2. 订单状态分布
    order_status = Order.objects.values('status').annotate(count=Count('id'))
    stats['order_status_distribution'] = [
        {'name': get_status_text(item['status']), 'value': item['count']}
        for item in order_status
    ]

    # 3. 近7天销售趋势
    seven_days_ago = today - timedelta(days=7)
    daily_sales = Order.objects.filter(
        created_at__gte=seven_days_ago,
        status__in=['paid', 'shipped', 'completed']
    ).annotate(date=TruncDate('created_at')).values('date').annotate(
        total=Sum('total_price'),
        count=Count('id')
    ).order_by('date')

    stats['sales_trend'] = [
        {'date': str(item['date']), 'total': float(item['total'] or 0), 'count': item['count']}
        for item in daily_sales
    ]

    # 4. 热销商品TOP10
    hot_products = OrderItem.objects.values(
        'product__prod_id',
        'product__name'
    ).annotate(
        total_sales=Sum('price'),
        total_count=Sum('count')
    ).order_by('-total_count')[:10]

    stats['hot_products'] = [
        {
            'name': item['product__name'],
            'prod_id': item['product__prod_id'],
            'sales': float(item['total_sales'] or 0),
            'count': item['total_count']
        }
        for item in hot_products
    ]

    # 5. 用户增长趋势（近7天）
    daily_users = User.objects.filter(
        date_joined__gte=seven_days_ago
    ).annotate(date=TruncDate('date_joined')).values('date').annotate(
        count=Count('id')
    ).order_by('date')

    stats['user_growth'] = [
        {'date': str(item['date']), 'count': item['count']}
        for item in daily_users
    ]

    # 6. 商品分类分布 (使用 category_id 关联 Category 表)
    category_dist = CleanProduct.objects.values(
        'category_id'
    ).annotate(count=Count('prod_id')).order_by('-count')[:10]

    # 获取分类名
    category_ids = [item['category_id'] for item in category_dist]
    category_map = {c.id: c.name for c in Category.objects.filter(id__in=category_ids)}

    stats['category_distribution'] = [
        {'name': category_map.get(item['category_id'], '未分类'), 'value': item['count']}
        for item in category_dist
    ]

    # 7. 评分分布
    rating_ranges = [
        {'range': '5星', 'min': 4.5, 'max': 5.0},
        {'range': '4星', 'min': 3.5, 'max': 4.5},
        {'range': '3星', 'min': 2.5, 'max': 3.5},
        {'range': '2星', 'min': 1.5, 'max': 2.5},
        {'range': '1星', 'min': 0, 'max': 1.5},
    ]
    rating_dist = []
    for r in rating_ranges:
        count = CleanProduct.objects.filter(rate__gte=r['min'], rate__lt=r['max']).count()
        rating_dist.append({'range': r['range'], 'count': count})
    stats['rating_distribution'] = rating_dist

    # 8. 评论情感分析 (5个类别) - 从数据库读取
    label_counts = CleanReview.objects.exclude(
        sentiment_label=''
    ).values('sentiment_label').annotate(count=Count('id'))
    label_dict = {item['sentiment_label']: item['count'] for item in label_counts}
    order = ['极度正面', '正面', '中性', '负面', '极度负面']
    sentiment_dist = []
    for label in order:
        sentiment_dist.append({'label': label, 'value': label_dict.get(label, 0)})
    stats['sentiment_distribution'] = sentiment_dist


    # 10. 词云数据 - 积极词和消极词
    import jieba
    # 加载停用词
    stopwords_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '../AttachFile/stopwords_baidu.txt')
    stopwords = set()
    if os.path.exists(stopwords_path):
        with open(stopwords_path, 'r', encoding='utf-8') as f:
            stopwords = set(f.read().splitlines())

    # 加载情感词典 (ntusd)
    base_dir = 'D:/PycharmProjects/DigRecSys_1'
    positive_dict_path = os.path.join(base_dir, 'AttachFile', 'ntusd-positive.txt')
    negative_dict_path = os.path.join(base_dir, 'AttachFile', 'ntusd-negative.txt')
    stopwords_path = os.path.join(base_dir, 'AttachFile', 'stopwords_baidu.txt')
    positive_dict = set()
    negative_dict = set()

    if os.path.exists(positive_dict_path):
        with open(positive_dict_path, 'r', encoding='utf-8') as f:
            # 格式: 词语\t词频
            positive_dict = set(line.strip().split('\t')[0] for line in f if line.strip())

    if os.path.exists(negative_dict_path):
        with open(negative_dict_path, 'r', encoding='utf-8') as f:
            negative_dict = set(line.strip().split('\t')[0] for line in f if line.strip())

    # 读取数据库获取评论 (积极评论匹配ntusd-positive词典，消极评论匹配ntusd-negative词典)
    reviews = CleanReview.objects.exclude(sentiment_score__isnull=True).exclude(content='')
    positive_words = {}
    negative_words = {}

    for review in reviews:
        content = review.content
        sentiment_score = review.sentiment_score or 0.5
        if not content:
            continue

        # 分词
        words = jieba.cut(content)
        for word in words:
            word = word.strip()
            if not word or len(word) <= 1 or word in stopwords:
                continue

            # 积极评论只匹配积极词典
            if sentiment_score > 0.5 and word in positive_dict:
                positive_words[word] = positive_words.get(word, 0) + 1
            # 消极评论只匹配消极词典
            elif sentiment_score < 0.5 and word in negative_dict:
                negative_words[word] = negative_words.get(word, 0) + 1

    print(f"词云统计(ntusd过滤): 积极词={len(positive_words)}, 消极词={len(negative_words)}")

    # 取频率最高的前50个词
    pos_list = sorted(positive_words.items(), key=lambda x: x[1], reverse=True)[:50]
    neg_list = sorted(negative_words.items(), key=lambda x: x[1], reverse=True)[:50]

    stats['wordcloud_positive'] = [{'name': w[0], 'value': w[1]} for w in pos_list]
    stats['wordcloud_negative'] = [{'name': w[0], 'value': w[1]} for w in neg_list]

    # 11. 价格分布雷达图 (按分类统计)
    price_ranges = [
        {'range': '0-100', 'min': 0, 'max': 100},
        {'range': '100-300', 'min': 100, 'max': 300},
        {'range': '300-500', 'min': 300, 'max': 500},
        {'range': '500-1000', 'min': 500, 'max': 1000},
        {'range': '1000-3000', 'min': 1000, 'max': 3000},
        {'range': '3000-7000', 'min': 3000, 'max': 7000},
        {'range': '7000-10000', 'min': 7000, 'max': 10000},
        {'range': '10000+', 'min': 10000, 'max': 999999},
    ]

    # 获取所有分类
    categories = Category.objects.all()[:6]  # 最多6个分类
    price_distribution = []

    for cat in categories:
        price_dist = []
        for r in price_ranges:
            # 统计该分类在各价格区间的订单数
            if r['max'] == 99999:
                count = OrderItem.objects.filter(
                    product__category_id=cat.id,
                    price__gte=r['min']
                ).count()
            else:
                count = OrderItem.objects.filter(
                    product__category_id=cat.id,
                    price__gte=r['min'],
                    price__lt=r['max']
                ).count()
            price_dist.append({'range': r['range'], 'count': count})
        price_distribution.append({
            'category': cat.name,
            'data': price_dist
        })

    stats['price_distribution'] = price_distribution

    return Response(stats)


def get_status_text(status):
    """订单状态转换"""
    status_map = {
        'unpaid': '待支付',
        'paid': '已支付',
        'shipped': '已发货',
        'completed': '已完成',
        'cancelled': '已取消',
    }
    return status_map.get(status, status)


@api_view(['GET'])
def dashboard_detail(request, chart_type):
    """获取图表详情数据"""
    from django.db.models import F

    today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    seven_days_ago = today - timedelta(days=7)

    result = {'data': [], 'columns': [], 'title': ''}

    if chart_type == 'sales':
        # 销售额趋势详情 - 每日订单列表
        result['title'] = '销售额趋势详情'
        orders = Order.objects.filter(
            created_at__gte=seven_days_ago,
            status__in=['paid', 'shipped', 'completed']
        ).annotate(
            order_date=TruncDate('created_at')
        ).values('order_date').annotate(
            daily_total=Sum('total_price'),
            order_count=Count('id')
        ).order_by('-order_date')[:50]

        result['columns'] = [
            {'prop': 'date', 'label': '日期', 'width': '120'},
            {'prop': 'total', 'label': '销售额(¥)', 'width': '120'},
            {'prop': 'count', 'label': '订单数', 'width': '100'},
        ]
        result['data'] = [
            {'date': str(item['order_date']), 'total': f"¥{item['daily_total']:.2f}", 'count': item['order_count']}
            for item in orders
        ]

    elif chart_type == 'order_status':
        # 订单状态分布详情 - 订单列表
        result['title'] = '订单状态详情'
        orders = Order.objects.select_related('user').order_by('-created_at')[:50]
        result['columns'] = [
            {'prop': 'order_id', 'label': '订单号', 'width': '100'},
            {'prop': 'user', 'label': '用户', 'width': '100'},
            {'prop': 'status', 'label': '状态', 'width': '80'},
            {'prop': 'total', 'label': '金额(¥)', 'width': '100'},
            {'prop': 'created_at', 'label': '创建时间', 'width': '160'},
        ]
        result['data'] = [
            {
                'order_id': f"ORD{order.id:06d}",
                'user': order.user.username if order.user else '匿名',
                'status': get_status_text(order.status),
                'total': f"¥{order.total_price:.2f}",
                'created_at': order.created_at.strftime('%Y-%m-%d %H:%M')
            }
            for order in orders
        ]

    elif chart_type == 'hot_products':
        # 热销商品详情
        result['title'] = '热销商品详情'
        hot_items = OrderItem.objects.values(
            'product__prod_id',
            'product__name'
        ).annotate(
            total_sales=Sum(F('price') * F('count')),
            total_count=Sum('count')
        ).order_by('-total_count')[:50]

        result['columns'] = [
            {'prop': 'prod_id', 'label': '商品ID', 'width': '80'},
            {'prop': 'name', 'label': '商品名称', 'width': '200'},
            {'prop': 'sales', 'label': '销售额(¥)', 'width': '120'},
            {'prop': 'count', 'label': '销量', 'width': '80'},
        ]
        result['data'] = [
            {
                'prod_id': item['product__prod_id'],
                'name': item['product__name'],
                'sales': f"¥{item['total_sales']:.2f}",
                'count': item['total_count']
            }
            for item in hot_items
        ]

    elif chart_type == 'sentiment':
        # 评论情感分析详情 - 从数据库读取
        result['title'] = '评论情感详情'
        reviews = CleanReview.objects.exclude(
            sentiment_label=''
        ).values('content', 'sentiment_label', 'sentiment_score')[:50]
        comments = [
            {
                'content': (r['content'][:50] + '...' if len(r['content']) > 50 else r['content']) if r['content'] else '',
                'sentiment': r['sentiment_label'] or '未知',
                'score': r['sentiment_score'] or ''
            }
            for r in reviews
        ]
        result['columns'] = [
            {'prop': 'content', 'label': '评论内容', 'width': '300'},
            {'prop': 'sentiment', 'label': '情感分类', 'width': '100'},
            {'prop': 'score', 'label': '情感得分', 'width': '80'},
        ]
        result['data'] = comments

    elif chart_type == 'price':
        # 价格分布详情 (所有订单的价格分布)
        result['title'] = '订单价格分布详情'
        orders = Order.objects.filter(
            status__in=['paid', 'shipped', 'completed']
        ).order_by('-total_price')[:50]

        result['columns'] = [
            {'prop': 'order_id', 'label': '订单号', 'width': '100'},
            {'prop': 'total', 'label': '订单金额(¥)', 'width': '120'},
            {'prop': 'status', 'label': '状态', 'width': '80'},
            {'prop': 'created_at', 'label': '创建时间', 'width': '160'},
        ]
        result['data'] = [
            {
                'order_id': f"ORD{order.id:06d}",
                'total': f"¥{order.total_price:.2f}",
                'status': get_status_text(order.status),
                'created_at': order.created_at.strftime('%Y-%m-%d %H:%M')
            }
            for order in orders
        ]

    return Response(result)


@api_view(['GET'])
def dashboard_heatmap(request):
    """获取热力图数据"""
    import jieba
    from datetime import timedelta

    today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    thirty_days_ago = today - timedelta(days=30)

    result = {}

    # 1. 用户-商品交互热力图 (按分类统计用户活跃度)
    # 横轴: 分类, 纵轴: 用户活跃度分段
    categories = Category.objects.all()[:8]
    user_segments = ['高活跃(>10次)', '中活跃(3-10次)', '低活跃(1-3次)', '沉默(0次)']

    # 统计数据
    heatmap_data = []
    for cat_idx, cat in enumerate(categories):
        # 获取该分类下的商品 (使用 category_id 关联)
        products = CleanProduct.objects.filter(category_id=cat.id)
        product_ids = list(products.values_list('prod_id', flat=True))

        # 统计各活跃度段的用户数
        high_active = OrderItem.objects.filter(
            product_id__in=product_ids
        ).values('order__user').annotate(
            order_count=Sum('count')
        ).filter(order_count__gt=10).count()

        mid_active = OrderItem.objects.filter(
            product_id__in=product_ids
        ).values('order__user').annotate(
            order_count=Sum('count')
        ).filter(order_count__gt=2, order_count__lte=10).count()

        low_active = OrderItem.objects.filter(
            product_id__in=product_ids
        ).values('order__user').annotate(
            order_count=Sum('count')
        ).filter(order_count__gte=1, order_count__lte=2).count()

        # 该分类的总用户
        total_users = User.objects.filter(is_active=True).count()
        silent = total_users - high_active - mid_active - low_active

        # 按纵轴顺序添加数据 [x(分类索引), y(活跃度索引), value]
        heatmap_data.append([cat_idx, 0, high_active])  # 高活跃
        heatmap_data.append([cat_idx, 1, mid_active])  # 中活跃
        heatmap_data.append([cat_idx, 2, low_active])  # 低活跃
        heatmap_data.append([cat_idx, 3, max(0, silent)])  # 沉默

    # 构建用户-商品热力图
    result['user_product_heatmap'] = {
        'xAxis': {'type': 'category', 'data': [cat.name for cat in categories], 'name': '商品分类'},
        'yAxis': {'type': 'category', 'data': user_segments, 'name': '用户活跃度'},
        'series': [{
            'type': 'heatmap',
            'data': heatmap_data,
            'itemStyle': {
                'color': '#6366f1'
            },
            'emphasis': {
                'itemStyle': {
                    'shadowBlur': 10,
                    'shadowColor': 'rgba(0, 0, 0, 0.5)'
                }
            }
        }]
    }

    return Response(result)