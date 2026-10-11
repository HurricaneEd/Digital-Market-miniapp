import uuid

from django.conf import settings
from django.core.files.storage import default_storage
from django.db.models.deletion import ProtectedError
from rest_framework import viewsets, status, filters
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from Users.models import User
from Users.serializer import (
    AdminUserSerializer,
    AvatarUploadSerializer,
    ChangePasswordSerializer,
    LoginSerializer,
    ProfileSerializer,
    RegisterSerializer,
    UserSerializer,
)


# Create your views here.
class UserViewSet(viewsets.GenericViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        action = getattr(self, 'action', None)
        serializers_by_action = {
            'register': RegisterSerializer,
            'login': LoginSerializer,
            'change_password': ChangePasswordSerializer,
            'profile': ProfileSerializer,
            'upload_avatar': AvatarUploadSerializer,
        }
        return serializers_by_action.get(action, self.serializer_class)

    # 1. 注册逻辑
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def register(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'username': user.username,
            'avatar': user.avatar
        }, status=status.HTTP_201_CREATED)

    # 2. 登录逻辑
    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def login(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

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
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        file = serializer.validated_data['avatar']

        suffix = file.validated_extension
        file_name = f"avatars/user_{request.user.id}_{uuid.uuid4().hex}{suffix}"

        path = default_storage.save(file_name, file)

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
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()

        return Response({'message': '密码修改成功'})

    # 5. 获取/更新用户资料
    @action(detail=False, methods=['get', 'put'], permission_classes=[IsAuthenticated])
    def profile(self, request):
        user = request.user

        if request.method == 'GET':
            return Response(self.get_serializer(user).data)

        serializer = self.get_serializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        response_data = self.get_serializer(serializer.instance).data
        response_data['message'] = '资料更新成功'
        return Response(response_data)


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

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {'detail': '该用户存在历史订单，不能删除；请改为停用账号'},
                status=status.HTTP_409_CONFLICT,
            )

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
