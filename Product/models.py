from django.db import models

class Category(models.Model):
    """商品分类表"""
    id = models.BigAutoField(primary_key=True)  # 显式主键，bigint类型
    # 原始分类代码，如 cell_phone, digital_camera
    code = models.CharField(max_length=50, unique=True, db_index=True, verbose_name="分类代码")
    # 展示名称，如 手机, 数码相机
    name = models.CharField(max_length=50, verbose_name="分类名称")

    class Meta:
        db_table = 'product_categories'
        verbose_name = '商品分类'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name

class Brand(models.Model):
    """品牌表"""
    id = models.BigAutoField(primary_key=True)  # 显式主键，bigint类型
    name = models.CharField(max_length=50, unique=True, db_index=True, verbose_name="品牌名称")

    class Meta:
        db_table = 'product_brands'
        verbose_name = '品牌信息'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name
class Product(models.Model):
    """商品主表"""
    prod_id = models.CharField(max_length=20, primary_key=True, verbose_name="产品ID")

    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, db_index=True, verbose_name="品牌", null=True, blank=True)

    category = models.ForeignKey(Category, on_delete=models.PROTECT, db_index=True, verbose_name="分类", null=True, blank=True)

    name = models.CharField(max_length=200, verbose_name="商品名称")
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="价格")

    rate = models.FloatField(default=0.0, verbose_name="评分")
    comment_count = models.IntegerField(default=0, verbose_name="评论数")

    img_url = models.URLField(max_length=1000, verbose_name="图片链接")

    sub_images = models.JSONField(default=list, verbose_name="轮播图列表")
    all_params = models.JSONField(default=dict, verbose_name="详细参数")

    stock = models.IntegerField(default=100, verbose_name="库存")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    is_active = models.BooleanField(default=True, verbose_name="是否在售")

    class Meta:
        db_table = 'products'
        verbose_name = '商品信息'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class Review(models.Model):
    """评论从表"""
    id = models.BigAutoField(primary_key=True)  # 显式主键，bigint类型
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='reviews')
    username = models.CharField(max_length=50, verbose_name="用户名")
    content = models.TextField(verbose_name="评论内容")
    rating = models.FloatField(default=0.0, verbose_name="用户评分")
    date = models.CharField(max_length=30, verbose_name="原始评论日期")

    class Meta:
        db_table = 'raw_reviews'
        verbose_name = '用户评论'
        verbose_name_plural = verbose_name


class CleanProduct(models.Model):
    """清洁后的产品表"""
    prod_id = models.CharField(max_length=20, primary_key=True, verbose_name="产品ID")

    # 直接存储原始ID，使用BigIntegerField匹配Category/Brand主键类型
    brand_id = models.BigIntegerField(db_index=True, null=True, blank=True, verbose_name="品牌ID")
    category_id = models.BigIntegerField(db_index=True, null=True, blank=True, verbose_name="分类ID")

    name = models.CharField(max_length=200, verbose_name="商品名称")
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="价格")

    rate = models.FloatField(default=0.0, verbose_name="评分")
    comment_count = models.IntegerField(default=0, verbose_name="评论数")

    img_url = models.URLField(max_length=1000, verbose_name="主图链接")
    sub_images = models.JSONField(default=list, verbose_name="轮播图列表")
    all_params = models.JSONField(default=dict, verbose_name="详细参数")

    stock = models.IntegerField(default=0, verbose_name="库存")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    is_active = models.BooleanField(default=True, verbose_name="是否在售")

    class Meta:
        db_table = 'clean_products'
        verbose_name = '清洁产品'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class CleanReview(models.Model):
    """清洁后的评论表"""
    id = models.BigAutoField(primary_key=True)  # 显式主键，bigint类型
    product = models.ForeignKey(CleanProduct, on_delete=models.PROTECT, related_name='reviews')
    user = models.ForeignKey('Users.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='reviews')
    username = models.CharField(max_length=50, verbose_name="用户名")  # 保留用于兼容历史数据
    content = models.TextField(verbose_name="评论内容", blank=True, default="")
    clean_content = models.TextField(verbose_name="分词过滤后的内容", default="", blank=True)
    rating = models.FloatField(default=0.0, verbose_name="用户评分")
    date = models.DateTimeField(verbose_name="评论日期")
    sentiment_score = models.FloatField(default=None, null=True, blank=True, verbose_name="情感分值")
    sentiment_label = models.CharField(max_length=20, default="", blank=True, verbose_name="情感标签")

    class Meta:
        db_table = 'clean_reviews'
        verbose_name = '清洁评论'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.username}: {self.content[:20]}..."














