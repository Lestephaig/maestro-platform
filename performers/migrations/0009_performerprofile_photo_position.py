# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('performers', '0008_change_birth_year_to_birth_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='performerprofile',
            name='photo_position',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('top', 'Верх'),
                    ('center', 'Центр'),
                    ('bottom', 'Низ'),
                ],
                default='center',
                help_text='Позиция фото в Hero секции'
            ),
        ),
    ]
