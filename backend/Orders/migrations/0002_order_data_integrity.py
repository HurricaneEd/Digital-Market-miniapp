import django.core.validators
from django.db import migrations, models


def validate_existing_orders(apps, schema_editor):
    Order = apps.get_model('Orders', 'Order')
    valid_statuses = ['unpaid', 'paid', 'shipped', 'completed', 'cancelled']
    valid_methods = ['wechat', 'alipay']

    invalid = Order.objects.exclude(status__in=valid_statuses)
    invalid = invalid | Order.objects.exclude(
        payment_method__isnull=True
    ).exclude(payment_method__in=valid_methods)
    invalid = invalid | Order.objects.filter(
        status='unpaid',
        payment_method__isnull=False,
    )
    invalid = invalid | Order.objects.filter(
        status__in=['paid', 'shipped', 'completed'],
        payment_method__isnull=True,
    )
    if invalid.exists():
        raise RuntimeError('存在状态或支付方式不一致的订单，请先清理数据后再迁移。')


class Migration(migrations.Migration):

    dependencies = [
        ('Orders', '0001_initial'),
        ('Product', '0002_catalog_data_integrity'),
    ]

    operations = [
        migrations.AlterField(
            model_name='address',
            name='phone',
            field=models.CharField(
                max_length=11,
                validators=[
                    django.core.validators.RegexValidator(
                        message='手机号格式不正确',
                        regex=r'^1[3-9]\d{9}$',
                    )
                ],
                verbose_name='手机号',
            ),
        ),
        migrations.AlterField(
            model_name='shippingaddresssnapshot',
            name='phone',
            field=models.CharField(
                max_length=11,
                validators=[
                    django.core.validators.RegexValidator(
                        message='手机号格式不正确',
                        regex=r'^1[3-9]\d{9}$',
                    )
                ],
                verbose_name='手机号',
            ),
        ),
        migrations.AddIndex(
            model_name='cartitem',
            index=models.Index(fields=['user', '-updated_at'], name='shopping_ca_user_id_586208_idx'),
        ),
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['status', '-created_at'], name='orders_status_f8c8df_idx'),
        ),
        migrations.RunPython(validate_existing_orders, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='order',
            constraint=models.CheckConstraint(
                condition=models.Q(status__in=['unpaid', 'paid', 'shipped', 'completed', 'cancelled']),
                name='ck_order_status_valid',
            ),
        ),
        migrations.AddConstraint(
            model_name='order',
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(payment_method__isnull=True)
                    | models.Q(payment_method__in=['wechat', 'alipay'])
                ),
                name='ck_order_payment_method_valid',
            ),
        ),
        migrations.AddConstraint(
            model_name='order',
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(status='unpaid', payment_method__isnull=True)
                    | models.Q(status='cancelled')
                    | models.Q(
                        status__in=['paid', 'shipped', 'completed'],
                        payment_method__isnull=False,
                    )
                ),
                name='ck_order_status_payment_consistent',
            ),
        ),
    ]
