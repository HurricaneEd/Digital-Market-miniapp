import django.core.validators
from django.db import migrations, models
from django.db.models.functions import Lower, Trim


def normalize_optional_user_fields(apps, schema_editor):
    User = apps.get_model('Users', 'User')
    User.objects.filter(avatar__isnull=True).update(avatar='')
    User.objects.filter(nickname__isnull=True).update(nickname='')
    User.objects.filter(phone__isnull=False).update(phone=Trim('phone'))
    User.objects.filter(phone='').update(phone=None)
    User.objects.filter(email__isnull=False).update(email=Lower(Trim('email')))
    User.objects.filter(email='').update(email=None)


class Migration(migrations.Migration):

    dependencies = [
        ('Users', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(normalize_optional_user_fields, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='user',
            name='avatar',
            field=models.CharField(blank=True, default='', max_length=500, verbose_name='头像URL'),
        ),
        migrations.AlterField(
            model_name='user',
            name='nickname',
            field=models.CharField(blank=True, default='', max_length=50, verbose_name='昵称'),
        ),
        migrations.AlterField(
            model_name='user',
            name='phone',
            field=models.CharField(
                blank=True,
                max_length=11,
                null=True,
                unique=True,
                validators=[
                    django.core.validators.RegexValidator(
                        message='手机号格式不正确',
                        regex=r'^1[3-9]\d{9}$',
                    )
                ],
                verbose_name='手机号',
            ),
        ),
        migrations.AddConstraint(
            model_name='user',
            constraint=models.CheckConstraint(
                condition=models.Q(phone__isnull=True) | ~models.Q(phone=''),
                name='ck_user_phone_not_blank',
            ),
        ),
        migrations.AddConstraint(
            model_name='user',
            constraint=models.CheckConstraint(
                condition=models.Q(email__isnull=True) | ~models.Q(email=''),
                name='ck_user_email_not_blank',
            ),
        ),
    ]
