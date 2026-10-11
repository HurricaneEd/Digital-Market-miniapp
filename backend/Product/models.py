from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Category(models.Model):
    """商品分类。parent 支持后续扩展多级分类。"""

    id = models.BigAutoField(primary_key=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='上级分类',
    )
    code = models.CharField(max_length=50, unique=True, verbose_name='分类代码')
    name = models.CharField(max_length=50, verbose_name='分类名称')

    class Meta:
        db_table = 'catalog_categories'
        verbose_name = '商品分类'
        verbose_name_plural = verbose_name

    def clean(self):
        ancestor = self.parent
        visited = set()
        while ancestor is not None:
            if ancestor.pk == self.pk or ancestor.pk in visited:
                raise ValidationError({'parent': '分类层级不能形成循环'})
            visited.add(ancestor.pk)
            ancestor = ancestor.parent

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Brand(models.Model):
    """商品品牌。"""

    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=50, unique=True, verbose_name='品牌名称')

    class Meta:
        db_table = 'catalog_brands'
        verbose_name = '品牌信息'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class Product(models.Model):
    """线上商品目录中的唯一商品实体，动态规格统一保存在 all_params。"""

    id = models.BigAutoField(primary_key=True)
    prod_id = models.CharField(max_length=50, unique=True, verbose_name='外部产品ID')
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, related_name='products', verbose_name='品牌')
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products', verbose_name='分类')
    name = models.CharField(max_length=200, verbose_name='商品名称')
    origin = models.CharField(max_length=100, blank=True, default='', verbose_name='产地')
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)], verbose_name='价格')
    img_url = models.URLField(max_length=1000, blank=True, default='', verbose_name='商品主图')
    all_params = models.JSONField(default=dict, blank=True, verbose_name='商品动态参数')
    stock = models.PositiveIntegerField(default=0, verbose_name='库存')
    is_active = models.BooleanField(default=True, verbose_name='是否在售')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'catalog_products'
        verbose_name = '商品信息'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['category', '-updated_at']),
            models.Index(fields=['brand', '-updated_at']),
            models.Index(fields=['is_active', '-updated_at']),
            models.Index(fields=['-updated_at']),
            models.Index(fields=['is_active', 'price']),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(price__gte=0), name='ck_product_price_nonnegative'),
            models.CheckConstraint(condition=models.Q(stock__gte=0), name='ck_product_stock_nonnegative'),
        ]

    def __str__(self):
        return self.name


class Review(models.Model):
    """商品评论。外部匿名评论通过 author_name 保留来源显示名。"""

    id = models.BigAutoField(primary_key=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(
        'Users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviews',
    )
    author_name = models.CharField(max_length=100, blank=True, default='', verbose_name='来源作者名')
    content = models.TextField(verbose_name='评论内容')
    rating = models.DecimalField(
        max_digits=2,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        verbose_name='用户评分',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name='评论时间')

    class Meta:
        db_table = 'catalog_reviews'
        verbose_name = '商品评论'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['product', '-reviewed_at']),
            models.Index(fields=['rating', '-reviewed_at']),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(rating__gte=0), name='ck_review_rating_min'),
            models.CheckConstraint(condition=models.Q(rating__lte=5), name='ck_review_rating_max'),
        ]
