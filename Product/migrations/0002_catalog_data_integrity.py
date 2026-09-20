import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Product', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='brand',
            name='name',
            field=models.CharField(max_length=50, unique=True, verbose_name='品牌名称'),
        ),
        migrations.AlterField(
            model_name='category',
            name='code',
            field=models.CharField(max_length=50, unique=True, verbose_name='分类代码'),
        ),
        migrations.AlterField(
            model_name='product',
            name='prod_id',
            field=models.CharField(max_length=50, unique=True, verbose_name='外部产品ID'),
        ),
        migrations.AlterField(
            model_name='review',
            name='rating',
            field=models.DecimalField(
                blank=True,
                decimal_places=1,
                max_digits=2,
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(0),
                    django.core.validators.MaxValueValidator(5),
                ],
                verbose_name='用户评分',
            ),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['-updated_at'], name='catalog_pro_updated_00195c_idx'),
        ),
        migrations.AddIndex(
            model_name='product',
            index=models.Index(fields=['is_active', 'price'], name='catalog_pro_is_acti_c3a0e8_idx'),
        ),
        migrations.AddIndex(
            model_name='review',
            index=models.Index(fields=['rating', '-reviewed_at'], name='catalog_rev_rating_70039d_idx'),
        ),
        migrations.AddConstraint(
            model_name='product',
            constraint=models.CheckConstraint(
                condition=models.Q(stock__gte=0),
                name='ck_product_stock_nonnegative',
            ),
        ),
    ]
