from django.conf import settings
from django.contrib.auth import authenticate
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from rest_framework import viewsets, status, filters
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from Users.models import User, UserAction, Favorite
from Users.serializer import UserSerializer, UserActionSerializer, FavoriteSerializer, AdminUserSerializer
from Orders.models import Order, CartItem, Address, OrderItem


# Create your views here.
class UserViewSet(viewsets.GenericViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    # 1. 注册逻辑
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def register(self, request):
        import re
        username = request.data.get('username')
        phone = request.data.get('phone')
        email = request.data.get('email')
        password = request.data.get('password')
        if not username or not phone or not email or not password:
            return Response({'error': '请填写完整信息'}, status=status.HTTP_400_BAD_REQUEST)
        # 验证手机号格式（11位数字）
        if not re.match(r'^1[3-9]\d{9}$', phone):
            return Response({'error': '手机号格式不正确'}, status=status.HTTP_400_BAD_REQUEST)
        # 验证邮箱格式
        if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
            return Response({'error': '邮箱格式不正确'}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(username=username).exists():
            return Response({'error': '用户名已存在'}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(phone=phone).exists():
            return Response({'error': '手机号已被注册'}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(email=email).exists():
            return Response({'error': '邮箱已被注册'}, status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.create_user(username=username, password=password)
        user.phone = phone
        user.email = email
        user.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'username': user.username,
            'avatar': user.avatar
        }, status=status.HTTP_201_CREATED)

    # 2. 登录逻辑
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def login(self, request):
        identifier = request.data.get('identifier')  # 可以是用户名、手机号或邮箱
        password = request.data.get('password')
        if not identifier or not password:
            return Response({'error': '请填写完整信息'}, status=status.HTTP_400_BAD_REQUEST)
        # 根据identifier类型进行认证
        if '@' in identifier:
            # 是邮箱
            user = User.objects.filter(email=identifier).first()
            if user:
                if user.check_password(password):
                    pass
                else:
                    return Response({'error': '用户名、手机号或邮箱或密码错误'}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({'error': '用户名、手机号或邮箱或密码错误'}, status=status.HTTP_400_BAD_REQUEST)
        elif identifier.isdigit():
            # 是手机号
            user = User.objects.filter(phone=identifier).first()
            if user:
                if user.check_password(password):
                    pass
                else:
                    return Response({'error': '用户名、手机号或邮箱或密码错误'}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({'error': '用户名、手机号或邮箱或密码错误'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            # 是用户名
            user = authenticate(username=identifier, password=password)
            if not user:
                return Response({'error': '用户名、手机号或邮箱或密码错误'}, status=status.HTTP_400_BAD_REQUEST)

        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_profile': {
                'uid': user.id,
                'username': user.username,
                'nickname': user.nickname or '',
                'phone': user.phone,
                'email': user.email,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
                'avatar': user.avatar if user.avatar else '',
            }
        })

    # 3. 获取当前登录用户信息
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        user = request.user
        return Response({
            'username': user.username,
            'nickname': user.nickname or '',
            'avatar': user.avatar,
            'is_staff': user.is_staff
        })

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def upload_avatar(self, request):
        file = request.FILES.get('avatar')
        if not file:
            return Response({'error': '未选择图片'}, status=400)

        # 1. 构造存储路径 (例如: avatars/user_1.jpg)
        file_name = f"avatars/user_{request.user.id}_{file.name}"

        # 2. 保存文件到 MEDIA_ROOT
        path = default_storage.save(file_name, ContentFile(file.read()))

        # 3. 更新数据库中的用户头像字段
        user = request.user
        avatar_url = settings.MEDIA_URL + path
        user.avatar = avatar_url
        user.save()

        return Response({
            'message': '上传成功',
            'avatar': avatar_url,
            'avatar_url': avatar_url
        })

    # 4. 修改密码
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def change_password(self, request):
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')

        if not old_password or not new_password or not confirm_password:
            return Response({'error': '请填写完整信息'}, status=status.HTTP_400_BAD_REQUEST)

        if new_password != confirm_password:
            return Response({'error': '两次输入的密码不一致'}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        if not user.check_password(old_password):
            return Response({'error': '当前密码错误'}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()

        return Response({'message': '密码修改成功'})

    # 5. 获取/更新用户资料
    @action(detail=False, methods=['get', 'put'], permission_classes=[IsAuthenticated])
    def profile(self, request):
        user = request.user

        if request.method == 'GET':
            return Response({
                'id': user.id,
                'username': user.username,
                'nickname': user.nickname,
                'email': user.email,
                'phone': user.phone,
                'avatar': user.avatar,
                'date_joined': user.date_joined,
            })

        # PUT 更新资料
        nickname = request.data.get('nickname')
        email = request.data.get('email')
        phone = request.data.get('phone')

        if nickname:
            user.nickname = nickname
        if email:
            user.email = email
        if phone:
            user.phone = phone

        user.save()
        return Response({
            'message': '资料更新成功',
            'nickname': user.nickname,
            'email': user.email,
            'phone': user.phone,
        })


class UserActionViewSet(viewsets.ModelViewSet):
    """用户行为记录"""
    serializer_class = UserActionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserAction.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class FavoriteViewSet(viewsets.ModelViewSet):
    """用户收藏管理"""
    serializer_class = FavoriteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Favorite.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['post'])
    def toggle(self, request):
        """切换收藏状态 - 添加或取消收藏"""
        product_id = request.data.get('product')
        if not product_id:
            return Response({'error': '缺少商品ID'}, status=status.HTTP_400_BAD_REQUEST)

        # 检查是否已收藏
        favorite = Favorite.objects.filter(user=request.user, product_id=product_id).first()

        if favorite:
            # 已收藏 -> 取消收藏
            favorite.delete()
            return Response({'status': 'removed', 'message': '取消收藏成功'})
        else:
            # 未收藏 -> 添加收藏
            note = request.data.get('note', '')
            Favorite.objects.create(user=request.user, product_id=product_id, note=note)
            return Response({'status': 'added', 'message': '收藏成功'})


class AdminUserPagination(PageNumberPagination):
    """后台用户管理分页"""
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class AdminUserViewSet(viewsets.ModelViewSet):
    """
    管理员用户管理接口
    支持：获取列表、查看详情、局部修改
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = AdminUserSerializer
    permission_classes = [IsAdminUser]
    pagination_class = AdminUserPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['username', 'email', 'phone']
    ordering_fields = ['date_joined', 'last_login', 'id']

    def perform_destroy(self, instance):
        user_id = instance.id
        # 先清除订单的地址引用，避免外键保护错误
        Order.objects.filter(user_id=user_id).update(address=None)
        # 删除关联的收货地址
        Address.objects.filter(user_id=user_id).delete()
        # 删除关联的用户行为记录
        UserAction.objects.filter(user_id=user_id).delete()
        # 删除关联的收藏
        Favorite.objects.filter(user_id=user_id).delete()
        # 先删除订单详情（OrderItem），避免外键保护错误
        OrderItem.objects.filter(order__user_id=user_id).delete()
        # 删除关联的订单
        Order.objects.filter(user_id=user_id).delete()
        # 删除关联的购物车项
        CartItem.objects.filter(user_id=user_id).delete()
        # 删除用户
        instance.delete()

    def get_queryset(self):
        queryset = super().get_queryset()
        # 处理 is_active 筛选（支持 true/false 布尔值和 'true'/'false' 字符串）
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            if str(is_active).lower() == 'true':
                queryset = queryset.filter(is_active=True)
            elif str(is_active).lower() == 'false':
                queryset = queryset.filter(is_active=False)
        return queryset

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        # 处理密码更新 (前端传 password)
        new_password = request.data.get('password')
        if new_password:
            instance.set_password(new_password)
            instance.save()

        self.perform_update(serializer)

        return Response(serializer.data)
