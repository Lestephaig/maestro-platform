from django.db import models
from accounts.models import User


class AgentProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='agent_profile',
    )
    display_name = models.CharField('Отображаемое имя', max_length=200)
    agency_name = models.CharField('Агентство', max_length=200, blank=True)
    bio = models.TextField('Описание', blank=True)
    specialization = models.CharField('Специализация', max_length=200, blank=True)
    experience_years = models.PositiveIntegerField('Опыт (лет)', default=0)
    website = models.URLField('Сайт или портфолио', blank=True)
    trust_level = models.PositiveIntegerField(
        'Уровень доверия',
        default=0,
        help_text='Уровень доверия (0-100)',
    )
    total_deals = models.PositiveIntegerField(
        'Всего сделок',
        default=0,
        help_text='Общее количество сделок',
    )
    successful_deals = models.PositiveIntegerField(
        'Успешных сделок',
        default=0,
        help_text='Количество успешных сделок',
    )
    is_verified = models.BooleanField('Верифицирован', default=False)
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        verbose_name = 'Профиль организатора'
        verbose_name_plural = 'Профили организаторов'
        ordering = ['-created_at']

    def __str__(self):
        return f"Agent: {self.display_name or self.user.username}"

