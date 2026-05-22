"""
推荐算法核心模块
包含：热度推荐、协同过滤、内容推荐、混合推荐
"""
import math
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DigRecSys.settings')
_django_initialized = False

def _ensure_django():
    global _django_initialized
    if not _django_initialized:
        django.setup()
        _django_initialized = True

from datetime import datetime
from collections import defaultdict
from django.utils import timezone
from django.db.models import Count, Sum
from Product.models import CleanProduct, Category, Brand, CleanReview
from Users.models import User, UserAction, Favorite


# 向量计算工具
def cosine_similarity(vec1, vec2):
    """
    计算两个向量的余弦相似度
    vec1, vec2: dict 格式 {feature: weight}
    返回: 0~1 之间的相似度值
    """
    if not vec1 or not vec2:
        return 0.0
    # 计算点积
    dot_product = sum(vec1.get(k, 0) * vec2.get(k, 0) for k in set(vec1.keys()) & set(vec2.keys()))
    # 计算模长
    norm1 = math.sqrt(sum(v * v for v in vec1.values()))
    norm2 = math.sqrt(sum(v * v for v in vec2.values()))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot_product / (norm1 * norm2)


def get_category_idf_weights():
    """
    计算分类的IDF权重
    返回: {category_code: idf_weight}
    大众分类（商品多）权重低，小众分类权重高
    """
    if not IDF_CONFIG.get('enable', True):
        return {}
    threshold = IDF_CONFIG.get('threshold', 100)
    popular_boost = IDF_CONFIG.get('popular_boost', 0.5)
    niche_boost = IDF_CONFIG.get('niche_boost', 2.0)
    all_products = CleanProduct.objects.filter(is_active=True, category_id__isnull=False)
    total_products = all_products.count()
    if total_products == 0:
        return {}
    # 统计每个 category_id 的商品数量
    cat_product_counts = {}
    for product in all_products:
        cat_id = product.category_id
        if cat_id:
            cat_product_counts[cat_id] = cat_product_counts.get(cat_id, 0) + 1
    # 获取分类code映射
    idf_weights = {}
    cat_ids = list(cat_product_counts.keys())
    categories = Category.objects.filter(id__in=cat_ids)
    cat_code_map = {c.id: c.code for c in categories}
    for cat_id, count in cat_product_counts.items():
        cat_code = cat_code_map.get(cat_id)
        if not cat_code:
            continue
        if count > threshold:
            idf_weights[cat_code] = popular_boost
        else:
            idf_weights[cat_code] = min(niche_boost, total_products / max(count, 1))
    return idf_weights


# 配置参数
ACTION_WEIGHTS = {
    'view': 1,        # 浏览
    'cart': 4,         # 加购
    'buy': 10,        # 购买（最高权重，表示强意向）
    'favorite': 6,     # 收藏（重要交互）
    'comment': 3,     # 评论
    'dislike': -5,    # 负反馈：不感兴趣/不喜欢
}

# 内容推荐 IDF 配置（逆文档频率）
IDF_CONFIG = {
    'enable': True,       # 是否启用IDF加权
    'popular_boost': 0.5,  # 大众品牌降权系数 (0-1之间)
    'niche_boost': 2.0, # 小众偏好加权系数 (>1)
    'threshold': 100,    # 当某品牌商品数>threshold时视为大众品牌
}

# 基础热度配置（按分类）- 不同品类根据用户兴趣度设置不同基础值
# 可以根据不同时间段的用户行为数据动态调整
CATEGORY_BASE_HEAT = {
    'cell_phone': 100,      # 手机 - 高热度品类
    'digital_camera': 80,  # 数码相机
    'mice': 90,            # 鼠标 - 常用配件
    'pocketpower': 70,     # 移动电源
    'tablepc': 60,         # 平板电脑
    'laptop': 95,          # 笔记本 - 高热度品类
    'earphone': 85,       # 耳机 - 热门配件
    'keyboard': 75,        # 键盘
}

# 默认分类基础热度
DEFAULT_BASE_HEAT = 50
# 时间衰减配置：半衰期（小时）- 牛顿冷却定律
# 商品热度每经过这个时间衰减一半
HALF_LIFE_HOURS = 168  # 7天
# 时间衰减系数，用于控制衰减速度
DECAY_COEFFICIENT = 0.05  # 衰减系数k
# 用户画像时间衰减配置（小时）- 控制近期行为的权重
# 近期行为权重更高，历史行为逐渐衰减
PROFILE_HALF_LIFE_HOURS = 72  # 3天内行为权重最高，之后逐渐衰减

# 工具函数
def get_interacted_product_ids(user_id):
    """获取用户已交互的商品ID集合"""
    if user_id is None:
        return set()
    user_actions = UserAction.objects.filter(user_id=user_id).values_list('product_id', flat=True)
    user_favorites = Favorite.objects.filter(user_id=user_id).values_list('product_id', flat=True)
    return set(user_actions) | set(user_favorites)


# 一、热度推荐算法 
def calculate_item_heat(product, current_time=None, interaction_heat=0):
    """
    计算单个商品的热度值，总热度 = (基础热度 + 用户交互热度) / T(Time)
    其中 T(Time) = 2^(Δt / T_half) 为时间衰减因子（基于牛顿冷却定律的半衰期公式），T(Time) >= 1，随时间增长，热度逐渐衰减趋近于0
    """
    if current_time is None:
        current_time = timezone.now()
    # 基础热度 - 按分类（不同品类设置不同基础值）
    if product.category_id:
        cat = Category.objects.filter(id=product.category_id).first()
        category_code = cat.code if cat else 'default'
    else:
        category_code = 'default'
    base_heat = CATEGORY_BASE_HEAT.get(category_code, DEFAULT_BASE_HEAT)
    # 用户交互热度 -
    if interaction_heat is None:
        interaction_heat = 0
    # 确保基础热度 + 交互热度不小于0
    base_score = max(base_heat + interaction_heat, 0)
    # 时间衰减因子 - 基于牛顿冷却定律的半衰期公式T(Time) = 2^(Δt / T_half)，Δt 越大，T(Time) 越大，热度越低
    item_time = product.updated_at
    if item_time:
        hours_diff = (current_time - item_time).total_seconds() / 3600
        # 半衰期公式: 时间每增加 T_half，衰减因子翻倍，使用 max 确保衰减因子至少为1（不放大热度）
        time_factor = max(1.0, math.pow(2, hours_diff / HALF_LIFE_HOURS))
    else:
        time_factor = 1.0
    # 计算最终热度: 基础分除以时间衰减因子，时间越久远，time_factor越大，热度越低
    total_heat = base_score / time_factor
    return round(total_heat, 2)


def get_hot_items(top_n=20, category_code=None, exclude_ids=None):
    """
    获取热度排名前N的商品
    """
    current_time = timezone.now()
    # 获取基础商品列表
    products = CleanProduct.objects.filter(is_active=True)
    if category_code:
        # 先获取分类ID，再按 category_id 过滤
        cat = Category.objects.filter(code=category_code).first()
        if cat:
            products = products.filter(category_id=cat.id)
    # 排除指定商品
    if exclude_ids:
        products = products.exclude(prod_id__in=exclude_ids)
    # 预加载关联
    products = list(products)
    if not products:
        return []
    # 批量获取所有商品的交互热度
    product_ids = [p.prod_id for p in products]
    # 获取所有交互记录，按商品分组计算
    action_records = UserAction.objects.filter(product_id__in=product_ids).values('product_id').annotate(total_count=Sum('count'))
    # 计算热度和度（浏览=1, 加购=4, 购买=5）
    action_heat_map = {}
    for record in action_records:
        pid = record['product_id']
        action_heat_map[pid] = record['total_count'] or 0
    # 获取收藏数量并单独计算
    fav_counts = Favorite.objects.filter(product_id__in=product_ids).values('product_id').annotate(count=Count('id'))
    fav_heat_map = {item['product_id']: item['count'] * 3 for item in fav_counts}
    # 重新获取带类型加权的交互
    action_heat_map = {}
    for action in UserAction.objects.filter(product_id__in=product_ids):
        pid = action.product_id
        weight = ACTION_WEIGHTS.get(action.action_type, 1)
        action_heat_map[pid] = action_heat_map.get(pid, 0) + weight * action.count
    # 计算热度并排序
    heat_scores = []
    for product in products:
        # 交互热度
        interaction_heat = action_heat_map.get(product.prod_id, 0) + fav_heat_map.get(product.prod_id, 0)
        heat = calculate_item_heat(product, current_time, interaction_heat)
        heat_scores.append((product, heat))
    # 按热度降序排序
    heat_scores.sort(key=lambda x: x[1], reverse=True)
    return heat_scores[:top_n]


# UserCF协同过滤推荐算法
def build_user_item_matrix():
    """
    构建用户-商品交互矩阵
    """
    matrix = defaultdict(dict)
    actions = UserAction.objects.all()
    favorites = Favorite.objects.all()
    for action in actions:
        uid = action.user_id
        pid = action.product_id
        weight = ACTION_WEIGHTS.get(action.action_type, 1)
        matrix[uid][pid] = matrix[uid].get(pid, 0) + weight * action.count
    for fav in favorites:
        uid = fav.user_id
        pid = fav.product_id
        matrix[uid][pid] = matrix[uid].get(pid, 0) + ACTION_WEIGHTS['favorite']
    return matrix

def calculate_user_similarity(user_matrix):
    user_similarity = defaultdict(dict)
    users = list(user_matrix.keys())
    if not users:
        return user_similarity
    # 构建倒排表
    item_users = defaultdict(set)
    for uid, items in user_matrix.items():
        for pid in items:
            item_users[pid].add(uid)
    # 只计算有共同商品的用户对
    for i, u in enumerate(users):
        for j in range(i + 1, len(users)):
            v = users[j]
            common = set(user_matrix[u].keys()) & set(user_matrix[v].keys())
            if not common:
                continue
            dot = sum(user_matrix[u][i] * user_matrix[v][i] for i in common)
            norm_u = math.sqrt(sum(user_matrix[u][i] ** 2 for i in user_matrix[u]))
            norm_v = math.sqrt(sum(user_matrix[v][i] ** 2 for i in user_matrix[v]))
            if norm_u > 0 and norm_v > 0:
                sim = dot / (norm_u * norm_v)
                user_similarity[u][v] = sim
                user_similarity[v][u] = sim
    return user_similarity

def user_cf_recommend(user_id, top_k=10, top_n=20):
    """协同过滤推荐"""
    user_id = int(user_id)
    user_matrix = build_user_item_matrix()
    if user_id not in user_matrix:
        return get_hot_items(top_n)
    user_similarity = calculate_user_similarity(user_matrix)
    if user_id not in user_similarity:
        return get_hot_items(top_n)
    # 获取最相似的K个用户
    similar_users = sorted(user_similarity[user_id].items(), key=lambda x: x[1], reverse=True)[:top_k]
    if not similar_users:
        return get_hot_items(top_n)
    # 计算推荐分数
    target_items = set(user_matrix[user_id].keys())
    candidates = defaultdict(float)
    for sim_user, sim_score in similar_users:
        if sim_user not in user_matrix:
            continue
        for pid, score in user_matrix[sim_user].items():
            if pid not in target_items:
                candidates[pid] += sim_score * score

    sorted_pids = sorted(candidates.items(), key=lambda x: x[1], reverse=True)[:top_n]
    # 获取商品对象
    result = []
    for pid, score in sorted_pids:
        try:
            product = CleanProduct.objects.get(prod_id=pid, is_active=True)
            result.append((product, score))
        except CleanProduct.DoesNotExist:
            continue
    return result

# Item-CF 协同过滤
def build_item_user_matrix():
    """
    构建商品-用户交互矩阵（倒排）
    用于Item-CF：matrix[商品ID] = {用户ID: 评分}
    """
    matrix = defaultdict(dict)
    actions = UserAction.objects.all()
    favorites = Favorite.objects.all()
    for action in actions:
        uid = action.user_id
        pid = action.product_id
        weight = ACTION_WEIGHTS.get(action.action_type, 1)
        matrix[pid][uid] = matrix[pid].get(uid, 0) + weight * action.count
    for fav in favorites:
        uid = fav.user_id
        pid = fav.product_id
        matrix[pid][uid] = matrix[pid].get(uid, 0) + ACTION_WEIGHTS['favorite']
    return matrix


def calculate_item_similarity(item_matrix):
    """
    计算商品相似度（Item-based CF）
    使用余弦相似度
    """
    item_similarity = defaultdict(dict)
    items = list(item_matrix.keys())
    if not items:
        return item_similarity
    # 构建用户-商品倒排表
    user_items = defaultdict(set)
    for iid, users in item_matrix.items():
        for uid in users:
            user_items[uid].add(iid)
    # 只计算有共同用户的商品对
    for i, item_i in enumerate(items):
        for j in range(i + 1, len(items)):
            item_j = items[j]
            common_users = set(item_matrix[item_i].keys()) & set(item_matrix[item_j].keys())
            if not common_users:
                continue
            # 余弦相似度
            dot = sum(item_matrix[item_i][u] * item_matrix[item_j][u] for u in common_users)
            norm_i = math.sqrt(sum(item_matrix[item_i][u] ** 2 for u in item_matrix[item_i]))
            norm_j = math.sqrt(sum(item_matrix[item_j][u] ** 2 for u in item_matrix[item_j]))
            if norm_i > 0 and norm_j > 0:
                sim = dot / (norm_i * norm_j)
                item_similarity[item_i][item_j] = sim
                item_similarity[item_j][item_i] = sim

    return item_similarity

def item_cf_recommend(user_id, top_k=10, top_n=20):
    """Item-CF 协同过滤推荐基于用户已交互的商品，推荐相似的商品"""
    user_id = int(user_id)
    # 获取用户已交互的商品
    user_interacted = get_interacted_product_ids(user_id)
    if not user_interacted:
        return get_hot_items(top_n)
    # 构建商品-用户矩阵
    item_matrix = build_item_user_matrix()
    # 如果没有足够的交互数据，回退到热度推荐
    if len(item_matrix) < 2:
        return get_hot_items(top_n)
    # 计算商品相似度
    item_similarity = calculate_item_similarity(item_matrix)
    # 找到用户交互过的商品中，最相似的商品
    target_items = set(user_interacted)
    candidates = defaultdict(float)
    for item_id in target_items:
        if item_id not in item_similarity:
            continue
        # 获取与该商品最相似的K个商品
        similar_items = sorted(item_similarity[item_id].items(), key=lambda x: x[1], reverse=True)[:top_k]
        for sim_item, sim_score in similar_items:
            if sim_item not in target_items:
                candidates[sim_item] += sim_score
    # 排序并取Top_N
    sorted_items = sorted(candidates.items(), key=lambda x: x[1], reverse=True)[:top_n]
    # 获取商品对象
    result = []
    for pid, score in sorted_items:
        try:
            product = CleanProduct.objects.get(prod_id=pid, is_active=True)
            result.append((product, score))
        except CleanProduct.DoesNotExist:
            continue
    if not result:
        return get_hot_items(top_n)
    return result

# 内容推荐算法
def get_user_profile(user_id):
    """
    获取用户兴趣画像
    支持负反馈： dislike / skip 会扣分
    支持近期行为加权：越近期的行为权重越高（基于半衰期衰减）
    返回：{
        'categories': {code: score},  # 正分
        'brands': {name: score},       # 正分
        'negative_categories': {code: score},  # 负分
        'negative_brands': {name: score},       # 负分
    }
    """
    profile = {
        'categories': defaultdict(float),
        'brands': defaultdict(float),
        'negative_categories': defaultdict(float),
        'negative_brands': defaultdict(float),
    }
    user_id = int(user_id)
    current_time = timezone.now()

    # UserAction记录（包含正负反馈）
    actions = UserAction.objects.filter(user_id=user_id)
    for action in actions:
        if action.product:
            # 计算时间衰减因子
            time_factor = 1.0
            if action.created_at:
                hours_diff = (current_time - action.created_at).total_seconds() / 3600
                # 半衰期衰减：时间越久远，权重越低
                time_factor = max(0.1, math.pow(2, -hours_diff / PROFILE_HALF_LIFE_HOURS))

            weight = ACTION_WEIGHTS.get(action.action_type, 1) * action.count * time_factor
            is_negative = weight < 0  # 负反馈
            # 确定目标字典（正或负）
            if is_negative:
                cat_dict = profile['negative_categories']
                brand_dict = profile['negative_brands']
            else:
                cat_dict = profile['categories']
                brand_dict = profile['brands']
            # 更新分类
            if action.product.category_id:
                cat = Category.objects.filter(id=action.product.category_id).first()
                if cat:
                    cat_dict[cat.code] += abs(weight)
            # 更新品牌
            if action.product.brand_id:
                brand = Brand.objects.filter(id=action.product.brand_id).first()
                if brand:
                    brand_dict[brand.name] += abs(weight)

    # 收藏记录
    favorites = Favorite.objects.filter(user_id=user_id)
    for fav in favorites:
        if fav.product:
            # 计算时间衰减因子
            time_factor = 1.0
            if fav.created_at:
                hours_diff = (current_time - fav.created_at).total_seconds() / 3600
                time_factor = max(0.1, math.pow(2, -hours_diff / PROFILE_HALF_LIFE_HOURS))

            weight = ACTION_WEIGHTS['favorite'] * time_factor
            if fav.product.category_id:
                cat = Category.objects.filter(id=fav.product.category_id).first()
                if cat:
                    profile['categories'][cat.code] += weight
            if fav.product.brand_id:
                brand = Brand.objects.filter(id=fav.product.brand_id).first()
                if brand:
                    profile['brands'][brand.name] += weight
    return profile

def calculate_content_similarity(user_profile, product, cat_idf_weights=None, brand_idf_weights=None):
    if cat_idf_weights is None:cat_idf_weights = get_category_idf_weights() if IDF_CONFIG.get('enable', True) else {}
    if brand_idf_weights is None:brand_idf_weights = get_brand_idf_weights() if IDF_CONFIG.get('enable', True) else {}
    # 构建商品向量
    product_vec = {}
    if product.category_id:
        cat = Category.objects.filter(id=product.category_id).first()
        if cat:
            weight = cat_idf_weights.get(cat.code, 1.0)
            product_vec[f'cat_{cat.code}'] = weight
    if product.brand_id:
        brand = Brand.objects.filter(id=product.brand_id).first()
        if brand:
            weight = brand_idf_weights.get(brand.name, 1.0)
            product_vec[f'brand_{brand.name}'] = weight
    if not product_vec:
        return 0.0
    # 构建用户向量（应用负反馈）
    user_vec = {}
    # 正反馈分类权重
    for cat_code, score in user_profile['categories'].items():
        weight = cat_idf_weights.get(cat_code, 1.0)
        user_vec[f'cat_{cat_code}'] = score * weight
    # 正反馈品牌权重
    for brand_name, score in user_profile['brands'].items():
        weight = brand_idf_weights.get(brand_name, 1.0)
        user_vec[f'brand_{brand_name}'] = score * weight
    # 负反馈（扣减权重）
    for cat_code, score in user_profile['negative_categories'].items():
        weight = cat_idf_weights.get(cat_code, 1.0)
        key = f'cat_{cat_code}'
        if key in user_vec:
            user_vec[key] -= score * weight
        else:
            user_vec[key] = -score * weight
    for brand_name, score in user_profile['negative_brands'].items():
        weight = brand_idf_weights.get(brand_name, 1.0)
        key = f'brand_{brand_name}'
        if key in user_vec:
            user_vec[key] -= score * weight
        else:
            user_vec[key] = -score * weight
    # 计算余弦相似度
    return cosine_similarity(user_vec, product_vec)


def get_brand_idf_weights():
    """
    计算品牌的IDF权重
    返回：{brand_name: idf_weight}
    大众品牌（商品多）权重低，小众品牌权重高
    """
    if not IDF_CONFIG.get('enable', True):
        return {}
    threshold = IDF_CONFIG.get('threshold', 100)
    popular_boost = IDF_CONFIG.get('popular_boost', 0.5)
    niche_boost = IDF_CONFIG.get('niche_boost', 2.0)
    # CleanProduct 使用 brand_id 存储品牌ID，需要通过遍历统计
    all_products = CleanProduct.objects.filter(is_active=True, brand_id__isnull=False)
    total_products = all_products.count()
    if total_products == 0:
        return {}
    # 统计每个 brand_id 的商品数量
    brand_product_counts = {}
    for product in all_products:
        brand_id = product.brand_id
        if brand_id:
            brand_product_counts[brand_id] = brand_product_counts.get(brand_id, 0) + 1
    # 获取品牌名称映射
    idf_weights = {}
    brand_ids = list(brand_product_counts.keys())
    brands = Brand.objects.filter(id__in=brand_ids)
    brand_name_map = {b.id: b.name for b in brands}
    for brand_id, count in brand_product_counts.items():
        brand_name = brand_name_map.get(brand_id)
        if not brand_name:
            continue
        if count > threshold:
            # 大众品牌→降权
            idf_weights[brand_name] = popular_boost
        else:
            # 小众品牌→加权
            idf_weights[brand_name] = min(niche_boost, total_products / max(count, 1))
    return idf_weights


def cb_recommend(user_id, top_n=20, category_code=None):
    """内容推荐 - 基于余弦相似度
    支持负反馈和IDF加权
    """
    user_id = int(user_id)
    user_profile = get_user_profile(user_id)
    if not user_profile['categories'] and not user_profile['brands']:
        return get_hot_items(top_n, category_code)
    # 获取候选商品
    products = CleanProduct.objects.filter(is_active=True)
    if category_code:
        cat = Category.objects.filter(code=category_code).first()
        if cat:
            products = products.filter(category_id=cat.id)
    # 排除已交互商品
    interacted_ids = get_interacted_product_ids(user_id)
    products = products.exclude(prod_id__in=interacted_ids)
    # 预获取IDF权重（避免重复计算）
    cat_idf_weights = get_category_idf_weights() if IDF_CONFIG.get('enable', True) else {}
    brand_idf_weights = get_brand_idf_weights() if IDF_CONFIG.get('enable', True) else {}
    # 计算余弦相似度
    scores = []
    for product in products:
        sim = calculate_content_similarity(user_profile, product, cat_idf_weights, brand_idf_weights)
        if sim > 0:
            scores.append((product, sim))
    scores.sort(key=lambda x: x[1], reverse=True)
    return scores[:top_n]


# 混合推荐
def hybrid_recommend(user_id, top_n=20, weights=None):
    if weights is None:
        weights = {'heat': 0.4, 'cf': 0.35, 'cb': 0.25}
    user_id = int(user_id)
    # 新用户冷启动处理
    interacted_ids = get_interacted_product_ids(user_id)
    if not interacted_ids:
        # 新用户：只用热度推荐
        return get_hot_items(top_n)
    # 正常推荐
    heat_items = {p[0].prod_id: p[1] for p in get_hot_items(top_n * 2, exclude_ids=interacted_ids)}
    cf_items = {p[0].prod_id: p[1] for p in item_cf_recommend(user_id, top_k=10, top_n=top_n * 2)}
    cb_items = {p[0].prod_id: p[1] for p in cb_recommend(user_id, top_n=top_n * 2)}
    all_ids = set(heat_items.keys()) | set(cf_items.keys()) | set(cb_items.keys())
    final_scores = []
    for pid in all_ids:
        score = 0.0
        if pid in heat_items:
            max_v = max(heat_items.values()) or 1
            score += weights['heat'] * (heat_items[pid] / max_v)
        if pid in cf_items:
            max_v = max(cf_items.values()) or 1
            score += weights['cf'] * (cf_items[pid] / max_v)
        if pid in cb_items:
            max_v = max(cb_items.values()) or 1
            score += weights['cb'] * (cb_items[pid] / max_v)
        final_scores.append((pid, score))
    final_scores.sort(key=lambda x: x[1], reverse=True)
    result = []
    for pid, score in final_scores[:top_n]:
        try:
            product = CleanProduct.objects.get(prod_id=pid, is_active=True)
            result.append((product, score))
        except CleanProduct.DoesNotExist:
            continue
    return result


