from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models


phone_validator = RegexValidator(
    regex=r'^1[3-9]\d{9}$',
    message='手机号格式不正确',
)


class User(AbstractUser):
    """扩展用户模型"""
    avatar = models.CharField(max_length=500, blank=True, default='', verbose_name="头像URL")
    phone = models.CharField(
        max_length=11,
        null=True,
        blank=True,
        unique=True,
        validators=[phone_validator],
        verbose_name="手机号",
    )
    # 使用AbstractUser已有的email字段，此处覆盖为可选且唯一
    email = models.EmailField(max_length=254, null=True, blank=True, verbose_name="邮箱", unique=True)
    nickname = models.CharField(max_length=50, blank=True, default='', verbose_name="昵称")

    class Meta:
        db_table = 'auth_user'
        verbose_name = '用户'
        verbose_name_plural = verbose_name
        constraints = [
            models.CheckConstraint(
                condition=models.Q(phone__isnull=True) | ~models.Q(phone=''),
                name='ck_user_phone_not_blank',
            ),
            models.CheckConstraint(
                condition=models.Q(email__isnull=True) | ~models.Q(email=''),
                name='ck_user_email_not_blank',
            ),
        ]

    def save(self, *args, **kwargs):
        self.phone = self.phone.strip() if self.phone and self.phone.strip() else None
        self.email = self.email.strip().lower() if self.email and self.email.strip() else None
        self.avatar = self.avatar or ''
        self.nickname = self.nickname or ''
        super().save(*args, **kwargs)

    def is_admin(self):
        return self.is_superuser or self.is_staff
