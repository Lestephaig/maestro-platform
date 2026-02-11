from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='clientprofile',
            name='address',
            field=models.CharField(blank=True, max_length=255, verbose_name='Адрес площадки'),
        ),
        migrations.AddField(
            model_name='clientprofile',
            name='venue_type',
            field=models.CharField(blank=True, max_length=120, verbose_name='Тип площадки'),
        ),
        migrations.AddField(
            model_name='clientprofile',
            name='hall_capacity',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='Вместимость зала'),
        ),
        migrations.AddField(
            model_name='clientprofile',
            name='has_stage',
            field=models.BooleanField(default=False, verbose_name='Наличие сцены'),
        ),
        migrations.AddField(
            model_name='clientprofile',
            name='stage_size',
            field=models.CharField(blank=True, max_length=120, verbose_name='Размер сцены (Ш×Г×В)'),
        ),
        migrations.AddField(
            model_name='clientprofile',
            name='microphones_count',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='Микрофоны (кол-во)'),
        ),
        migrations.AddField(
            model_name='clientprofile',
            name='sound_system',
            field=models.CharField(blank=True, max_length=200, verbose_name='Акустическая система'),
        ),
        migrations.AddField(
            model_name='clientprofile',
            name='mixing_console',
            field=models.CharField(blank=True, max_length=200, verbose_name='Микшерный пульт'),
        ),
        migrations.AddField(
            model_name='clientprofile',
            name='lighting_equipment',
            field=models.CharField(blank=True, max_length=200, verbose_name='Световое оборудование'),
        ),
        migrations.AddField(
            model_name='clientprofile',
            name='video_equipment',
            field=models.CharField(blank=True, max_length=200, verbose_name='Видеооборудование / экраны'),
        ),
        migrations.AddField(
            model_name='clientprofile',
            name='has_internet',
            field=models.BooleanField(default=False, verbose_name='Интернет'),
        ),
        migrations.AddField(
            model_name='clientprofile',
            name='power_supply',
            field=models.CharField(blank=True, max_length=120, verbose_name='Электропитание 220В / 380В'),
        ),
        migrations.AddField(
            model_name='clientprofile',
            name='has_green_rooms',
            field=models.BooleanField(default=False, verbose_name='Гримерные комнаты'),
        ),
    ]
