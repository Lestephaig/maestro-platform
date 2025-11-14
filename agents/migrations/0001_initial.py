from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AgentProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('display_name', models.CharField(max_length=200, verbose_name='Отображаемое имя')),
                ('agency_name', models.CharField(blank=True, max_length=200, verbose_name='Агентство')),
                ('bio', models.TextField(blank=True, verbose_name='Описание')),
                ('specialization', models.CharField(blank=True, max_length=200, verbose_name='Специализация')),
                ('experience_years', models.PositiveIntegerField(default=0, verbose_name='Опыт (лет)')),
                ('website', models.URLField(blank=True, verbose_name='Сайт или портфолио')),
                ('trust_level', models.PositiveIntegerField(default=0, help_text='Уровень доверия (0-100)', verbose_name='Уровень доверия')),
                ('total_deals', models.PositiveIntegerField(default=0, help_text='Общее количество сделок', verbose_name='Всего сделок')),
                ('successful_deals', models.PositiveIntegerField(default=0, help_text='Количество успешных сделок', verbose_name='Успешных сделок')),
                ('is_verified', models.BooleanField(default=False, verbose_name='Верифицирован')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создано')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлено')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='agent_profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
                'verbose_name': 'Профиль организатора',
                'verbose_name_plural': 'Профили организаторов',
            },
        ),
    ]

