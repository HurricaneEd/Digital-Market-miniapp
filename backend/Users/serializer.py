from django.contrib.auth import authenticate
from django.contrib.auth.validators import UnicodeUsernameValidator
from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    """用户信息"""
    class Meta:
        model = User
        fields = [
            'id', 'username', 'avatar', 'phone', 'nickname', 'email',
            'is_staff','is_superuser', 'date_joined'
        ]
        read_only_fields = ['is_staff','is_superuser', 'date_joined']


class RegisterSerializer(serializers.ModelSerializer):
    """注册参数校验和用户创建。"""

    password = serializers.CharField(write_only=True, min_length=6)
    phone = serializers.RegexField(
        regex=r'^1[3-9]\d{9}$',
        error_messages={'invalid': '手机号格式不正确'},
    )
    email = serializers.EmailField(
        error_messages={'invalid': '邮箱格式不正确'},
    )

    class Meta:
        model = User
        fields = ['username', 'phone', 'email', 'password']

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('用户名已存在')
        return value

    def validate_phone(self, value):
        value = value.strip()
        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError('手机号已被注册')
        return value

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('邮箱已被注册')
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    """登录参数校验，并根据用户名、手机号或邮箱查找用户。"""

    identifier = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        identifier = attrs['identifier'].strip()
        password = attrs['password']

        if '@' in identifier:
            user = User.objects.filter(email=identifier.lower()).first()
            authenticated = user and user.check_password(password)
        elif identifier.isdigit():
            user = User.objects.filter(phone=identifier).first()
            authenticated = user and user.check_password(password)
        else:
            user = authenticate(username=identifier, password=password)
            authenticated = user is not None

        if not authenticated:
            raise serializers.ValidationError(
                {'error': '用户名、手机号或邮箱或密码错误'}
            )

        attrs['user'] = user
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    """修改密码参数校验。"""

    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=6)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError('两次输入的密码不一致')
        if not self.context['request'].user.check_password(attrs['old_password']):
            raise serializers.ValidationError('当前密码错误')
        return attrs


class ProfileSerializer(serializers.ModelSerializer):
    """当前用户资料读写序列化器。"""

    username = serializers.CharField(
        required=False,
        max_length=150,
        validators=[UnicodeUsernameValidator()],
    )
    email = serializers.EmailField(
        required=False,
        allow_blank=True,
        error_messages={'invalid': '邮箱格式不正确'},
    )
    phone = serializers.RegexField(
        regex=r'^1[3-9]\d{9}$',
        required=False,
        allow_blank=True,
        error_messages={'invalid': '手机号格式不正确'},
    )

    class Meta:
        model = User
        fields = ['id', 'username', 'nickname', 'email', 'phone', 'avatar', 'date_joined']
        read_only_fields = ['id', 'avatar', 'date_joined']

    def validate_username(self, value):
        value = value.strip()
        if User.objects.filter(username=value).exclude(
            pk=getattr(self.instance, 'pk', None)
        ).exists():
            raise serializers.ValidationError('用户名已存在')
        return value

    def validate_phone(self, value):
        if not value:
            return None
        value = value.strip()
        if value and User.objects.filter(phone=value).exclude(
            pk=getattr(self.instance, 'pk', None)
        ).exists():
            raise serializers.ValidationError('手机号已被注册')
        return value

    def validate_email(self, value):
        if not value:
            return None
        value = value.strip().lower()
        if User.objects.filter(email=value).exclude(
            pk=getattr(self.instance, 'pk', None)
        ).exists():
            raise serializers.ValidationError('邮箱已被注册')
        return value


class AvatarUploadSerializer(serializers.Serializer):
    avatar = serializers.FileField()

    MAX_AVATAR_SIZE = 5 * 1024 * 1024
    ALLOWED_CONTENT_TYPES = {
        'image/gif',
        'image/jpeg',
        'image/png',
        'image/webp',
    }

    def validate_avatar(self, value):
        if value.size > self.MAX_AVATAR_SIZE:
            raise serializers.ValidationError('头像大小不能超过 5MB')
        content_type = (getattr(value, 'content_type', '') or '').lower()
        if content_type and content_type not in (
            self.ALLOWED_CONTENT_TYPES | {'application/octet-stream'}
        ):
            raise serializers.ValidationError('仅支持 JPG、PNG、GIF 或 WebP 图片')
        header = value.read(16)
        value.seek(0)
        if header.startswith(b'\xff\xd8\xff'):
            validated_extension = '.jpg'
        elif header.startswith(b'\x89PNG\r\n\x1a\n'):
            validated_extension = '.png'
        elif header.startswith((b'GIF87a', b'GIF89a')):
            validated_extension = '.gif'
        elif header.startswith(b'RIFF') and header[8:12] == b'WEBP':
            validated_extension = '.webp'
        else:
            raise serializers.ValidationError('头像文件内容不是有效图片')
        value.validated_extension = validated_extension
        return value


class AdminUserSerializer(serializers.ModelSerializer):
    """管理员用户管理序列化器"""
    class Meta:
        model = User
        fields = ['id', 'username', 'nickname', 'email', 'phone', 'avatar', 'password', 'is_staff', 'is_superuser', 'is_active', 'date_joined', 'last_login']
        extra_kwargs = {'password': {'write_only': True, 'required': False}}
        read_only_fields = ['is_superuser', 'date_joined', 'last_login']

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        if password:
            instance.set_password(password)
        return super().update(instance, validated_data)
