import uuid
from decimal import Decimal
from django.db import models

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from Orders.models import Order, OrderItem, CartItem, Address
from Orders.serializer import OrderSerializer, CartSerializer, AddressSerializer
from Users.models import UserAction


class OrderViewSet(viewsets.ModelViewSet):
    """订单管理：查看订单列表、订单详情、创建订单"""
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'order_sn'  # 使用order_sn作为查找字段

    def get_queryset(self):
        # 只返回当前用户的订单
        return Order.objects.filter(user=self.request.user).order_by('-created_at')

    # 创建订单
    def create(self, request, *args, **kwargs):
        address_id = request.data.get('address_id')
        cart_item_ids = request.data.get('cart_item_ids', [])

        if not address_id:
            return Response({'error': '请选择收货地址'}, status=status.HTTP_400_BAD_REQUEST)

        if not cart_item_ids:
            return Response({'error': '请选择要结算的商品'}, status=status.HTTP_400_BAD_REQUEST)

        # 获取收货地址
        try:
            address = Address.objects.get(id=int(address_id), user=request.user)
        except (Address.DoesNotExist, ValueError):
            return Response({'error': '收货地址不存在'}, status=status.HTTP_400_BAD_REQUEST)

        # 获取购物车商品
        cart_items = CartItem.objects.filter(id__in=cart_item_ids, user=request.user)
        if not cart_items.exists():
            return Response({'error': '购物车商品不存在'}, status=status.HTTP_400_BAD_REQUEST)

        # 计算订单总价
        total_price = sum(Decimal(str(item.product.price)) * item.count for item in cart_items)

        # 生成订单号
        order_sn = f"ORD{uuid.uuid4().hex[:12].upper()}"

        # 创建订单
        order = Order.objects.create(
            order_sn=order_sn,
            user=request.user,
            address=address,
            total_price=total_price,
            status='unpaid'  # 待支付状态
        )

        # 创建订单商品详情
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                price=item.product.price,
                count=item.count
            )

        # 删除已结算的购物车商品
        cart_items.delete()

        serializer = self.get_serializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    # 自定义动作：确认收货
    @action(detail=True, methods=['post'])
    def confirm_receive(self, request, order_sn=None):
        """确认收货"""
        order = self.get_object()
        if order.status != 'shipped':
            return Response({'error': '只有已发货的订单才能确认收货'}, status=status.HTTP_400_BAD_REQUEST)
        order.status = 'completed'
        order.save()
        return Response({'status': '确认收货成功'})

    # 自定义动作：取消订单
    @action(detail=True, methods=['post'])
    def cancel(self, request, order_sn=None):
        """取消订单"""
        order = self.get_object()
        if order.status not in ['unpaid', 'paid', 'shipped']:
            return Response({'error': '该订单无法取消'}, status=status.HTTP_400_BAD_REQUEST)
        order.status = 'cancelled'
        order.save()
        return Response({'status': '订单已取消'})

    # 自定义动作：支付订单
    @action(detail=True, methods=['post'])
    def pay(self, request, order_sn=None):
        """支付订单"""
        order = self.get_object()
        if order.status != 'unpaid':
            return Response({'error': '该订单无法支付'}, status=status.HTTP_400_BAD_REQUEST)

        payment_method = request.data.get('payment_method', 'wechat')  # 默认微信支付

        # 模拟支付成功（实际项目中需要接入微信/支付宝API）
        order.status = 'paid'
        order.payment_method = payment_method
        order.save()

        # 记录购买行为 (让模型的 save 方法处理合并逻辑)
        order_items = OrderItem.objects.filter(order=order)
        for item in order_items:
            UserAction.objects.create(
                user=order.user,
                product=item.product,
                action_type='buy',
                score=5 * item.count,
                count=item.count
            )

        return Response({
            'status': 'success',
            'message': '支付成功',
            'order_sn': order.order_sn
        })


class AdminOrderViewSet(viewsets.ModelViewSet):
    """管理员订单管理"""
    queryset = Order.objects.all().order_by('-created_at')
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAdminUser]
    lookup_field = 'order_sn'  # 使用order_sn作为查找字段

    def get_queryset(self):
        queryset = Order.objects.all().order_by('-created_at')

        # 搜索订单号或用户名
        search = self.request.query_params.get('search', '')
        if search:
            queryset = queryset.filter(
                models.Q(order_sn__icontains=search) |
                models.Q(user__username__icontains=search)
            )

        # 状态筛选
        status = self.request.query_params.get('status', '')
        if status:
            queryset = queryset.filter(status=status)

        return queryset

    # 自定义动作：发货
    @action(detail=True, methods=['post'])
    def ship(self, request, order_sn=None):
        order = self.get_object()
        order.status = 'shipped'
        order.save()
        return Response({'status': '已设为发货状态'})

    # 自定义动作：取消订单
    @action(detail=True, methods=['post'])
    def cancel(self, request, order_sn=None):
        order = self.get_object()
        order.status = 'cancelled'
        order.save()
        return Response({'status': '已取消订单'})

    # 批量发货
    @action(detail=False, methods=['post'],url_path="batch-ship")
    def batch_ship(self, request):
        order_sns = request.data.get('order_nos', [])
        # 只对待支付的订单发货
        updated = Order.objects.filter(order_sn__in=order_sns, status='paid').update(status='shipped')
        return Response({'status': f'成功发货 {updated} 个订单'})

    # 批量取消
    @action(detail=False, methods=['post'],url_path="batch-cancel")
    def batch_cancel(self, request):
        order_sns = request.data.get('order_nos', [])
        # 只对未支付或已支付的订单进行取消
        updated = Order.objects.filter(order_sn__in=order_sns, status__in=['unpaid', 'paid']).update(status='cancelled')
        return Response({'status': f'成功取消 {updated} 个订单'})


class CartViewSet(viewsets.ModelViewSet):
    """购物车管理"""
    permission_classes = [IsAuthenticated]
    serializer_class = CartSerializer

    def get_queryset(self):
        # 只能看到自己的购物车
        return CartItem.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        # 从已校验数据中 获取商品对象和数量
        product = serializer.validated_data.get('product')
        count = serializer.validated_data.get('count', 1)
        user = self.request.user
        # 检查购物车是否已存在该商品
        cart_item = CartItem.objects.filter(user=user, product=product).first()
        if cart_item:
            # 如果存在，则累加数量并保存
            cart_item.count += count
            cart_item.save()
        else:
            # 如果不存在，则正常创建并关联用户
            serializer.save(user=user)


class AddressViewSet(viewsets.ModelViewSet):
    """收货地址管理"""
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # 获取请求中的 is_default 值
        is_default = self.request.data.get('is_default', False)
        # 如果设为默认地址，先取消其他默认地址
        if str(is_default).lower() in ('true', '1', 'yes'):
            Address.objects.filter(user=self.request.user, is_default=True).update(is_default=False)
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """设为默认地址"""
        address = self.get_object()
        # 取消其他默认地址
        Address.objects.filter(user=request.user, is_default=True).update(is_default=False)
        address.is_default = True
        address.save()
        return Response({'status': '已设为默认地址'})
