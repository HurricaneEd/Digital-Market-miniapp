
import os
import random
import sys
from datetime import timedelta

import django

# Django 初始化
project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_path)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DigRecSys.settings')
django.setup()

from django.utils import timezone
from django.db.models import Count
from Product.models import CleanProduct
from Users.models import Favorite, User, UserAction
from Orders.models import Order, OrderItem, CartItem, Address


def ensure_users(min_count=30):
    """确保有足够的用户"""
    # User 模型没有 role 字段，使用 is_staff=False 过滤普通用户
    current = User.objects.filter(is_staff=False, is_superuser=False).count()
    if current < min_count:
        need = min_count - current
        print(f"创建 {need} 个用户...")
        created = 0
        attempts = 0
        max_attempts = need * 10  # 防止死循环

        while created < need and attempts < max_attempts:
            attempts += 1
            username = f'testuser_{random.randint(10000, 99999)}'
            # 检查用户名是否已存在
            if User.objects.filter(username=username).exists():
                continue
            email = f'{username}@example.com'
            # 检查email是否已存在
            if User.objects.filter(email=email).exists():
                continue
            User.objects.create_user(username=username, password='123456', email=email)
            created += 1

        print(f"实际创建 {created} 个用户")

    # 修复空 email
    users_with_empty_email = User.objects.filter(email='')
    for user in users_with_empty_email:
        new_email = f'{user.username}@example.com'
        if not User.objects.filter(email=new_email).exists():
            user.email = new_email
            user.save(update_fields=['email'])

    print(f"用户数量: {User.objects.filter(is_staff=False, is_superuser=False).count()}")


def ensure_products():
    """确保有足够的商品"""
    count = CleanProduct.objects.filter(is_active=True).count()
    if count < 50:
        print(f"警告: CleanProduct 数量仅 {count}，建议至少 50 个")
    print(f"CleanProduct 数量: {count}")


def generate_user_actions():
    """生成用户行为数据 (浏览、加购)"""
    print("\n生成 UserAction 数据...")

    users = list(User.objects.filter(is_staff=False, is_superuser=False))
    products = list(CleanProduct.objects.filter(is_active=True))

    if not users or not products:
        print("错误: 用户或商品为空")
        return

    categories = list(set(p.category_id for p in products if p.category_id))

    # 按分类组织商品
    cat_products = {}
    for cat in categories:
        cat_products[cat] = [p for p in products if p.category_id == cat]

    count = 0
    for user in users:
        # 每个用户选择 2-4 个分类作为兴趣
        interest_cats = random.sample(categories, min(len(categories), random.randint(2, 4)))

        for cat in interest_cats:
            cat_prods = cat_products.get(cat, [])
            if not cat_prods:
                continue

            # 每个分类下交互 2-5 个商品
            interact_count = min(len(cat_prods), random.randint(2, 5))
            selected = random.sample(cat_prods, interact_count)

            for prod in selected:
                # 行为类型权重: 浏览 70%, 加购 30%
                action_type = random.choices(
                    ['view', 'cart'],
                    weights=[70, 30],
                    k=1
                )[0]

                score_map = {'view': 1, 'cart': 4}
                score = score_map[action_type]

                action, created = UserAction.objects.get_or_create(
                    user=user,
                    product=prod,
                    action_type=action_type,
                    defaults={
                        'score': score,
                        'count': random.randint(1, 3)
                    }
                )
                if created:
                    count += 1

    print(f"新增 {count} 条 UserAction 记录")


def generate_negative_feedback():
    """
    生成负反馈数据 (dislike/skip)
    用于测试内容推荐的负反馈功能
    """
    print("\n生成负反馈数据...")

    users = list(User.objects.filter(is_staff=False, is_superuser=False))
    products = list(CleanProduct.objects.filter(is_active=True))

    if not users or not products:
        print("错误: 用户或商品为空")
        return

    count = 0
    for user in users:
        # 30% 概率生成负反馈
        if random.random() > 0.3:
            continue

        # 选择 1-2 个商品标记为不喜欢
        skip_products = random.sample(products, min(len(products), random.randint(1, 2)))

        for prod in skip_products:
            # 负反馈类型
            action_type = 'dislike'
            score = -3

            # 删除该用户对该商品的所有旧行为（避免冲突）
            UserAction.objects.filter(
                user=user,
                product=prod
            ).delete()

            # 创建负反馈
            UserAction.objects.create(
                user=user,
                product=prod,
                action_type=action_type,
                score=score,
                count=1
            )
            count += 1

    print(f"新增 {count} 条负反馈记录")


def generate_cart_items():
    """生成购物车数据"""
    print("\n生成购物车数据...")

    users = list(User.objects.filter(is_staff=False, is_superuser=False))
    products = list(CleanProduct.objects.filter(is_active=True))

    if not users or not products:
        print("错误: 用户或商品为空")
        return

    count = 0
    for user in users:
        # 每个用户有 0-5 个购物车商品
        cart_count = random.randint(0, 5)
        selected = random.sample(products, min(len(products), cart_count))

        for prod in selected:
            # 检查是否已存在
            if not CartItem.objects.filter(user=user, product=prod).exists():
                CartItem.objects.create(
                    user=user,
                    product=prod,
                    count=random.randint(1, 3),
                    selected=random.choice([True, False])
                )
                count += 1

    print(f"新增 {count} 条购物车记录")


def generate_orders():
    """生成订单和支付状态数据"""
    print("\n生成订单数据...")

    users = list(User.objects.filter(is_staff=False, is_superuser=False))
    products = list(CleanProduct.objects.filter(is_active=True))

    if not users or not products:
        print("错误: 用户或商品为空")
        return

    # 先为每个用户创建一个默认收货地址
    for user in users:
        if not Address.objects.filter(user=user).exists():
            Address.objects.create(
                user=user,
                receiver=user.nickname or user.username,
                phone=user.phone or '13800138000',
                detail=f"默认收货地址{random.randint(1, 999)}号",
                is_default=True
            )

    # 状态权重: 已支付 30%, 已发货 20%, 已完成 40%, 已取消 10%
    status_weights = {
        'paid': 0.3,
        'shipped': 0.2,
        'completed': 0.4,
        'cancelled': 0.1,
    }

    order_count = 0
    item_count = 0

    for user in users:
        # 每个用户生成 0-3 个订单
        num_orders = random.randint(0, 3)
        for _ in range(num_orders):
            address = Address.objects.filter(user=user).first()
            if not address:
                continue

            # 选择订单状态
            status = random.choices(
                list(status_weights.keys()),
                weights=list(status_weights.values()),
                k=1
            )[0]

            # 选择商品 (1-3个)
            order_products = random.sample(products, random.randint(1, 3))

            # 计算总价
            total_price = sum(float(p.price) * random.randint(1, 2) for p in order_products)

            # 生成订单号（使用微秒确保唯一性）
            order_sn = f"ORD{timezone.now().strftime('%Y%m%d%H%M%S%f')}{random.randint(100, 999)}"

            # 创建订单
            payment_method = random.choice(['wechat', 'alipay'])

            order = Order.objects.create(
                order_sn=order_sn,
                user=user,
                address=address,
                total_price=total_price,
                status=status,
                payment_method=payment_method,
            )

            # 手动设置创建时间为过去90天内
            created_at = timezone.now() - timedelta(days=random.randint(0, 90))
            Order.objects.filter(pk=order.pk).update(created_at=created_at)

            order_count += 1

            # 创建订单项
            for prod in order_products:
                cnt = random.randint(1, 2)
                OrderItem.objects.create(
                    order=order,
                    product=prod,
                    price=prod.price,
                    count=cnt
                )
                item_count += 1

                # 如果是购买行为，同时创建 UserAction
                if status in ['paid', 'shipped', 'completed']:
                    UserAction.objects.get_or_create(
                        user=user,
                        product=prod,
                        action_type='buy',
                        defaults={
                            'score': 5 * cnt,
                            'count': cnt
                        }
                    )

    print(f"新增 {order_count} 条订单, {item_count} 条订单项")


def generate_favorites():
    """
    生成收藏数据
    Favorite 是协同过滤的重要信号（权重为5）
    """
    print("\n生成 Favorite 数据...")

    users = list(User.objects.filter(is_staff=False, is_superuser=False))
    products = list(CleanProduct.objects.filter(is_active=True))

    if not users or not products:
        print("错误: 用户或商品为空")
        return

    categories = list(set(p.category_id for p in products if p.category_id))
    cat_products = {}
    for cat in categories:
        cat_products[cat] = [p for p in products if p.category_id == cat]

    count = 0
    for user in users:
        # 每个用户收藏 3-10 个商品
        fav_count = random.randint(3, 10)

        # 从用户感兴趣的分类中选择
        interest_cats = random.sample(categories, min(len(categories), random.randint(2, 4)))

        candidates = []
        for cat in interest_cats:
            candidates.extend(cat_products.get(cat, []))

        if not candidates:
            continue

        selected = random.sample(candidates, min(len(candidates), fav_count))

        for prod in selected:
            fav, created = Favorite.objects.get_or_create(
                user=user,
                product=prod
            )
            if created:
                count += 1

    print(f"新增 {count} 条 Favorite 记录")


def verify_cf_data():
    """验证协同过滤数据是否就绪"""
    print("\n=== 验证协同过滤数据 ===")

    user_count = User.objects.filter(is_staff=False, is_superuser=False).count()
    product_count = CleanProduct.objects.filter(is_active=True).count()
    action_count = UserAction.objects.count()
    fav_count = Favorite.objects.count()
    cart_count = CartItem.objects.count()
    order_count = Order.objects.count()

    print(f"用户数: {user_count}")
    print(f"商品数: {product_count}")
    print(f"UserAction: {action_count}")
    print(f"Favorite: {fav_count}")
    print(f"CartItem: {cart_count}")
    print(f"Order: {order_count}")

    # 行为类型统计
    action_types = UserAction.objects.values('action_type').annotate(count=Count('id'))
    print("\n行为类型分布:")
    for item in action_types:
        print(f"  {item['action_type']}: {item['count']}")

    # 检查是否有共同行为
    from collections import defaultdict
    item_users = defaultdict(set)
    for action in UserAction.objects.all():
        item_users[action.product_id].add(action.user_id)
    for fav in Favorite.objects.all():
        item_users[fav.product_id].add(fav.user_id)

    # 统计有共同用户的商品对
    common_pairs = 0
    product_ids = list(item_users.keys())
    for i, p1 in enumerate(product_ids[:50]):  # 只检查前50个商品
        for p2 in product_ids[i+1:50]:
            if item_users[p1] & item_users[p2]:
                common_pairs += 1

    print(f"\n有共同用户的商品对: {common_pairs}")

    if action_count > 0 and fav_count > 0 and common_pairs > 0:
        print("OK: 协同过滤数据已就绪")
    else:
        print("FAIL: 数据不足以启动协同过滤")


if __name__ == "__main__":
    # Step 1: 确保用户和商品
    ensure_users(300)
    ensure_products()

    # Step 2: 生成行为数据 (浏览、加购)
    generate_user_actions()

    # Step 3: 生成收藏数据
    generate_favorites()

    # Step 4: 生成购物车数据
    generate_cart_items()

    # Step 5: 生成订单数据 (包含支付状态)
    generate_orders()

    # Step 6: 生成负反馈数据 (dislike/skip)
    generate_negative_feedback()

    # Step 7: 验证
    verify_cf_data()