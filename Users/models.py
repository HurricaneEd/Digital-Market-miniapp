from django.db import models
from django.contrib.auth.models import AbstractUser

from Product.models import CleanProduct


class User(AbstractUser):
    """扩展用户模型"""
    avatar = models.CharField(max_length=500, null=True, blank=True, verbose_name="头像URL")
    phone = models.CharField(max_length=11, null=True, blank=True, verbose_name="手机号", unique=True)
    # 使用AbstractUser已有的email字段，此处覆盖为可选且唯一
    email = models.EmailField(max_length=254, null=True, blank=True, verbose_name="邮箱", unique=True)
    nickname = models.CharField(max_length=50, null=True, blank=True, verbose_name="昵称")
    class Meta:
        db_table = 'auth_user'
        verbose_name = '用户'
        verbose_name_plural = verbose_name
    def is_admin(self):
        return self.is_superuser or self.is_staff

class UserAction(models.Model):
    """用户行为记录"""
    id = models.BigAutoField(primary_key=True)  # 显式主键，bigint类型
    ACTION_CHOICES = (
        ('view', '浏览'),
        ('cart', '加购'),
        ('buy', '购买'),
        ('favorite', '收藏'),
        ('unfavorite', '取消收藏'),
        ('dislike', '不感兴趣'),
    )
    WEIGHT_MAP = {
        'view': 1,
        'cart': 4,
        'buy': 5,
        'favorite': 3,
        'unfavorite': -3,
        'dislike': -3,
    }

    user = models.ForeignKey(User, on_delete=models.PROTECT, db_column='user_id')
    product = models.ForeignKey(CleanProduct, on_delete=models.PROTECT, db_column='product_id')
    action_type = models.CharField(max_length=10, choices=ACTION_CHOICES)
    count = models.IntegerField(default=1)
    score = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # 检查是否已存在相同记录，存在则累加
        if not self.pk:  # 只在新建时检查，更新时不重复检查
            # 处理 unfavorite - 删除对应的 favorite 记录，不创建新记录
            if self.action_type == 'unfavorite':
                UserAction.objects.filter(
                    user=self.user,
                    product=self.product,
                    action_type='favorite'
                ).delete()
                # 取消收藏成功，不保存当前记录
                return

            # 计算单次得分
            single_score = self.WEIGHT_MAP.get(self.action_type, 1) * self.count

            existing = UserAction.objects.filter(
                user=self.user,
                product=self.product,
                action_type=self.action_type
            ).first()

            if existing:
                existing.count += self.count
                existing.score += single_score
                existing.save()
                # 将当前实例的 pk 设为已存在记录的 pk，避免创建新记录
                self.pk = existing.pk
                return

            self.score = single_score

        super().save(*args, **kwargs)


class Favorite(models.Model):
    """用户收藏表 - 独立的收藏功能"""
    id = models.BigAutoField(primary_key=True)  # 显式主键，bigint类型
    user = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name="用户", db_column='user_id')
    product = models.ForeignKey(CleanProduct, on_delete=models.PROTECT, verbose_name="商品", db_column='product_id')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="收藏时间")

    class Meta:
        db_table = 'users_favorite'
        verbose_name = "收藏"
        verbose_name_plural = "收藏"
        unique_together = ['user', 'product']  # 防止重复收藏
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} 收藏了 {self.product.name}"