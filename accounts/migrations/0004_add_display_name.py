# Generated manually for adding display_name field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_add_email_verification'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='display_name',
            field=models.CharField(
                blank=True,
                help_text='Отображаемое имя пользователя',
                max_length=150,
                verbose_name='Имя пользователя'
            ),
        ),
    ]

