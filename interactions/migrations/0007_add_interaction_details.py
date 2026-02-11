from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('interactions', '0006_interaction_completion_completed_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='interaction',
            name='organizer_name',
            field=models.CharField(blank=True, max_length=255, verbose_name='Организатор'),
        ),
        migrations.AddField(
            model_name='interaction',
            name='contact_person',
            field=models.CharField(blank=True, max_length=255, verbose_name='Контактное лицо'),
        ),
        migrations.AddField(
            model_name='interaction',
            name='contact_info',
            field=models.CharField(blank=True, max_length=255, verbose_name='Телефон / Email'),
        ),
        migrations.AddField(
            model_name='interaction',
            name='event_date',
            field=models.DateField(blank=True, null=True, verbose_name='Дата проведения'),
        ),
        migrations.AddField(
            model_name='interaction',
            name='event_start_time',
            field=models.TimeField(blank=True, null=True, verbose_name='Время начала'),
        ),
        migrations.AddField(
            model_name='interaction',
            name='event_end_time',
            field=models.TimeField(blank=True, null=True, verbose_name='Время окончания'),
        ),
        migrations.AddField(
            model_name='interaction',
            name='total_duration',
            field=models.CharField(blank=True, max_length=120, verbose_name='Общая продолжительность'),
        ),
        migrations.AddField(
            model_name='interaction',
            name='rehearsal_schedule',
            field=models.CharField(blank=True, max_length=200, verbose_name='Репетиции / саундчек'),
        ),
        migrations.AddField(
            model_name='interaction',
            name='setup_schedule',
            field=models.CharField(blank=True, max_length=200, verbose_name='Монтаж оборудования'),
        ),
        migrations.AddField(
            model_name='interaction',
            name='teardown_schedule',
            field=models.CharField(blank=True, max_length=200, verbose_name='Демонтаж оборудования'),
        ),
        migrations.AddField(
            model_name='interaction',
            name='event_type',
            field=models.CharField(blank=True, max_length=32, verbose_name='Тип мероприятия'),
        ),
        migrations.AddField(
            model_name='interaction',
            name='event_format',
            field=models.CharField(blank=True, max_length=32, verbose_name='Формат проведения'),
        ),
        migrations.AddField(
            model_name='interaction',
            name='venue_name',
            field=models.CharField(blank=True, max_length=255, verbose_name='Наименование площадки'),
        ),
        migrations.AddField(
            model_name='interaction',
            name='venue_address',
            field=models.CharField(blank=True, max_length=255, verbose_name='Адрес площадки'),
        ),
        migrations.AddField(
            model_name='interaction',
            name='venue_type',
            field=models.CharField(blank=True, max_length=120, verbose_name='Тип площадки'),
        ),
        migrations.AddField(
            model_name='interaction',
            name='venue_capacity',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='Вместимость зала'),
        ),
        migrations.AddField(
            model_name='interaction',
            name='venue_has_stage',
            field=models.BooleanField(default=False, verbose_name='Наличие сцены'),
        ),
        migrations.AddField(
            model_name='interaction',
            name='venue_requirements',
            field=models.TextField(blank=True, verbose_name='Требования к площадке'),
        ),
        migrations.AddField(
            model_name='interaction',
            name='stage_size',
            field=models.CharField(blank=True, max_length=120, verbose_name='Размер сцены (Ш×Г×В)'),
        ),
        migrations.AddField(
            model_name='interaction',
            name='microphones_count',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='Микрофоны (кол-во)'),
        ),
        migrations.AddField(
            model_name='interaction',
            name='sound_system',
            field=models.CharField(blank=True, max_length=200, verbose_name='Акустическая система'),
        ),
        migrations.AddField(
            model_name='interaction',
            name='mixing_console',
            field=models.CharField(blank=True, max_length=200, verbose_name='Микшерный пульт'),
        ),
        migrations.AddField(
            model_name='interaction',
            name='lighting_equipment',
            field=models.CharField(blank=True, max_length=200, verbose_name='Световое оборудование'),
        ),
        migrations.AddField(
            model_name='interaction',
            name='video_equipment',
            field=models.CharField(blank=True, max_length=200, verbose_name='Видеооборудование / экраны'),
        ),
        migrations.AddField(
            model_name='interaction',
            name='has_internet',
            field=models.BooleanField(default=False, verbose_name='Интернет'),
        ),
        migrations.AddField(
            model_name='interaction',
            name='power_supply',
            field=models.CharField(blank=True, max_length=120, verbose_name='Электропитание 220В / 380В'),
        ),
        migrations.AddField(
            model_name='interaction',
            name='has_green_rooms',
            field=models.BooleanField(default=False, verbose_name='Гримерные комнаты'),
        ),
        migrations.AddField(
            model_name='interaction',
            name='staff_host',
            field=models.BooleanField(default=False, verbose_name='Ведущий'),
        ),
        migrations.AddField(
            model_name='interaction',
            name='staff_sound_engineer',
            field=models.BooleanField(default=False, verbose_name='Звукорежиссёр'),
        ),
        migrations.AddField(
            model_name='interaction',
            name='staff_light_engineer',
            field=models.BooleanField(default=False, verbose_name='Светорежиссёр'),
        ),
        migrations.AddField(
            model_name='interaction',
            name='staff_tech_admin',
            field=models.BooleanField(default=False, verbose_name='Технический администратор'),
        ),
        migrations.AddField(
            model_name='interaction',
            name='staff_security',
            field=models.BooleanField(default=False, verbose_name='Охрана'),
        ),
        migrations.AddField(
            model_name='interaction',
            name='staff_medical',
            field=models.BooleanField(default=False, verbose_name='Медицинское сопровождение'),
        ),
        migrations.AddField(
            model_name='interaction',
            name='info_promo_materials',
            field=models.BooleanField(default=False, verbose_name='Афиша / рекламные материалы'),
        ),
        migrations.AddField(
            model_name='interaction',
            name='info_online_registration',
            field=models.BooleanField(default=False, verbose_name='Онлайн-регистрация'),
        ),
        migrations.AddField(
            model_name='interaction',
            name='info_photo_video',
            field=models.BooleanField(default=False, verbose_name='Фото- и видеосъёмка'),
        ),
        migrations.AddField(
            model_name='interaction',
            name='info_live_stream',
            field=models.BooleanField(default=False, verbose_name='Онлайн-трансляция'),
        ),
        migrations.AddField(
            model_name='interaction',
            name='paid_entry',
            field=models.BooleanField(default=False, verbose_name='Платный вход'),
        ),
        migrations.AddField(
            model_name='interaction',
            name='ticket_price',
            field=models.CharField(blank=True, max_length=120, verbose_name='Стоимость билета / взноса'),
        ),
        migrations.AddField(
            model_name='interaction',
            name='venue_special_requirements',
            field=models.TextField(blank=True, verbose_name='Особые требования площадки'),
        ),
        migrations.AddField(
            model_name='interaction',
            name='additional_comments',
            field=models.TextField(blank=True, verbose_name='Дополнительные комментарии'),
        ),
    ]
