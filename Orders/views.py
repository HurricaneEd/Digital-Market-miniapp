import uuid
from collections import defaultdict
from decimal import Decimal
from django.db import models, transaction
from django.db.models import F, Sum

from rest_framework import mixins, permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from Orders.models import Order, OrderItem, CartItem, Address, ShippingAddressSnapshot
from Orders.serializer import (
    AddressSerializer,
    CartSerializer,
    CreateOrderSerializer,
    OrderBatchSerializer,
    OrderSerializer,
    PaymentSerializer,
)
from Product.models import Product


def get_checkout_lines(user, validated_data):
    """锁定结算商品，统一返回商品、数量和待删除购物车项。"""
    cart_item_ids = validated_data.get('cart_item_ids')
    if not cart_item_ids:
        try:
            product = Product.objects.select_for_update().get(
                prod_id=validated_data['product_id'],
            )
        except Product.DoesNotExist:
            raise serializers.ValidationError({'product_id': '商品不存在'})
        return [(product, validated_data['count'])], []

    cart_items = list(
        CartItem.objects.select_for_update().filter(
            id__in=cart_item_ids,
            user=user,
        )
    )
    if len(cart_items) != len(cart_item_ids):
        raise serializers.ValidationError({'error': '部分购物车商品不存在'})

    products = Product.objects.select_for_update().filter(
        pk__in=[item.product_id for item in cart_items],
    )
    products_by_id = {product.pk: product for product in products}
    lines = [
        (products_by_id.get(item.product_id), item.count)
        for item in cart_items
    ]
    return lines, [item.pk for item in cart_items]


def cancel_orders(queryset):
    """原子取消订单并归还创建订单时预占的库存。"""
    with transaction.atomic():
        orders = list(queryset.select_for_update())
        if not orders:
            return 0

        item_totals = OrderItem.objects.filter(
            order_id__in=[order.pk for order in orders],
            product_id__isnull=False,
        ).values('product_id').annotate(total=Sum('count'))
        restock = defaultdict(int)
        for item_total in item_totals:
            restock[item_total['product_id']] += item_total['total']

        for product_id, count in restock.items():
            Product.objects.filter(pk=product_id).update(stock=F('stock') + count)

        Order.objects.filter(pk__in=[order.pk for order in orders]).update(
            status=Order.Status.CANCELLED,
        )
        return len(orders)


class OrderViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """订单管理：查看订单列表、订单详情、创建订单"""
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'order_sn'  # 使用order_sn作为查找字段

    def get_serializer_class(self):
        action = getattr(self, 'action', None)
        if action == 'create':
            return CreateOrderSerializer
        if action == 'pay':
            return PaymentSerializer
        return self.serializer_class

    def get_queryset(self):
        # swagger 生成文档时没有真实用户，跳过用户过滤
        if getattr(self, 'swagger_fake_view', False):
            return Order.objects.none()
        # 只返回当前用户的订单
        return Order.objects.filter(user=self.request.user).prefetch_related(
            'items__product', 'shipping_address'
        ).order_by('-created_at')

    # 创建订单
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        input_serializer = self.get_serializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        address_id = input_serializer.validated_data['address_id']

        try:
            address = Address.objects.select_for_update().get(id=address_id, user=request.user)
        except Address.DoesNotExist:
            return Response({'error': '收货地址不存在'}, status=status.HTTP_400_BAD_REQUEST)

        lines, settled_cart_item_ids = get_checkout_lines(
            request.user,
            input_serializer.validated_data,
        )
        for product, count in lines:
            if product is None or not product.is_active:
                return Response({'error': '结算商品已下架'}, status=status.HTTP_400_BAD_REQUEST)
            if product.stock < count:
                return Response(
                    {'error': f'商品“{product.name}”库存不足'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        total_price = sum(
            (product.price * count for product, count in lines),
            Decimal('0.00'),
        )
        order_sn = f"ORD{uuid.uuid4().hex.upper()}"
        order = Order.objects.create(
            order_sn=order_sn,
            user=request.user,
            total_price=total_price,
            status=Order.Status.UNPAID,
        )
        ShippingAddressSnapshot.objects.create(
            order=order,
            receiver=address.receiver,
            phone=address.phone,
            detail=address.detail,
        )

        OrderItem.objects.bulk_create([
            OrderItem(
                order=order,
                product=product,
                product_code=product.prod_id,
                product_name=product.name,
                price=product.price,
                count=count,
            )
            for product, count in lines
        ])
        products = []
        for product, count in lines:
            product.stock -= count
            products.append(product)
        Product.objects.bulk_update(products, ['stock'])

        if settled_cart_item_ids:
            CartItem.objects.filter(pk__in=settled_cart_item_ids).delete()

        output_serializer = OrderSerializer(
            order,
            context=self.get_serializer_context(),
        )
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    # 自定义动作：确认收货
    @action(detail=True, methods=['post'])
    def confirm_receive(self, request, order_sn=None):
        """确认收货"""
        order = self.get_object()
        updated = Order.objects.filter(
            pk=order.pk,
            status=Order.Status.SHIPPED,
        ).update(status=Order.Status.COMPLETED)
        if not updated:
            return Response({'error': '只有已发货的订单才能确认收货'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status': '确认收货成功'})

    # 自定义动作：取消订单
    @action(detail=True, methods=['post'])
    def cancel(self, request, order_sn=None):
        """取消订单"""
        order = self.get_object()
        cancelled = cancel_orders(
            Order.objects.filter(
                pk=order.pk,
                status__in=[Order.Status.UNPAID, Order.Status.PAID],
            )
        )
        if not cancelled:
            return Response({'error': '该订单无法取消'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status': '订单已取消'})

    # 自定义动作：支付订单
    @action(detail=True, methods=['post'])
    def pay(self, request, order_sn=None):
        """支付订单"""
        order = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment_method = serializer.validated_data['payment_method']

        # 模拟支付成功（实际项目中需要接入微信/支付宝API）
        updated = Order.objects.filter(
            pk=order.pk,
            status=Order.Status.UNPAID,
        ).update(
            status=Order.Status.PAID,
            payment_method=payment_method,
        )
        if not updated:
            return Response({'error': '该订单无法支付'}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'status': 'success',
            'message': '支付成功',
            'order_sn': order.order_sn
        })


class AdminOrderViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """管理员订单管理"""
    queryset = Order.objects.all().prefetch_related('items__product', 'shipping_address').order_by('-created_at')
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAdminUser]
    lookup_field = 'order_sn'  # 使用order_sn作为查找字段

    def get_serializer_class(self):
        action = getattr(self, 'action', None)
        if action in {'batch_ship', 'batch_cancel'}:
            return OrderBatchSerializer
        return self.serializer_class

    def get_queryset(self):
        queryset = Order.objects.all().prefetch_related('items__product', 'shipping_address').order_by('-created_at')

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
        updated = Order.objects.filter(
            pk=order.pk,
            status=Order.Status.PAID,
        ).update(status=Order.Status.SHIPPED)
        if not updated:
            return Response({'error': '只有已支付订单才能发货'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status': '已设为发货状态'})

    # 自定义动作：取消订单
    @action(detail=True, methods=['post'])
    def cancel(self, request, order_sn=None):
        order = self.get_object()
        cancelled = cancel_orders(
            Order.objects.filter(
                pk=order.pk,
                status__in=[Order.Status.UNPAID, Order.Status.PAID],
            )
        )
        if not cancelled:
            return Response({'error': '该订单无法取消'}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'status': '已取消订单'})

    # 批量发货
    @action(detail=False, methods=['post'],url_path="batch-ship")
    def batch_ship(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order_sns = serializer.validated_data['order_nos']
        # 只对待支付的订单发货
        updated = Order.objects.filter(
            order_sn__in=order_sns,
            status=Order.Status.PAID,
        ).update(status=Order.Status.SHIPPED)
        return Response({'status': f'成功发货 {updated} 个订单'})

    # 批量取消
    @action(detail=False, methods=['post'],url_path="batch-cancel")
    def batch_cancel(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order_sns = serializer.validated_data['order_nos']
        # 只对未支付或已支付的订单进行取消
        updated = cancel_orders(
            Order.objects.filter(
                order_sn__in=order_sns,
                status__in=[Order.Status.UNPAID, Order.Status.PAID],
            )
        )
        return Response({'status': f'成功取消 {updated} 个订单'})


class CartViewSet(viewsets.ModelViewSet):
    """购物车管理"""
    permission_classes = [IsAuthenticated]
    serializer_class = CartSerializer

    def get_queryset(self):
        # swagger 生成文档时没有真实用户，跳过用户过滤
        if getattr(self, 'swagger_fake_view', False):
            return CartItem.objects.none()
        # 只能看到自己的购物车
        return CartItem.objects.filter(user=self.request.user).select_related(
            'product',
        ).order_by('-created_at')

    @transaction.atomic
    def perform_create(self, serializer):
        count = serializer.validated_data.get('count', 1)
        user = self.request.user
        product_id = serializer.validated_data['product'].pk
        cart_item = CartItem.objects.select_for_update().filter(
            user=user,
            product_id=product_id,
        ).first()
        product = Product.objects.select_for_update().get(pk=product_id)
        if cart_item is None:
            cart_item = CartItem.objects.select_for_update().filter(
                user=user,
                product_id=product_id,
            ).first()
        target_count = count + (cart_item.count if cart_item else 0)
        if not product.is_active:
            raise serializers.ValidationError({'product_id': '商品已下架'})
        if target_count > product.stock:
            raise serializers.ValidationError({
                'count': f'购物车数量不能超过库存（当前库存 {product.stock}）',
            })

        if cart_item is None:
            serializer.save(user=user, product=product)
            return

        cart_item.count = target_count
        cart_item.save(update_fields=['count', 'updated_at'])
        serializer.instance = cart_item

    @transaction.atomic
    def perform_update(self, serializer):
        cart_item = CartItem.objects.select_for_update().get(
            pk=serializer.instance.pk,
        )
        serializer.instance = cart_item
        if 'count' in serializer.validated_data:
            product = Product.objects.select_for_update().get(
                pk=cart_item.product_id,
            )
            count = serializer.validated_data['count']
            if not product.is_active:
                raise serializers.ValidationError({'product_id': '商品已下架'})
            if count > product.stock:
                raise serializers.ValidationError({
                    'count': f'购物车数量不能超过库存（当前库存 {product.stock}）',
                })
        serializer.save()


class AddressViewSet(viewsets.ModelViewSet):
    """收货地址管理"""
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # swagger 生成文档时没有真实用户，跳过用户过滤
        if getattr(self, 'swagger_fake_view', False):
            return Address.objects.none()
        return Address.objects.filter(user=self.request.user).order_by(
            '-is_default',
            '-id',
        )

    @transaction.atomic
    def perform_create(self, serializer):
        request_user = type(self.request.user).objects.select_for_update().get(
            pk=self.request.user.pk
        )
        is_default = serializer.validated_data.get('is_default', False)
        if not Address.objects.filter(user=request_user).exists():
            is_default = True
        # 如果设为默认地址，先取消其他默认地址
        if is_default:
            Address.objects.filter(user=request_user, is_default=True).update(is_default=False)
        serializer.save(user=request_user, is_default=is_default)

    @transaction.atomic
    def perform_update(self, serializer):
        request_user = type(self.request.user).objects.select_for_update().get(
            pk=self.request.user.pk
        )
        if serializer.validated_data.get('is_default') is True:
            Address.objects.filter(
                user=request_user,
                is_default=True,
            ).exclude(pk=serializer.instance.pk).update(is_default=False)
        serializer.save()

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        address = self.get_object()
        type(request.user).objects.select_for_update().get(pk=request.user.pk)
        was_default = address.is_default
        response = super().destroy(request, *args, **kwargs)
        if was_default:
            replacement = Address.objects.filter(user=request.user).order_by('-id').first()
            if replacement:
                replacement.is_default = True
                replacement.save(update_fields=['is_default'])
        return response

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def set_default(self, request, pk=None):
        """设为默认地址"""
        address = self.get_object()
        type(request.user).objects.select_for_update().get(pk=request.user.pk)
        # 取消其他默认地址
        Address.objects.filter(user=request.user, is_default=True).update(is_default=False)
        address.is_default = True
        address.save()
        return Response({'status': '已设为默认地址'})
