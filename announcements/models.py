from django.db import models
from django.conf import settings
from django.utils import timezone


class Tag(models.Model):
    """Теги для объявлений"""
    name = models.CharField('Название', max_length=50, unique=True)
    slug = models.SlugField('URL', max_length=50, unique=True)
    created_at = models.DateTimeField('Создано', auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return self.name


class Announcement(models.Model):
    TYPE_NEED_PERFORMER = 'need_performer'
    TYPE_NEED_VENUE = 'need_venue'
    TYPE_COLLABORATION = 'collaboration'
    TYPE_AUDITION = 'audition'
    TYPE_CONTEST = 'contest'
    TYPE_OTHER = 'other'
    TYPE_CHOICES = [
        (TYPE_NEED_PERFORMER, 'Ищем исполнителей'),
        (TYPE_NEED_VENUE, 'Ищем площадку'),
        (TYPE_COLLABORATION, 'Совместный проект'),
        (TYPE_AUDITION, 'Прослушивание'),
        (TYPE_CONTEST, 'Конкурс'),
        (TYPE_OTHER, 'Другое'),
    ]

    STATUS_DRAFT = 'draft'
    STATUS_PUBLISHED = 'published'
    STATUS_ARCHIVED = 'archived'
    STATUS_COMPLETED = 'completed'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Черновик'),
        (STATUS_PUBLISHED, 'Опубликовано'),
        (STATUS_ARCHIVED, 'Архивировано'),
        (STATUS_COMPLETED, 'Завершено'),
    ]

    CURRENCY_RUB = 'RUB'
    CURRENCY_USD = 'USD'
    CURRENCY_EUR = 'EUR'
    CURRENCY_CHOICES = [
        (CURRENCY_RUB, '₽'),
        (CURRENCY_USD, '$'),
        (CURRENCY_EUR, '€'),
    ]

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='Автор',
        on_delete=models.CASCADE,
        related_name='announcements',
    )
    author_role = models.CharField(
        'Роль автора',
        max_length=20,
        blank=True,
        help_text='Для быстрого фильтра по типу аккаунта',
    )
    title = models.CharField('Название', max_length=255)
    announcement_type = models.CharField(
        'Тип объявления',
        max_length=32,
        choices=TYPE_CHOICES,
        default=TYPE_NEED_PERFORMER,
    )
    description = models.TextField('Описание')
    requirements = models.JSONField('Требования', blank=True, null=True)
    tags = models.ManyToManyField(
        Tag,
        verbose_name='Теги',
        related_name='announcements',
        blank=True,
    )
    city = models.CharField('Город', max_length=255, blank=True)
    location = models.CharField('Локация', max_length=255, blank=True)
    is_online = models.BooleanField('Онлайн', default=False)
    is_one_day = models.BooleanField('Одним днем', default=False)
    start_date = models.DateField('Дата начала', null=True, blank=True)
    end_date = models.DateField('Дата окончания', null=True, blank=True)
    application_deadline = models.DateField('Дедлайн откликов', null=True, blank=True)
    budget_amount = models.DecimalField(
        'Бюджет',
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    budget_currency = models.CharField(
        'Валюта',
        max_length=3,
        choices=CURRENCY_CHOICES,
        default=CURRENCY_RUB,
    )
    is_paid = models.BooleanField('Оплачиваемо', default=True)
    status = models.CharField(
        'Статус',
        max_length=16,
        choices=STATUS_CHOICES,
        default=STATUS_PUBLISHED,
    )
    is_approved = models.BooleanField('Одобрено модератором', default=True)
    published_at = models.DateTimeField('Опубликовано', null=True, blank=True)
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        ordering = ['-published_at', '-created_at']
        verbose_name = 'Объявление'
        verbose_name_plural = 'Объявления'

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # Автоматически устанавливаем published_at при первой публикации
        if self.status == self.STATUS_PUBLISHED and not self.published_at:
            self.published_at = timezone.now()
        # Сохраняем роль автора при создании
        if not self.author_role and self.author:
            self.author_role = self.author.role
        # Если выбрано "Одним днем", то end_date = start_date
        if self.is_one_day and self.start_date:
            self.end_date = self.start_date
        super().save(*args, **kwargs)

    @property
    def is_active(self):
        return self.status in [self.STATUS_PUBLISHED, self.STATUS_COMPLETED] and self.is_approved

    @property
    def is_deadline_soon(self):
        """Проверяет, скоро ли дедлайн (менее 3 дней)"""
        if not self.application_deadline:
            return False
        from datetime import timedelta
        return (self.application_deadline - timezone.now().date()) <= timedelta(days=3)

    @property
    def response_count(self):
        """Количество откликов на объявление"""
        return self.responses.count()


class AnnouncementResponse(models.Model):
    """Отклики на объявления"""
    STATUS_NEW = 'new'
    STATUS_VIEWED = 'viewed'
    STATUS_ACCEPTED = 'accepted'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = [
        (STATUS_NEW, 'Новый'),
        (STATUS_VIEWED, 'Просмотрен'),
        (STATUS_ACCEPTED, 'Принят'),
        (STATUS_REJECTED, 'Отклонен'),
    ]

    announcement = models.ForeignKey(
        Announcement,
        verbose_name='Объявление',
        on_delete=models.CASCADE,
        related_name='responses',
    )
    responder = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='Откликнувшийся',
        on_delete=models.CASCADE,
        related_name='announcement_responses',
    )
    message = models.TextField('Сообщение', blank=True)
    status = models.CharField(
        'Статус',
        max_length=16,
        choices=STATUS_CHOICES,
        default=STATUS_NEW,
    )
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлено', auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Отклик'
        verbose_name_plural = 'Отклики'
        unique_together = ['announcement', 'responder']  # Один пользователь может откликнуться только один раз

    def __str__(self):
        return f'Отклик от {self.responder} на "{self.announcement.title}"'
